import random
import carla

SpawnActor = carla.command.SpawnActor


class Walker:
    def __init__(self, sync_world, spawn_point):
        self.world = sync_world.world
        self.blueprint, self.speed = get_random_walker_bp(
            self.world.get_blueprint_library().filter('walker.pedestrian.*'),
            sync_world.running_factor,
            sync_world.standing_factor
        )

        self.actor = None
        self.controller = None
        self.spawn_point = spawn_point

    def get_spawn_cmd(self):
        return SpawnActor(self.blueprint, self.spawn_point)

    def get_spawn_controller_cmd(self):
        return SpawnActor(
            self.world.get_blueprint_library().find('controller.ai.walker'),
            carla.Transform(),
            self.actor
        )

    def start(self):
        self.controller.start()
        self.controller.go_to_location(self.world.get_random_location_from_navigation())
        self.controller.set_max_speed(float(self.speed))

    def stop(self):
        if self.controller is not None:
            self.controller.stop()
            self.controller.destroy()
        self.actor.destroy()


def get_random_walker_bp(bp_walkers, running_factor, standing_factor):
    blueprint = random.choice(bp_walkers)

    # set as not invincible
    if blueprint.has_attribute('is_invincible'):
        blueprint.set_attribute('is_invincible', 'false')

    # set the max speed
    if blueprint.has_attribute('speed'):
        r = random.random()
        if r > 1 - running_factor:
            # walking
            walker_speed = blueprint.get_attribute('speed').recommended_values[1]
        elif r <= standing_factor:
            # standing
            walker_speed = blueprint.get_attribute('speed').recommended_values[0]
        else:
            # running
            walker_speed = blueprint.get_attribute('speed').recommended_values[2]
    else:
        print("Walker has no speed")
        walker_speed = 0.0

    return blueprint, walker_speed
