import os.path
import random
import argparse
import logging
import shutil

import carla
import csv
import yaml
import collections
import time
from pprint import pprint

from syncworld import SyncWorld


def get_params_data(path):
    columns = collections.OrderedDict()
    n_rows = 0

    # read csv to dict
    with open(path) as params_file:
        reader = csv.reader(params_file)
        headers = next(reader, None)
        for header in headers:
            columns[header] = []

        for row in reader:
            n_rows += 1
            for header, value in zip(headers, row):
                columns[header].append(value)

    # fill missing parameters with the ones from the previous line
    for header in columns:
        prev_value = ''
        for row, value in enumerate(columns[header]):
            if value == '':
                columns[header][row] = prev_value
            else:
                prev_value = value

    return n_rows, columns


def write_sample_info(path, data, finish=False):
    si_path = os.path.join(path, '_sample_info.yml')
    if os.path.exists(si_path):
        with open(si_path, mode='r') as yml_file:
            old_data = yaml.safe_load(yml_file)
        old_data.update(data)
        data = old_data

    with open(si_path, mode='w') as yml_file:
        yaml.safe_dump(data, yml_file)

    if finish:
        os.rename(si_path, os.path.join(path, 'sample_info.yml'))


def write_actor_info(path, frame, data):
    with open(os.path.join(path, '%08d.csv' % frame), mode='w') as csv_file:
        csv_writer = csv.writer(csv_file, delimiter=',')
        csv_writer.writerows(data)


def main():
    dataset_path = os.path.join(args.dataset_path, *args.params_file.split('.')[:-1])
    os.makedirs(dataset_path, exist_ok=True)
    shutil.copyfile(args.params_file, os.path.join(dataset_path, 'params.csv'))
    client = carla.Client('localhost', 2000)
    client.set_timeout(10.0)
    world = client.get_world()
    original_settings = world.get_settings()  # makes server async after client disconnects

    pprint(sorted(client.get_available_maps()))
    try:
        n_samples, params = get_params_data(args.params_file)
        if args.end_row > n_samples:
            logging.error("Only %d samples are defined in %s, but end_row argument was %d" % (n_samples, args.params_file, args.end_row))
            args.end_row = -1
        if args.end_row == -1:
            args.end_row = n_samples
        for i in range(args.start_row-1, args.end_row):
            start = time.time()

            # initialize paramters
            split = params['split'][i]
            map_name = params['map'][i]
            fps = int(params['fps'][i])
            duration = int(params['duration'][i])
            seed = int(params['seed'][i])
            n_vehicles = int(params['n_vehicles'][i])
            n_walkers = int(params['n_walkers'][i])
            img_h, img_w = int(params['img_h'][i]), int(params['img_w'][i])
            fov = float(params['fov'][i])
            cam_x, cam_y, cam_z = float(params['cam_x'][i]), float(params['cam_y'][i]), float(params['cam_z'][i])
            cam_pitch, cam_yaw, cam_roll = float(params['cam_pitch'][i]), float(params['cam_yaw'][i]), float(params['cam_roll'][i])
            cam_transform = carla.Transform(carla.Location(x=cam_x, y=cam_y, z=cam_z),
                                            carla.Rotation(pitch=cam_pitch, yaw=cam_yaw, roll=cam_roll))
            weather_name = params['weather'][i]
            speed_diff = float(params['speed_diff'][i])
            hash_str = params['hash'][i]
            sample_path = os.path.join(dataset_path, split, map_name, hash_str, '')

            print('')
            logging.info('%d/%d Load world: %s' % (i+1, n_samples, [split, map_name, hash_str, fps, duration, seed, n_vehicles, n_walkers, weather_name, speed_diff,
                                                                    [img_h, img_w], fov, [cam_x, cam_y, cam_z], [cam_pitch, cam_yaw, cam_roll],
                                                                    sample_path]))

            if os.path.exists(sample_path):
                if os.path.exists(os.path.join(sample_path, 'sample_info.yml')):
                    logging.info('Such a sample already exists (seed from params). Skipping above sample and continue with next sample ...')
                    continue
                else:
                    logging.warning('sample_info.yml does not exist or is incomplete. Overwriting sample ...')
                    shutil.rmtree(sample_path)

            os.makedirs(os.path.dirname(sample_path), exist_ok=True)

            actor_path = os.path.join(sample_path, 'actors')
            os.makedirs(actor_path, exist_ok=True)

            ignore_ticks = 3 * fps  # ignore first 3 seconds, because cars fall and settle at the beginning
            frames = duration * fps  # amount of ticks that should be simulated/captured
            random.seed(seed)

            # make simulation sync and deterministic
            settings = world.get_settings()
            settings.synchronous_mode = True
            settings.fixed_delta_seconds = 1.0/fps
            settings.deterministic_ragdolls = True
            settings.max_substep_delta_time = 0.01
            settings.max_substeps = 10
            world.apply_settings(settings)

            with SyncWorld(client, sample_path, map_name, seed, fps, img_h, img_w, fov, cam_transform, n_vehicles, n_walkers, weather_name, speed_diff, args.tm_port) as sync_world:
                write_sample_info(sample_path, {
                    'split': split,
                    '_hash': hash_str,
                    '_actor_id': sync_world.op.actor.id,
                    'map_name': map_name,
                    'fps': fps,
                    'duration': duration,
                    'img_h': img_h,
                    'img_w': img_w,
                    'fov': fov,
                    'cam_pitch': cam_pitch,
                    'cam_yaw': cam_yaw,
                    'cam_roll': cam_roll,
                    'cam_x': cam_x,
                    'cam_y': cam_y,
                    'cam_z': cam_z,
                    'seed': seed,
                    'n_vehicles': n_vehicles,
                    'n_walkers': n_walkers,
                    '_n_vehicles_actual': len(sync_world.vehicles),
                    '_n_walkers_actual': len(sync_world.walkers),
                    'weather': weather_name,
                    'speed_diff': speed_diff
                })

                for frame in range(frames + ignore_ticks):
                    meta_data, actor_data, cam_data, snapshot = sync_world.tick(1.0)

                    if frame < ignore_ticks:
                        continue

                    sync_world.meta_data.append(meta_data)
                    sync_world.op.save_cam_data(*cam_data)
                    write_actor_info(actor_path, sync_world.frame, actor_data)

            write_sample_info(sample_path, {'time': time.time() - start}, finish=True)
            logging.info('Time to process: {}'.format(time.time() - start))
    finally:
        world.apply_settings(original_settings)


