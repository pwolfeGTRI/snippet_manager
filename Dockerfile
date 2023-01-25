ARG FROM_IMG
FROM ${FROM_IMG}

# upgrade pip to latest
RUN pip3 install --upgrade pip

# install skaimsginterface as a python package
COPY msg_interface/package /root/skaimsginterface_package
RUN cd /root/skaimsginterface_package && ./install_skaimsginterface.sh

# first install opencv contrib
RUN pip install --upgrade pip && pip install opencv-contrib-python

# install ffmpeg
# RUN apt update && apt install -y ffmpeg
ARG FFMPEG_VERSION=5.1.2
RUN apt update && apt install -y \
    git \
    build-essential \
    gcc \
    make \
    yasm \
    autoconf \
    automake \
    cmake \
    libtool \
    checkinstall \
    libmp3lame-dev \
    pkg-config \
    libunwind-dev \
    zlib1g-dev \
    libssl-dev
RUN apt-get update \
    && apt-get clean \
    && apt-get install -y --no-install-recommends \
    libc6-dev \
    libgdiplus \
    wget \
    software-properties-common
RUN wget https://www.ffmpeg.org/releases/ffmpeg-${FFMPEG_VERSION}.tar.gz && \
    tar -xzf ffmpeg-${FFMPEG_VERSION}.tar.gz; rm -r ffmpeg-${FFMPEG_VERSION}.tar.gz && \
    cd ./ffmpeg-${FFMPEG_VERSION} && \
    ./configure --enable-gpl --enable-libmp3lame --enable-decoder=mjpeg,png --enable-encoder=png --enable-openssl --enable-nonfree && \
    make && \
    make install

# install requirements.txt
COPY requirements.txt /root/requirements.txt
RUN cd /root &&  pip3 install -r requirements.txt && rm requirements.txt
