class TrafficManager:
    def __init__(self, sync_world):
        self.tm = sync_world.client.get_trafficmanager(sync_world.tm_port)

        self.tm.set_global_distance_to_leading_vehicle(1.0)
        self.tm.global_percentage_speed_difference(sync_world.speed_diff)

        # make traffic manager deterministic
        self.tm.set_random_device_seed(sync_world.seed)
        self.tm.set_synchronous_mode(True)
