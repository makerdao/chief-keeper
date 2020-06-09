#!/bin/bash

# Remove the testnet database
rm chief_keeper/database/db_testnet.json

# Pull the docker image
docker pull makerdao/testchain-pymaker:unit-testing

# Start the docker image and wait for parity to initialize
pushd ./lib/pymaker
docker-compose up -d
sleep 2
popd

virtualenv --python=`which python3` _virtualenv
. _virtualenv/bin/activate

PYTHONPATH=$PYTHONPATH:./lib/pymaker:./ py.test \
    -s \
    --cov=chief_keeper \
    --cov-report=term \
    tests/ $@
TEST_RESULT=$?

echo Stopping container
pushd ./lib/pymaker
docker-compose down
popd

exit $TEST_RESULT
