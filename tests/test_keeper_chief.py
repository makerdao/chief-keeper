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

import time
from typing import List

from web3 import Web3

from chief_keeper.database import SimpleDatabase
from chief_keeper.chief_keeper import ChiefKeeper
from chief_keeper.spell import DSSSpell

from pymaker import Address
from pymaker.deployment import DssDeployment
from pymaker.numeric import Wad

from tests.test_dss import mint_mkr
from bad_spell import DSSBadSpell

pytest.global_spell = {};

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
        assert len(listOrDict) == leng
    else:
        assert len(list(listOrDict.keys())) == leng

    for addr in addresses:
        assert addr in listOrDict


def print_out(testName: str):
    print("")
    print(f"{testName}")
    print("")

class TestChiefKeeper:

    def test_check_deployment(self, mcd: DssDeployment, keeper: ChiefKeeper):
        print_out("test_check_deployment")
        keeper.check_deployment()

    def test_check_eta(self, mcd: DssDeployment, keeper: ChiefKeeper):
        print_out("test_check_eta")

        keeper.initial_query()

        etas = keeper.database.db.get(doc_id=3)['upcoming_etas']
        hat = mcd.ds_chief.get_hat()
        verify([hat.address], etas, 1)

        keeper.check_eta()

        # Confirm that the spell was casted and that the database was updated
        assert DSSSpell(mcd.web3, Address(hat)).done() == True
        etas = keeper.database.db.get(doc_id=3)['upcoming_etas']
        verify([], etas, 0)


    def test_check_hat(self, mcd: DssDeployment, keeper: ChiefKeeper, guy_address: Address):
        print_out("test_check_hat")

        # Confirm the hat with the most approval is unchanged
        oldHat = mcd.ds_chief.get_hat()
        keeper.check_hat()
        newHat = mcd.ds_chief.get_hat()
        assert oldHat.address == newHat.address

        # Move the 2000 MKR vote from the last spell in test_database.py to new spell
        self.spell = DSSSpell.deploy(mcd.web3, mcd.pause.address, mcd.vat.address)
        assert mcd.ds_chief.vote_yays([self.spell.address.address]).transact(from_address=guy_address)

        keeper.check_hat()

        # Confirm that the hat has been lifted
        newerHat = mcd.ds_chief.get_hat()
        assert newerHat.address == self.spell.address.address

        # Confirm that the spell was scheduled
        assert self.spell.eta() != 0


    def test_check_eta_receipt(self, mcd: DssDeployment, keeper: ChiefKeeper, simpledb: SimpleDatabase, our_address: Address):
        print_out("test_check_eta_receipt")

        # clear out anything that came before
        keeper.check_hat()
        keeper.check_eta()

        # Give 1000 MKR to our_address
        amount = Wad.from_number(5000)
        mint_mkr(mcd.mkr, our_address, amount)
        assert mcd.mkr.balance_of(our_address) == amount

        # Lock MKR in DS-Chief
        assert mcd.mkr.approve(mcd.ds_chief.address).transact(from_address=our_address)
        assert mcd.ds_chief.lock(amount).transact(from_address=our_address)

        # Deploy spell
        spell = DSSBadSpell.deploy(mcd.web3)

        # Vote 5000 mkr on the spell
        assert mcd.ds_chief.vote_yays([spell.address.address]).transact(from_address=our_address)

        keeper.check_hat()

        block = mcd.web3.eth.blockNumber
        simpledb.update_db_etas(block)

        hat = mcd.ds_chief.get_hat()

        etas = keeper.database.db.get(doc_id=3)['upcoming_etas']
        verify([hat.address], etas, 1)

        keeper.check_eta()

        # Confirm that the spell was casted and that the database was updated
        # For the DSSBadSpell, the cast() call in non-conformant.  Usually
        # cast() will flip done to true, but in this broken spell it's modified
        # to not set done to true so we can test this bug and prevent
        # regressions.
        assert DSSBadSpell(mcd.web3, Address(hat)).done() == False
        etas = keeper.database.db.get(doc_id=3)['upcoming_etas']
        verify([], etas, 0)
