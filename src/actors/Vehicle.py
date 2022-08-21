import logging
import random
import carla

SpawnActor = carla.command.SpawnActor
SetAutopilot = carla.command.SetAutopilot
SetVehicleLightState = carla.command.SetVehicleLightState
FutureActor = carla.command.FutureActor


class Vehicle:
    def __init__(self, sync_world, spawn_point):
        self.blueprint = get_random_vehicle_bp(get_bp_vehicles(sync_world.world, 'vehicle.*'))
        self.actor = None
        self.spawn_point = spawn_point
        self.tm_port = sync_world.tm_port

    def get_spawn_cmd(self):
        return SpawnActor(self.blueprint, self.spawn_point)\
            .then(SetAutopilot(FutureActor, True, self.tm_port))  # TODO light

    def stop(self):
        self.actor.destroy()


def get_random_vehicle_spawn_points(world, amount):
    spawn_points = world.get_map().get_spawn_points()
    random.shuffle(spawn_points)

    if amount > len(spawn_points):
        msg = "requested %d vehicle spawn points (including operator), but could only find %d spawn points. " \
              "Number of vehicles gets reduced accordingly!"
        logging.warning(msg, amount, len(spawn_points))

    return spawn_points[:amount]


def get_bp_vehicles(world, filterv):
    bp_vehicles = world.get_blueprint_library().filter(filterv)
    # avoid spawning vehicles prone to accidents
    bp_vehicles = [x for x in bp_vehicles if int(x.get_attribute('number_of_wheels')) == 4]
    bp_vehicles = [x for x in bp_vehicles if not x.id.endswith('microlino')]
    bp_vehicles = [x for x in bp_vehicles if not x.id.endswith('carlacola')]
    bp_vehicles = [x for x in bp_vehicles if not x.id.endswith('cybertruck')]
    bp_vehicles = [x for x in bp_vehicles if not x.id.endswith('t2')]
    bp_vehicles = [x for x in bp_vehicles if not x.id.endswith('sprinter')]
    bp_vehicles = [x for x in bp_vehicles if not x.id.endswith('firetruck')]
    bp_vehicles = [x for x in bp_vehicles if not x.id.endswith('ambulance')]

    bp_vehicles = sorted(bp_vehicles, key=lambda bp: bp.id)

    return bp_vehicles


def get_random_vehicle_bp(bp_vehicles):
    vehicle_bp = random.choice(bp_vehicles)

    if vehicle_bp.has_attribute('color'):
        color = random.choice(vehicle_bp.get_attribute('color').recommended_values)
        vehicle_bp.set_attribute('color', color)
    if vehicle_bp.has_attribute('driver_id'):
        driver_id = random.choice(vehicle_bp.get_attribute('driver_id').recommended_values)
        vehicle_bp.set_attribute('driver_id', driver_id)

    vehicle_bp.set_attribute('role_name', 'autopilot')

    return vehicle_bp
