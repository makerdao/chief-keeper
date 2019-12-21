# This file is part of the Maker Keeper Framework.
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

import argparse
import logging
import sys
import time
from datetime import datetime, timezone
import types
import os
from typing import List

from web3 import Web3, HTTPProvider

from pymaker import Address, Contract, Transact
from pymaker.util import is_contract_at
from pymaker.numeric import Wad, Rad, Ray

class DSSSpell(Contract):
    """A client for the `DSPause` contract, which schedules function calls after a predefined delay.

    You can find the source code of the `DSSSpell` contract here:

    Attributes:
        web3: An instance of `Web` from `web3.py`.
        address: Ethereum address of the `DSSSpell` contract.
    """

    # This ABI and BIN was used from the McdIlkLineSpell.sol
    abi = Contract._load_abi(__name__, 'abi/DSSSpell.abi')
    bin = Contract._load_bin(__name__, 'abi/DSSSpell.bin')

    def __init__(self, web3: Web3, address: Address):
        assert (isinstance(web3, Web3))
        assert (isinstance(address, Address))

        self.web3 = web3
        self.address = address
        self._contract = self._get_contract(web3, self.abi, address)

    def done(self) -> bool:
        return self._contract.call().done()

    def eta(self) -> datetime:
        try:
            timestamp = self._contract.call().eta()
        except ValueError:
            timestamp = 0

        return datetime.utcfromtimestamp(timestamp)

    @staticmethod
    def deploy(web3: Web3, pauseAddress: Address):
        return DSSSpell(web3=web3, address=Contract._deploy(web3, DSSSpell.abi, DSSSpell.bin, [pauseAddress.address]))

    def schedule(self):
        return Transact(self, self.web3, self.abi, self.address, self._contract, 'schedule', [])

    def cast(self):
        return Transact(self, self.web3, self.abi, self.address, self._contract, 'cast', [])
