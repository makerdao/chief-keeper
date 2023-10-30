FROM python:3.8-buster

RUN groupadd -r keeper && useradd -d /home/keeper -m --no-log-init -r -g keeper keeper && \
    apt-get -y update && \
    apt-get -y install python3-pip jshon jq virtualenv pkg-config openssl libssl-dev autoconf libtool libsecp256k1-dev && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

COPY . /opt/keeper/chief-keeper

WORKDIR /opt/keeper/chief-keeper

RUN git submodule update --init --recursive && \
    pip3 install virtualenv && \
    ./install.sh

CMD ["./run-chief-keeper.sh"]
