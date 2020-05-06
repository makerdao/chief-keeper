#!/usr/bin/env bash

set -e

function message() {
    echo
    echo -----------------------------------
    echo "$@"
    echo -----------------------------------
    echo
}

ENVIRONMENT=$1
REGION=$2

if [ "$ENVIRONMENT" == "prod" ]; then
  TAG=latest
else
   message UNKNOWN ENVIRONMENT
fi

if [ -z "$ENVIRONMENT" ]; then
  echo 'You must specifiy an envionrment (bash build-deploy.sh <ENVIRONMENT>).'
  echo 'Allowed values are "staging" or "prod"'
  exit 1
fi


# build image
message BUILDING IMAGE
docker build -t "$TRAVIS_REPO_SLUG:$TAG" .
# docker login
echo "$DOCKER_PASSWORD" | docker login --username "$DOCKER_USER" --password-stdin
# docker push
docker push "$TRAVIS_REPO_SLUG:$TAG"


# service deploy
if [ "$ENVIRONMENT" == "prod" ]; then
  message DEPLOYING MAINNET
  aws ecs update-service --cluster chief-keeper-mainnet-cluster --service chief-keeper-mainnet-service --force-new-deployment --endpoint https://ecs.$REGION.amazonaws.com --region $REGION

  message DEPLOYING KOVAN
  aws ecs update-service --cluster chief-keeper-kovan-cluster --service chief-keeper-kovan-service --force-new-deployment --endpoint https://ecs.$REGION.amazonaws.com --region $REGION

else
   message UNKNOWN ENVIRONMENT
fi