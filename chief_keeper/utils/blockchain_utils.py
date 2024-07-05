
# This file is part of the Maker Keeper Framework.

# It contains utility functions to handle the initialization and connection
# to an Ethereum blockchain node. The functions include methods for connecting
# to primary and backup nodes, and configuring the Web3 connection.
#
# Functions:
# - initialize_blockchain_connection: Initializes the blockchain connection using primary and backup nodes.
# - connect_to_primary_node: Connects to the primary Ethereum node.
# - connect_to_backup_node: Connects to the backup Ethereum node.
# - connect_to_node: Connects to an Ethereum node given its URL and timeout settings.
# - configure_web3: Configures the Web3 connection with a private key and logs the connection status.
#
# Usage:
# Call the initialize function: initialize_blockchain_connection(self)
#
# Dependencies:
# - web3: Web3.py library to interact with Ethereum.
# - web3.exceptions: Exceptions raised by the Web3.py library.
# - urllib.parse: Used to parse the URL of the Ethereum node.
# - logging: Standard Python logging library.
# - .register_keys: Custom function to register Ethereum keys with Web3.


import logging
from urllib.parse import urlparse
from web3 import Web3, HTTPProvider
from web3.exceptions import TimeExhausted
from .register_keys import register_keys

logger = logging.getLogger()

def initialize_blockchain_connection(keeper):
    """Initialize connection with Ethereum node."""
    if not connect_to_primary_node(keeper):
        logger.info("Switching to backup node.")
        if not connect_to_backup_node(keeper):
            logger.critical(
                "Error: Couldn't connect to the primary and backup Ethereum nodes."
            )

def connect_to_primary_node(keeper):
    """Connect to the primary Ethereum node"""
    return connect_to_node(
        keeper, keeper.arguments.rpc_primary_url, keeper.arguments.rpc_primary_timeout, "primary"
    )

def connect_to_backup_node(keeper):
    """Connect to the backup Ethereum node"""
    return connect_to_node(
        keeper, keeper.arguments.rpc_backup_url, keeper.arguments.rpc_backup_timeout, "backup"
    )

def connect_to_node(keeper, rpc_url, rpc_timeout, node_type):
    """Connect to an Ethereum node"""
    try:
        _web3 = Web3(HTTPProvider(rpc_url, {"timeout": rpc_timeout}))
    except (TimeExhausted, Exception) as e:
        logger.error(f"Error connecting to Ethereum node: {e}")
        return False
    else:
        if _web3.is_connected():
            keeper.web3 = _web3
            keeper.node_type = node_type
            return configure_web3(keeper)
    return False

def configure_web3(keeper):
    """Configure Web3 connection with private key"""
    try:
        keeper.web3.eth.defaultAccount = keeper.arguments.eth_from
        register_keys(keeper.web3, keeper.arguments.eth_key)
    except Exception as e:
        logger.error(f"Error configuring Web3: {e}")
        return False
    else:
        node_hostname = urlparse(keeper.web3.provider.endpoint_uri).hostname
        logger.info(f"Connected to Ethereum node at {node_hostname}")
        return True
