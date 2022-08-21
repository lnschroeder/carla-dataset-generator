import os
import carla
import numpy as np
from PIL import Image

SpawnActor = carla.command.SpawnActor
SetAutopilot = carla.command.SetAutopilot
SetVehicleLightState = carla.command.SetVehicleLightState
FutureActor = carla.command.FutureActor


class Operator:
    def __init__(self, sync_world, spawn_point):
        self.sync_world = sync_world
        self.spawn_point = spawn_point
        bp_lib = sync_world.world.get_blueprint_library()
        self.blueprint = bp_lib.filter('vehicle')[1]
        self.cam_blueprints = [bp_lib.find('sensor.camera.rgb'),
                               bp_lib.find('sensor.camera.depth'),
                               bp_lib.find('sensor.camera.instance_segmentation'),
                               bp_lib.find('sensor.camera.optical_flow')]

        for blueprint in self.cam_blueprints:
            blueprint.set_attribute('image_size_x', str(sync_world.img_w))
            blueprint.set_attribute('image_size_y', str(sync_world.img_h))
            blueprint.set_attribute('fov', str(sync_world.fov))

        self.cam_names = ['rgb', 'dep', 'isg', 'ofl']
        self._cam_cc = [carla.ColorConverter.Raw,
                        carla.ColorConverter.Depth,
                        carla.ColorConverter.Raw,
                        carla.ColorConverter.Raw]
        self.actor = None
        self.cams = []
        self.cam_transform = self.sync_world.cam_transform

    def get_spawn_cmd(self):
        return SpawnActor(self.blueprint, self.spawn_point)\
            .then(SetAutopilot(FutureActor, True, self.sync_world.tm_port))

    def get_spawn_cam_cmds(self):
        return [SpawnActor(cam, self.cam_transform, self.actor) for cam in self.cam_blueprints]

    def stop(self):
        for cam in self.cams:
            cam.destroy()

        self.actor.destroy()

    # source: https://github.com/carla-simulator/carla/blob/0.9.11/PythonAPI/examples/sensor_synchronization.py#L41
    def save_cam_data(self, *cam_data):
        for cam_name, cam_cc, data in zip(self.cam_names, self._cam_cc, cam_data):
            path_dir = os.path.join(self.sync_world.dataset_path, cam_name)
            path = os.path.join(path_dir, '%08d.png' % data.frame)

            if cam_name == 'dep':
                # https://github.com/carla-simulator/carla/blob/0.9.13/LibCarla/source/carla/image/ColorConverter.h#L28-L42
                data.save_to_disk(path, cam_cc)
                continue
            elif cam_name == 'ofl':
                data = data.get_color_coded_flow()

            img = np.frombuffer(data.raw_data, dtype=np.dtype("uint8"))
            img = np.reshape(img, (data.height, data.width, 4))
            img = img[..., 2::-1]  # BGRA2RGB

            os.makedirs(path_dir, exist_ok=True)
            Image.fromarray(img).save(path)

    def get_speed(self):
        vel = self.actor.get_velocity()
        return np.linalg.norm([vel.x, vel.y, vel.z]) * 3.6
