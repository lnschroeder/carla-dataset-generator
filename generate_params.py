import csv
import random
import sys
import hashlib

from syncworld import WEATHER_PRESETS


class Split(object):

    def __init__(self, name, maps, amt):
        # available maps: '01', '02', '03', '04', '05', '06', '07', '10HD'
        self.name = name
        self.maps = maps
        self.amt = amt


if __name__ == '__main__':
    seed = 1234567
    random.seed(seed)

    if len(sys.argv) != 2:
        exit('Specify a parameter filename. E.g.: \n    python3 generate_params.py params')
    filename = sys.argv[1] + '.csv'

    params = []
    splits = [
        Split('val', ['01', '02', '03', '04', '05', '06', '07'], 7),
        Split('test', ['01', '02', '03', '04', '05', '06', '07'], 7),
        Split('train', ['01', '02', '03', '04', '05', '06', '07'], 210),
    ]

    for split in splits:
        for i in range(split.amt):
            map_ = 'Town' + split.maps[i % len(split.maps)] + '_Opt'
            seed = random.randint(0, 100000)
            fps = 25  # minimal fps: 10 (see below)
            duration = 300  # in seconds
            n_vehicles = random.choice([100, 150, 200])
            n_walkers = random.choice([50, 100, 150, 200])
            weather = random.choice(list(WEATHER_PRESETS.keys()))
            speed_diff = random.randint(-60, 50)
            img_h = 128
            img_w = 128
            fov = 90
            cam_pitch = 0
            cam_yaw = 0
            cam_roll = 0
            cam_x = 1.5
            cam_y = 0
            cam_z = 2.4

            assert fps >= 10, "The framerate is too low!"  # https://carla.readthedocs.io/en/latest/adv_synchrony_timestep/#physics-substepping
            assert n_walkers >= 20, "Spawning too few walkers!"
            assert n_vehicles >= 20, "Spawning too few vehicles!"

            param = ['', split.name, map_, seed, fps, duration, n_vehicles, n_walkers, weather, speed_diff, img_h, img_w, fov, cam_pitch, cam_yaw, cam_roll, cam_x, cam_y, cam_z]
            hash_str = str([str(x) for x in param[1:]]).encode('utf-8')
            hash_str = hashlib.sha256(hash_str).hexdigest()
            param[0] = hash_str
            params.append(param)

    # params.sort(key=lambda x: x[1])  # Sorting by Town name (server does not have to load another world after each sample)

    with open(filename, mode='wt', encoding='utf-8') as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(['hash', 'split', 'map', 'seed', 'fps', 'duration', 'n_vehicles', 'n_walkers', 'weather', 'speed_diff', 'img_h', 'img_w', 'fov', 'cam_pitch', 'cam_yaw', 'cam_roll', 'cam_x', 'cam_y', 'cam_z'])
        writer.writerows(params)
