##-------------------------------------------------------------------##
# Template file for environment variables used for docker deployment.
# see DOCKER.md
##-------------------------------------------------------------------##

# DNS for ETH Parity Node, ex: myparity.node.com (default: `localhost')
PRIMARY_ETH_RPC_HOST=<REPLACE_WITH_RPC_URL>
BACKUP_ETH_RPC_HOST=<REPLACE_WITH_BACKUP_RPC_URL>

# Ethereum blockchain to connect to, ex: (mainnet | kovan)
BLOCKCHAIN_NETWORK=mainnet

# Account used to pay for gas
ETH_FROM_ADDRESS=<REPLACE_WITH_ETH_ADDRESS>

# For ease of use, do not change the location of ETH account keys, note that account files should always be placed in the secrets directory of the cage-keeper, and files named as indicated.
ETH_ACCOUNT_KEY=key_file=/opt/keeper/chief-keeper/secrets/mainnet-keystore.json,pass_file=/opt/keeper/chief-keeper/secrets/mainnet-password.txt

# Chief Keeper Deployment Block Number
CHIEF_DEPLOYMENT_BLOCK=11327777

BLOCKNATIVE_API_KEY=<REPLACE_WITH_BLOCKNATIVE_KEY>