if __name__ == '__main__':
    def check_seed(value):
        seed_value = int(value)
        # only 6 digits are reserved in the image file name
        if seed_value <= 0 or seed_value >= 1000000:
            raise argparse.ArgumentTypeError("%s is too small or too big for a seed" % value)
        return seed_value

    try:
        argparser = argparse.ArgumentParser(description=__doc__)

        argparser.add_argument(
            '-s', '--start-row',
            metavar='S',
            default=1,
            type=int,
            help='row of params.csv to start - 1-indexing with (default: 1)')
        argparser.add_argument(
            '-e', '--end-row',
            metavar='E',
            default=-1,
            type=int,
            help='row of params.csv to end - 1-indexing - inclusive. with (default: -1)')
        argparser.add_argument(
            '-d', '--duration',
            metavar='D',
            default=10,
            type=int,
            help='duration in seconds the simulation should run for (default: 10)')
        argparser.add_argument(
            '--tm-port',
            metavar='P',
            default=8000,
            type=int,
            help='port to communicate with TM (default: 8000)')
        argparser.add_argument(
            '-f', '--params-file',
            metavar='F',
            default='params.csv',
            type=str,
            help='file path for parameters (default: params.csv)')
        argparser.add_argument(
            '-p', '--dataset-path',
            metavar='P',
            default='/mnt/dataset',
            type=str,
            help='file path for parameters (default: params.csv)')

        args = argparser.parse_args()

        logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.INFO)
        main()
    except KeyboardInterrupt:
        pass
    except RuntimeError:
        exit(1)
    else:
        print('\ndone.')
