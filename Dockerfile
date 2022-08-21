# -> nschroeder/carla:0.9.13-v1
FROM carlasim/carla:0.9.13
COPY AdditionalMaps_0.9.13.tar.gz  /home/carla/Import
RUN /home/carla/ImportAssets.sh
WORKDIR /mnt/scripts
USER root
RUN apt-get update && \
	apt-get install --no-install-recommends -y \
		software-properties-common \
		sudo \
		git \
		python3-pip \
		libjpeg-turbo8 \
		libtiff5-dev \
		libomp5 \
		wget
USER carla
RUN pip3 install --upgrade pip
RUN python3 -m pip --no-cache-dir install \
    carla \
    pyyaml \
    Pillow \
    numpy
WORKDIR /mnt/scripts
