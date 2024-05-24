# This file is part of Maker Keeper Framework.
#
# Copyright (C) 2017-2019 reverendus, EdNoepel
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import logging
import pytest
from os import path

from unittest.mock import patch, MagicMock
from web3 import Web3, HTTPProvider

from pymaker import Address
from pymaker.auctions import Flipper, Flapper, Flopper
from pymaker.deployment import Deployment, DssDeployment
from pymaker.dss import Vat, Vow, Cat, Jug, Pot
from pymaker.shutdown import ShutdownModule, End
from pymaker.keys import register_keys

from chief_keeper.chief_keeper import ChiefKeeper
from chief_keeper.database import SimpleDatabase


@pytest.fixture(scope='session')
def new_deployment() -> Deployment:
    return Deployment()

@pytest.fixture()
def deployment(new_deployment: Deployment) -> Deployment:
    new_deployment.reset()
    return new_deployment

@pytest.fixture(scope="session")
def web3() -> Web3:
    # for local dockerized parity testchain
    web3 = Web3(HTTPProvider("http://0.0.0.0:8545"))
    web3.eth.defaultAccount = "0x50FF810797f75f6bfbf2227442e0c961a8562F4C"

    # Mock accounts and transaction methods
    web3.eth.accounts = [
        "0x50FF810797f75f6bfbf2227442e0c961a8562F4C",
        "0x9e1FfFaBdC50e54e030F6E5F7fC27c7Dd22a3F4e",
        "0x5BEB2D3aA2333A524703Af18310AcFf462c04723",
        "0x7fBe5C7C4E7a8B52b8aAA44425Fc1c0d0e72c2AA"
    ]

    web3.eth.sendTransaction = MagicMock()
    web3.eth.getBalance = MagicMock(return_value=1000000000000000000)  # 1 ETH
    web3.eth.blockNumber = 12345678

    register_keys(web3,
                  ["key_file=tests/config/keys/UnlimitedChain/key1.json,pass_file=/dev/null",
                   "key_file=tests/config/keys/UnlimitedChain/key2.json,pass_file=/dev/null",
                   "key_file=tests/config/keys/UnlimitedChain/key3.json,pass_file=/dev/null",
                   "key_file=tests/config/keys/UnlimitedChain/key4.json,pass_file=/dev/null",
                   "key_file=tests/config/keys/UnlimitedChain/key.json,pass_file=/dev/null"])

    # reduce logspew
    logging.getLogger("web3").setLevel(logging.INFO)
    logging.getLogger("urllib3").setLevel(logging.INFO)
    logging.getLogger("asyncio").setLevel(logging.INFO)

    assert len(web3.eth.accounts) > 3
    return web3

@pytest.fixture(scope="session")
def our_address(web3) -> Address:
    return Address(web3.eth.accounts[0])

@pytest.fixture(scope="session")
def guy_address(web3) -> Address:
    return Address(web3.eth.accounts[1])

@pytest.fixture(scope="session")
def keeper_address(web3) -> Address:
    return Address(web3.eth.accounts[2])

@pytest.fixture(scope="session")
def other_address(web3) -> Address:
    return Address(web3.eth.accounts[3])

@pytest.fixture(scope="session")
def zero_address() -> Address:
    return Address("0x0000000000000000000000000000000000000000")

@pytest.fixture(scope="session")
def deployment_address(web3) -> Address:
    # FIXME: Unsure why it isn't added to web3.eth.accounts list
    return Address("0x00a329c0648769A73afAc7F9381E08FB43dBEA72")

@pytest.fixture(scope="session")
def mcd(web3) -> DssDeployment:

    deployment = DssDeployment.from_network(web3=web3, network="testnet")
    validate_contracts_loaded(deployment)

    return deployment

@pytest.fixture(scope="session")
def keeper(mcd: DssDeployment, keeper_address: Address) -> ChiefKeeper:
    keeper = ChiefKeeper(args=args(f"--eth-from {keeper_address} --network testnet --rpc-primary-url https://localhost:8545 --rpc-backup-url https://localhost:8545"), web3=mcd.web3)
    assert isinstance(keeper, ChiefKeeper)
    keeper.web3 = mcd.web3  # Assign the mocked web3 instance
    return keeper

@pytest.fixture(scope="session")
def simpledb(web3: Web3, mcd: DssDeployment) -> SimpleDatabase:
    simpledb = SimpleDatabase(web3, 0, "testnet", mcd)
    assert isinstance(simpledb, SimpleDatabase)
    return simpledb

def args(arguments: str) -> list:
    return arguments.split()

def validate_contracts_loaded(deployment: DssDeployment):
    assert isinstance(deployment.vat, Vat)
    assert deployment.vat.address is not None
    assert isinstance(deployment.vow, Vow)
    assert deployment.vow.address is not None
    assert isinstance(deployment.cat, Cat)
    assert deployment.cat.address is not None
    assert isinstance(deployment.jug, Jug)
    assert deployment.jug.address is not None
    assert isinstance(deployment.flapper, Flapper)
    assert deployment.flapper.address is not None
    assert isinstance(deployment.flopper, Flopper)
    assert deployment.flopper.address is not None
    assert isinstance(deployment.pot, Pot)
    assert deployment.pot.address is not None
    assert isinstance(deployment.end, End)
    assert deployment.end.address is not None
    assert isinstance(deployment.esm, ShutdownModule)
    assert deployment.esm.address is not None
