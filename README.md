# CARLA dataset generator
_CARLA dataset generator_ uses [CARLA simulator](https://carla.org/) to generate videos of a car driving around the simulation environment. Four visual modalities (RGB, optical flow, depth, instance segmentation) are extracted, as well as the motion data of all vehicles and pedestrians at every timestep

![RGB, optical flow, depth, instance segmentation](modalities.svg)

The dataset generator can be parameterized with a CSV file (see [generate_params.py](src/generate_params.py)) that contains a seed, the split name (train, test, validation), map name, framerate, duration, number of cars, number of pedestrians, weather and daytime, a speed limit factor, the cameras’ position, orientation, field of view, and resolution. The generator was designed to be fully deterministic.

One sample of the training set can be found at:
https://tubcloud.tu-berlin.de/s/5ygs7dbMjDJWtqX

> **Note**
> Please refer to my bachelor's thesis for details: [Evaluating multi-stream networks for
self-supervised representation learning](https://www.cv.tu-berlin.de/fileadmin/fg140/Main/Lehre/Master/bt_schroeder_blackened.pdf) 

## How to generate a CARLA dataset
1. Clone this repo
2. Go to the cloned folder
    ```bash
    cd <PATH_TO_THIS_REPO>
    ```
3. Get docker image with one of the following methods:
    ```bash
    #Pull image from dockerhub
    docker pull nschroeder/carla:0.9.13-v1
    
    #Compile image yourself
    wget https://carla-releases.s3.eu-west-3.amazonaws.com/Linux/AdditionalMaps_0.9.13.tar.gz
    docker build -t nschroeder/carla:0.9.13-v1 .
    ```
4. Edit `src/generate_params.py` which will later generate a `.csv` file, which defines all parameters for each sample. The current configuration creates the `default4.csv` which was used for the main dataset of this thesis.
5. Generate this `.csv`
    ```bash
    `docker run --rm -v <ABSOLUTE_PATH_TO_THIS_REPO>/src/:/mnt/scripts nschroeder/carla:0.9.13-v1 python3 generate_params.py <DATASET_NAME>`
    ```
6. Now a `<DATASET_NAME>.csv` should be in the `<ABSOLUTE_PATH_TO_THIS_REPO>`
7. Start the CARLA server with display or headless:
    ```bash
    # stop already running server containers  
    docker container stop csniklas && docker rm csniklas
        
    # with display
    docker run -it --privileged --gpus all --net=host --name=csniklas -e DISPLAY=$DISPLAY nschroeder/carla:0.9.13-v1 /home/carla/CarlaUE4.sh -nosound
        
    # without display
    docker run -it --restart=always --privileged --gpus=all --net=host --name=csniklas nschroeder/carla:0.9.13-v1 /home/carla/CarlaUE4.sh -RenderOffScreen -nosound
    ```
8. Open another terminal (also inside this repo folder)
9. Start the CARLA client:
    ```bash
    # stop already running client containers
    docker container stop ccniklas && docker rm ccniklas
    
    CODE_DIR=<ABSOLUTE_PATH_TO_THIS_REPO>/src/
    DATASET=<ABSOLUTE_PATH_TO_FOLDER_WHERE_DATASET_SHOULD_BE_SAVED>
    PARAM_NAME=<DATASET_NAME>
    
    docker run -it --net=host -v ${CODE_DIR}:/mnt/scripts -v ${DATASET}:/mnt/dataset -e PARAM_NAME=${PARAM_NAME} --name=ccniklas nschroeder/carla:0.9.13-v1 /bin/bash
    ```
10. Start datagenerator inside Dockercontainer
     ```bash
     ./auto_restart.sh client.py -f ${PARAM_NAME}.csv
     ```
11. The dataset will be written to the specified folder
12. Stop client and server
    ```bash
    docker container stop csniklas
    docker rm csniklas
    docker container stop ccniklas
    docker rm ccniklas
    ```

## Entrypoint to code
The `src/client.py` first gets called.
