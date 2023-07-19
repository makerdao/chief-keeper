FROM python:3.7-buster

RUN groupadd -r keeper && useradd -d /home/keeper -m --no-log-init -r -g keeper keeper && \
    apt-get -y update && \
    apt-get -y install python3-pip jshon jq virtualenv pkg-config openssl libssl-dev autoconf libtool libsecp256k1-dev && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/keeper

COPY . /opt/keeper

RUN git submodule update --init --recursive && \
    pip3 install virtualenv && \
    ./install.sh

WORKDIR /opt/keeper/chief-keeper
CMD ["./run-chief-keeper.sh"]
