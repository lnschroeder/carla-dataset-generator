import logging
import carla
import csv
import os

from queue import Queue

from actors.Operator import Operator
from actors.TrafficManager import TrafficManager
from actors.Vehicle import Vehicle, get_random_vehicle_spawn_points
from actors.Walker import Walker

WEATHER_PRESETS = {
    'Default': carla.WeatherParameters.Default,
    'ClearNoon': carla.WeatherParameters.ClearNoon,
    'CloudyNoon': carla.WeatherParameters.CloudyNoon,
    'WetNoon': carla.WeatherParameters.WetNoon,
    'WetCloudyNoon': carla.WeatherParameters.WetCloudyNoon,
    'SoftRainNoon': carla.WeatherParameters.SoftRainNoon,
    'MidRainyNoon': carla.WeatherParameters.MidRainyNoon,
    'HardRainNoon': carla.WeatherParameters.HardRainNoon,
    'ClearSunset': carla.WeatherParameters.ClearSunset,
    'CloudySunset': carla.WeatherParameters.CloudySunset,
    'WetSunset': carla.WeatherParameters.WetSunset,
    'WetCloudySunset': carla.WeatherParameters.WetCloudySunset,
    'SoftRainSunset': carla.WeatherParameters.SoftRainSunset,
    'MidRainSunset': carla.WeatherParameters.MidRainSunset,
    'HardRainSunset': carla.WeatherParameters.HardRainSunset,
}


