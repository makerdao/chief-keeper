#!/bin/bash

dir=`pwd`

secret_paths=(${ETH_ACCOUNT_KEY//,/ })

if [[ ! -f "$(echo ${secret_paths[0]} | awk -F'[=]' '{print $2}')" ]] && [[ ! -f "$(echo ${secret_paths[1]} | awk -F'[=]' '{print $2}')" ]]
then
  echo "No keystore files found. Running this container locally requires keys and a secrets volume mapping, see DOCKER.md."

  # get expected secret key paths
  for secret in ${secret_paths[@]}
  do
    if [[ $secret == *"key_file"* ]]; then
      key_file_location=$(echo $secret | awk -F'[=]' '{print $2}')
    fi
    if [[ $secret == *"pass_file"* ]]; then
      pass_file_location=$(echo $secret | awk -F'[=]' '{print $2}')
    fi
  done

  if [[ -n "${SECRET_KEY}" ]]; then
    touch ${key_file_location}
    echo $SECRET_KEY | sed 's/\\"/\"/g' >> ${key_file_location}
  else
    echo "No secret key to write to file."
  fi
  if [[ -n "${SECRET_PASS}" ]]; then
    touch pass_file_location
    echo $SECRET_PASS >> ${pass_file_location}
  else
    echo "No secret pass to write to file."
  fi

fi


exec $dir/bin/chief-keeper \
  --rpc-host "${SERVER_ETH_RPC_HOST}" \
  --network "${BLOCKCHAIN_NETWORK}" \
  --eth-from "${ETH_FROM_ADDRESS}" \
  --eth-key "${ETH_ACCOUNT_KEY}" \
  --chief-deployment-block "${CHIEF_DEPLOYMENT_BLOCK}"