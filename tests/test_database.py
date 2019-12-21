# This file is part of Maker Keeper Framework.
#
# Copyright (C) 2019 KentonPrescott
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


import pytest

from datetime import datetime, timedelta, timezone
import time
from typing import List
import logging

from tinydb import TinyDB, Query
from web3 import Web3

from src.spell import DSSSpell
from src.database import SimpleDatabase

from pymaker import Address
from pymaker.approval import directly, hope_directly
from pymaker.auctions import Flapper, Flopper, Flipper
from pymaker.deployment import DssDeployment
from pymaker.dss import Collateral, Ilk, Urn
from pymaker.numeric import Wad, Ray, Rad
from pymaker.shutdown import ShutdownModule, End

from tests.test_auctions import create_debt, check_active_auctions, max_dart, simulate_bite
from tests.test_dss import mint_mkr, wrap_eth, frob, set_collateral_price


def time_travel_by(web3: Web3, seconds: int):
    assert(isinstance(web3, Web3))
    assert(isinstance(seconds, int))

    if "parity" in web3.version.node.lower():
        print(f"time travel unsupported by parity; waiting {seconds} seconds")
        time.sleep(seconds)
        # force a block mining to have a correct timestamp in latest block
        web3.eth.sendTransaction({'from': web3.eth.accounts[0], 'to': web3.eth.accounts[1], 'value': 1})
    else:
        web3.manager.request_blocking("evm_increaseTime", [seconds])
        # force a block mining to have a correct timestamp in latest block
        web3.manager.request_blocking("evm_mine", [])


def verify(addresses: List, listOrDict, leng: int):
    assert(isinstance(addresses, List))
    assert(isinstance(leng, int))

    if type(listOrDict) is list:
        assert len(list) == int
    else:
        assert len(list(listOrDict.keys())) == int

    for addr in addresses:
        assert addr in listOrDict


def print_out(testName: str):
    print("")
    print(f"{testName}")
    print("")

global_spell = "placeholder";

class TestSimpleDatabase:

    #TODO: Compartmentalize logic in pymaker/test_governance.py and import
    def test_setup(self, mcd: DssDeployment, our_address: Address, guy_address: Address):
        print_out("test_setup")

        amount = Wad.from_number(1000)
        mint_mkr(mcd.mkr, our_address, amount)
        assert mcd.mkr.balance_of(our_address) == amount

        guyAmount = Wad.from_number(2000)
        mint_mkr(mcd.mkr, guy_address, guyAmount)
        assert mcd.mkr.balance_of(guy_address) == guyAmount

        # Lock MKR in DS-Chief
        assert mcd.mkr.approve(mcd.ds_chief.address).transact(from_address=our_address)
        assert mcd.mkr.approve(mcd.ds_chief.address).transact(from_address=guy_address)
        assert mcd.ds_chief.lock(amount).transact(from_address=our_address)
        assert mcd.ds_chief.lock(guyAmount).transact(from_address=our_address)

        # Deploy spell
        self.spell = DSSSpell.deploy(mcd.web3, mcd.pause.address)

        # Vote for our address
        assert mcd.ds_chief.vote_yays([our_address.address, guy_address.address]).transact(from_address=our_address)
        assert mcd.ds_chief.vote_yays([self.spell.address]).transact(from_address=guy_address)

        # At this point there are two yays in the chief, one to our_address and the other to the spell address

        global_spell = self.spell


    def test_unpack_slate(self, mcd: DssDeployment, simpledb: SimpleDatabase, our_address: Address):
        print_out("test_unpack_slate")

        # unpack the first etch
        etches = mcd.ds_chief.past_etch(3)
        yays = simpledb.unpack_slate(etches[0], 3)
        verify_address([our_address.address, guy_address.address], yays, 2)


    def test_get_yays(self, mcd: DssDeployment, simpledb: SimpleDatabase, our_address: Address,  guy_address: Address):
        print_out("test_get_yays")

        yays = simpledb.get_yays(0, mcd.web3.eth.blockNumber)
        verify([our_address.address, guy_address.address, global_spell.address], yays, 3)


    def test_get_etas(self, mcd: DssDeployment, simpledb: SimpleDatabase, our_address: Address,  guy_address: Address):
        print_out("test_get_etas")

        yays = simpledb.get_yays(0, mcd.web3.eth.blockNumber)
        etas = simpledb.get_etas(yays, 0)

        verify([], etas, 0)


    def test_initial_query(self, mcd: DssDeployment, simpledb: SimpleDatabase, our_address: Address,  guy_address: Address):
        print_out("test_initial_query")

        simpledb.create()

        yays = simpledb.db.get(doc_id=2)["yays"]
        etas = simpledb.db.get(doc_id=3)["upcoming_etas"]

        verify([our_address.address, guy_address.address, global_spell.address], yays, 3)
        verify([], etas, 0)


    def test_yays_update(self, mcd: DssDeployment, simpledb: SimpleDatabase, our_address: Address,  guy_address: Address):
        print_out("test_yays_update")

        assert mcd.ds_chief.vote_yays([our_address.address]).transact(from_address=our_address)
        block = mcd.web3.eth.blockNumber

        # Updated vote should not delete yays that have had approval history
        simpledb.update_db_yays()
        yays = simpledb.db.get(doc_id=2)["yays"]
        DBblockNumber = self.db.get(doc_id=1)["last_block_checked_for_yays"]

        verify([our_address.address, guy_address.address, global_spell.address], yays, 3)
        assert DBblockNumber == block


    def test_etas_update(self, mcd: DssDeployment, simpledb: SimpleDatabase, our_address: Address,  guy_address: Address):
        print_out("test_yays_update")

        assert mcd.ds_chief.lift(global_spell.address).transact(from_address=our_address)
        assert global_spell.schedule().transact(from_address=our_address)
        block = mcd.web3.eth.blockNumber

        # Although pause.delay is 0, uddate_db_etas also catches etas that can be casted on the next block
        simpledb.update_db_etas(block)
        etas = simpledb.db.get(doc_id=2)['upcoming_etas']

        verify([global_spell.address], etas, 1)
