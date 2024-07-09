# This module provides functionality for securely managing Ethereum private keys 
# and configuring the Web3.py instance to use these keys for signing and sending 
# transactions. It includes functions to register multiple keys from key files, 
# decrypt them using passwords, and store them for automatic transaction signing.
#
# Functions:
# - register_keys: Registers multiple keys.
# - register_key: Registers a single key.
# - register_key_file: Registers a key from a file, decrypting it with a password.
# - get_private_key: Retrieves a private key as a hex string.
# - register_private_key: Registers a private key directly.
#
# Usage:
# 1. Initialize a Web3 instance connected to an Ethereum node.
# 2. Call register_keys with the Web3 instance and a list of key strings.
# 3. The keys can be in the format key_file=path/to/keyfile,pass_file=path/to/passfile.
# 4. The Web3 instance can then sign and send transactions automatically using the registered accounts.
#
# Example:
# from web3 import Web3
# web3 = Web3(Web3.HTTPProvider('http://localhost:8545'))
# keys = ['key_file=/path/to/keyfile1,pass_file=/path/to/passfile1', 'key_file=/path/to/keyfile2']
# register_keys(web3, keys)



import getpass
from typing import Optional, List

from eth_account import Account
from web3 import Web3
from web3.middleware import construct_sign_and_send_raw_middleware
from chief_keeper.utils.address import Address

_registered_accounts = {}

def register_keys(web3: Web3, keys: Optional[List[str]]) -> None:
    for key in keys or []:
        register_key(web3, key)

def register_key(web3: Web3, key: str) -> None:
    assert isinstance(web3, Web3)

    parsed = {var: val for var, val in (p.split("=") for p in key.split(","))}
    register_key_file(web3, parsed.get('key_file'), parsed.get('pass_file'))

def register_key_file(web3: Web3, key_file: str, pass_file: Optional[str] = None) -> None:
    assert isinstance(web3, Web3)
    assert isinstance(key_file, str)
    assert isinstance(pass_file, str) or pass_file is None

    with open(key_file) as key_file_open:
        read_key = key_file_open.read()
        if pass_file:
            with open(pass_file) as pass_file_open:
                read_pass = pass_file_open.read().strip()
        else:
            read_pass = getpass.getpass(prompt=f"Password for {key_file}: ")

        private_key = Account.decrypt(read_key, read_pass)
        register_private_key(web3, private_key)

def get_private_key(web3: Web3, key: str) -> str:
    assert isinstance(web3, Web3)
    assert isinstance(key, str)

    parsed = {var: val for var, val in (p.split("=") for p in key.split(","))}
    with open(parsed.get('key_file')) as key_file_open:
        read_key = key_file_open.read()
        if parsed.get('pass_file'):
            with open(parsed.get('pass_file')) as pass_file_open:
                read_pass = pass_file_open.read().strip()
        else:
            read_pass = getpass.getpass(prompt=f"Password for {parsed.get('key_file')}: ")

        private_key = Account.decrypt(read_key, read_pass).hex()
        return private_key

def register_private_key(web3: Web3, private_key: bytes) -> None:
    assert isinstance(web3, Web3)

    account = Account.from_key(private_key)
    _registered_accounts[(web3, Address(account.address))] = account
    web3.middleware_onion.add(construct_sign_and_send_raw_middleware(account))
