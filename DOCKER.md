#  Dockerized Chief-Keeper

# Build and Run the chief-keeper locally

## Prerequisite:
- docker installed: https://docs.docker.com/install/
- Git

## Installation
Clone the project and install required third-party packages:
```
git clone git@github.com:makerdao/chief-keeper.git
cd chief-keeper
git submodule update --init --recursive
```

## Configure, Build and Run:

## Configure
### Configure Envrionment variables
The chief-keeper requires the following environment variables in `env/envvars.sh` file.
Make a copy of the envvarstemplate.sh file, name it envvars.sh, and enter the required environment variables.

```
# DNS for ETH Parity Node, ex: myparity.node.com (default: `localhost')
SERVER_ETH_RPC_HOST=

# Ethereum blockchain to connect to, ex: (mainnet | kovan)
BLOCKCHAIN_NETWORK=

# Account used to pay for gas
ETH_FROM_ADDRESS=

# Chief Keeper Deployment Block Number
CHIEF_DEPLOYMENT_BLOCK=

# For ease of use, do not change the location of ETH account keys, note that account files should always be placed in the secrets directory of the chief-keeper, and files named as indicated.
ETH_ACCOUNT_KEY='key_file=/opt/keeper/chief-keeper/secrets/keystore.json,pass_file=/opt/keeper/chief-keeper/secrets/password.txt'
```

### Configure ETH account keys

Place unlocked keystore and password file for the account address under *secrets* directory. The names of the keystore should be *keystore.json*, and password file should be *password.txt*. If you name your secrets files something other than indicated, you will need to update the *ETH_ACCOUNT_KEY=* value, in envvars.sh, to reflect the change.

## Build
### Build the docker image locally
From within the `chief-keeper` directory, run the following command:
```
docker build --tag chief-keeper .
```

## Run
### Run the chief-keeper
Running the chief-keeper requires you to pass the environment file to the container, map a volume to the secrets directory to allow the chief-keeper to access your keystore files, and map a volume for the DB files.

From within the `chief-keeper` directory, run the following command:
```
docker run \
    --env-file env/envvars.sh \
    --volume "$(pwd)"/secrets:/opt/keeper/chief-keeper/secrets \
    --volume "$(pwd)"/chief_keeper/database:/opt/keeper/chief-keeper/chief_keeper/database \
    chief-keeper:latest
```

To run the container in the background, use the `-d` option.
```
docker run -d \
    --env-file env/envvars.sh \
    --volume "$(pwd)"/secrets:/opt/keeper/chief-keeper/secrets \
    --volume "$(pwd)"/chief_keeper/database:/opt/keeper/chief-keeper/chief_keeper/database \
    chief-keeper:latest
```