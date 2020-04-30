##-------------------------------------------------------------------##
# Template file for environment variables used for docker deployment.
# see DOCKER.md
##-------------------------------------------------------------------##

# DNS for ETH Parity Node, ex: myparity.node.com (default: `localhost')
SERVER_ETH_RPC_HOST=

# Ethereum blockchain to connect to, ex: (mainnet | kovan)
BLOCKCHAIN_NETWORK=

# Account used to pay for gas
ETH_FROM_ADDRESS=

# For ease of use, do not change the location of ETH account keys, note that account files should always be placed in the secrets directory of the cage-keeper, and files named as indicated.
ETH_ACCOUNT_KEY=key_file=/opt/keeper/chief-keeper/secrets/keystore.json,pass_file=/opt/keeper/chief-keeper/secrets/password.txt

# Chief Keeper Deployment Block Number
CHIEF_DEPLOYMENT_BLOCK=