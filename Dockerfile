# Use an official Python runtime as a parent image
FROM python:3.8-buster

# Add user and group for running the application
RUN groupadd -r keeper && useradd -d /home/keeper -m --no-log-init -r -g keeper keeper && \
    apt-get update -y && \
    apt-get install -y jshon jq pkg-config openssl libssl-dev autoconf libtool libsecp256k1-dev && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container to /opt/keeper/chief-keeper
WORKDIR /opt/keeper/chief-keeper

# Copy the rest of the application's code into the container
COPY . .

# Install submodules
RUN git submodule update --init --recursive

# Install any needed packages specified in requirements.txt
# First copy only the requirements.txt to leverage Docker cache
COPY requirements.txt ./
RUN pip3 install --no-cache-dir -r requirements.txt

# Run run-chief-keeper.sh when the container launches
CMD ["/bin/bash", "-c", "./run-chief-keeper.sh"]