class SyncWorld:
    def __init__(self, client, dataset_path, map_name, seed, fps, img_h, img_w, fov, cam_transform, n_vehicles, n_walkers, weather_name, speed_diff, tm_port=8000):
        self.client = client
        self.map_name = map_name
        self.world = None
        self.frame = -1
        self.fps = fps
        self.img_h = img_h
        self.img_w = img_w
        self.fov = fov
        self.cam_transform = cam_transform
        self.tm = None
        self.tm_port = tm_port
        self.seed = seed
        self.dataset_path = dataset_path
        self.weather = WEATHER_PRESETS[weather_name]
        self.speed_diff = speed_diff

        self.vehicles = []
        self.walkers = []
        self.op = None
        self.meta_data = [[
            'frame',
            'traffic_light',
            'speed_limit',
            'speed'
        ]]

        self.queues = []

        self.running_factor = 0.5  # how many pedestrians will run
        self.standing_factor = 0.1  # how many pedestrians will stand
        self.crossing_factor = 0.2  # how many pedestrians will cross the roads

        # some settings
        self._n_vehicles = n_vehicles
        self._n_walkers = n_walkers

    def tick(self, timeout):
        self.frame = self.world.tick()
        op = self.op.actor
        traffic_light = op.get_traffic_light().state if op.is_at_traffic_light() else 'None'

        meta_data = [
            self.frame, traffic_light, op.get_speed_limit(), self.op.get_speed()
        ]

        actor_data = [[
            'id',
            'type_id',
            'attribs',
            'fwd_x', 'fwd_y', 'fwd_z',
            'rgt_x', 'rgt_y', 'rgt_z',
            'upp_x', 'upp_y', 'upp_z',
            'rot_p', 'rot_y', 'rot_r',
            'loc_x', 'loc_y', 'loc_z',
            'vel_x', 'vel_y', 'vel_z',
            'acc_x', 'acc_y', 'acc_z',
            'agv_x', 'agv_y', 'agv_z'
        ]]

        for actor in [self.op] + self.vehicles + self.walkers:
            a = actor.actor
            a_id = a.id
            type_id = a.type_id
            attribs = a.attributes

            tf = a.get_transform()
            fwd = tf.get_forward_vector()
            rgt = tf.get_right_vector()
            upp = tf.get_up_vector()
            rot = tf.rotation
            loc = tf.location
            vel = a.get_velocity()
            acc = a.get_acceleration()
            agv = a.get_angular_velocity()

            fwd = [fwd.x, fwd.y, fwd.z]
            rgt = [rgt.x, rgt.y, rgt.z]
            upp = [upp.x, upp.y, upp.z]
            rot = [rot.pitch, rot.yaw, rot.roll]
            loc = [loc.x, loc.y, loc.z]
            vel = [vel.x, vel.y, vel.z]
            acc = [acc.x, acc.y, acc.z]
            agv = [agv.x, agv.y, agv.z]

            actor_data.append([a_id, type_id, attribs, *fwd, *rgt, *upp, *rot, *loc, *vel, *acc, *agv])

        cam_data = [self.retrieve_data(q, timeout) for q in self.queues]
        assert all(x.frame == self.frame for x in cam_data)

        return meta_data, actor_data, cam_data, self.world.get_snapshot()

    def retrieve_data(self, sensor_queue, timeout):
        while True:
            data = sensor_queue.get(timeout=timeout)
            if data.frame == self.frame:
                return data

    def load_world(self):
        self.world = self.client.load_world(self.map_name, reset_settings=False)
        self.tm = TrafficManager(self)

        self.world.set_pedestrians_cross_factor(self.crossing_factor)

    def spawn_op(self, spawn_point):
        self.op = Operator(self, spawn_point)
        spawn_cmd = self.op.get_spawn_cmd()
        response = self.client.apply_batch_sync([spawn_cmd], True)[0]

        if response.error:
            logging.error(response.error)
        else:
            self.op.actor = self.world.get_actor(response.actor_id)

        spawn_cam_cmds = self.op.get_spawn_cam_cmds()
        responses = self.client.apply_batch_sync(spawn_cam_cmds, True)

        def make_queue(register_event):
            q = Queue()
            register_event(q.put)
            self.queues.append(q)

        for response in responses:
            if response.error:
                logging.error(response.error + " (operator)")
            else:
                cam = self.world.get_actor(response.actor_id)
                self.op.cams.append(cam)
                make_queue(cam.listen)

    def spawn_vehicles(self, spawn_points):
        temp_vehicles = [Vehicle(self, spawn_point) for spawn_point in spawn_points]
        spawn_cmds = [vehicle.get_spawn_cmd() for vehicle in temp_vehicles]
        responses = self.client.apply_batch_sync(spawn_cmds, True)

        for vehicle, response in zip(temp_vehicles, responses):
            if not response.error:
                vehicle.actor = self.world.get_actor(response.actor_id)
                self.vehicles.append(vehicle)

    def spawn_walkers(self):
        # spawn walker actors
        spawn_points = [carla.Transform(self.world.get_random_location_from_navigation()) for _ in range(self._n_walkers)]
        temp_walkers = [Walker(self, spawn_point) for spawn_point in spawn_points]
        spawn_cmds = [walker.get_spawn_cmd() for walker in temp_walkers]
        responses = self.client.apply_batch_sync(spawn_cmds, True)

        temp_walkers2 = []
        for walker, response in zip(temp_walkers, responses):
            if not response.error:
                walker.actor = self.world.get_actor(response.actor_id)
                temp_walkers2.append(walker)

        # spawn walker controllers
        spawn_controller_cmds = [walker.get_spawn_controller_cmd() for walker in temp_walkers2]
        responses = self.client.apply_batch_sync(spawn_controller_cmds, True)

        for walker, response in zip(temp_walkers2, responses):
            if response.error:
                walker.stop()
                logging.error(response.error)
            else:
                walker.controller = self.world.get_actor(response.actor_id)
                self.walkers.append(walker)

        # start walkers
        for walker in self.walkers:
            walker.start()

    def __enter__(self):
        self.load_world()
        spawn_points = get_random_vehicle_spawn_points(self.world, self._n_vehicles)
        self.spawn_op(spawn_points[0])
        self.world.tick()
        self.spawn_vehicles(spawn_points[1:])
        self.world.tick()
        for vehicle in [*self.vehicles, self.op]:
            self.tm.tm.update_vehicle_lights(vehicle.actor, True)
        self.spawn_walkers()
        self.world.set_weather(self.weather)
        logging.info('Spawned %d vehicles and %d walkers, press Ctrl+C to exit.' % (len(self.vehicles), len(self.walkers)))

        return self

    def __exit__(self, *args, **kwargs):
        # destroy vehicles
        logging.info('Destroying %d vehicles' % len(self.vehicles))
        for vehicle in self.vehicles:
            vehicle.stop()

        # destroy walkers
        logging.info('Destroying %d walkers' % len(self.walkers))
        for walker in self.walkers:
            walker.stop()

        # destroy operator
        logging.info('Destroying op with cams')
        self.op.stop()

        logging.info('Writing metadata')
        # write meta_data to csv
        with open(os.path.join(self.dataset_path, 'frame_info.csv'), mode='w') as csv_file:
            csv_writer = csv.writer(csv_file, delimiter=',')
            csv_writer.writerows(self.meta_data)
