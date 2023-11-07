#!/bin/bash

#!/bin/bash

# Set the current working directory to the location of this script
dir=$(dirname "$(readlink -f "$0")")

# Split ETH_ACCOUNT_KEY into an array based on comma separator
IFS=',' read -ra secret_paths <<< "${ETH_ACCOUNT_KEY}"

# Check if the keystore files exist
if [[ ! -f "${secret_paths[0]}" ]] && [[ ! -f "${secret_paths[1]}" ]]; then
  echo "No keystore files found. Running this container locally requires keys and a secrets volume mapping, see DOCKER.md."


  # Get the expected secret key paths
  for secret in "${secret_paths[@]}"; do
    if [[ $secret == *"key_file"* ]]; then
      key_file_location=$(echo $secret | cut -d'=' -f2)
    elif [[ $secret == *"pass_file"* ]]; then
      pass_file_location=$(echo $secret | cut -d'=' -f2)
    fi
  done

  # Write the secret key to file if provided
  if [[ -n "${SECRET_KEY}" ]]; then
    echo -n "${SECRET_KEY}" > "${key_file_location}"
  fi

  # Write the secret pass to file if provided
  if [[ -n "${SECRET_PASS}" ]]; then
    echo -n "${SECRET_PASS}" > "${pass_file_location}"
  fi

fi

# Set a default RPC_HOST_TIMEOUT if not set
RPC_HOST_TIMEOUT="${RPC_HOST_TIMEOUT:-10}"

# Run the chief-keeper application
exec "${dir}/bin/chief-keeper" \
  --rpc-host "${SERVER_ETH_RPC_HOST}" \
  --rpc-timeout "${RPC_HOST_TIMEOUT}" \
  --network "${BLOCKCHAIN_NETWORK}" \
  --eth-from "${ETH_FROM_ADDRESS}" \
  --eth-key "${ETH_ACCOUNT_KEY}" \
  --chief-deployment-block "${CHIEF_DEPLOYMENT_BLOCK}" \
  --blocknative-api-key "${BLOCKNATIVE_API_KEY}"





# dir=`pwd`

# secret_paths=(${ETH_ACCOUNT_KEY//,/ })

# if [[ ! -f "$(echo ${secret_paths[0]} | awk -F'[=]' '{print $2}')" ]] && [[ ! -f "$(echo ${secret_paths[1]} | awk -F'[=]' '{print $2}')" ]]
# then
#   echo "No keystore files found. Running this container locally requires keys and a secrets volume mapping, see DOCKER.md."

#   # get expected secret key paths
#   for secret in ${secret_paths[@]}
#   do
#     if [[ $secret == *"key_file"* ]]; then
#       key_file_location=$(echo $secret | awk -F'[=]' '{print $2}')
#     fi
#     if [[ $secret == *"pass_file"* ]]; then
#       pass_file_location=$(echo $secret | awk -F'[=]' '{print $2}')
#     fi
#   done

#   if [[ -n "${SECRET_KEY}" ]]; then
#     touch ${key_file_location}
#     echo $SECRET_KEY | sed 's/\\"/\"/g' >> ${key_file_location}
#   else
#     echo "No secret key to write to file."
#   fi
#   if [[ -n "${SECRET_PASS}" ]]; then
#     touch pass_file_location
#     echo $SECRET_PASS >> ${pass_file_location}
#   else
#     echo "No secret pass to write to file."
#   fi

# fi

# if [[ -n "${RPC_HOST_TIMEOUT}" ]]; then
#   RPC_HOST_TIMEOUT=${RPC_HOST_TIMEOUT}
# else
#   RPC_HOST_TIMEOUT=10
# fi

# exec $dir/bin/chief-keeper \
#   --rpc-host "${SERVER_ETH_RPC_HOST}" \
#   --rpc-timeout "${RPC_HOST_TIMEOUT}" \
#   --network "${BLOCKCHAIN_NETWORK}" \
#   --eth-from "${ETH_FROM_ADDRESS}" \
#   --eth-key "${ETH_ACCOUNT_KEY}" \
#   --chief-deployment-block "${CHIEF_DEPLOYMENT_BLOCK}" \
#   --blocknative-api-key "${BLOCKNATIVE_API_KEY}"
