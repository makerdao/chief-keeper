#!/bin/bash
/Users/jrigor/repos/maker/chief-keeper/bin/chief-keeper \
  --rpc-host https://geth3.mainnet.makerops.services/rpc \
  --network 'mainnet' \
  --eth-from '0x8b4c184918947b52f615FC2aB350e092906b54CB' \
  --eth-key 'key_file=/Users/jrigor/repos/maker/chief-keeper/secrets/mainnet-keystore.json,pass_file=/Users/jrigor/repos/maker/chief-keeper/secrets/mainnet-password.txt' \
  --blocknative-api-key cc92ee09-8d9c-4db4-90a3-9ba180c70d42 \
  --chief-deployment-block 11327777