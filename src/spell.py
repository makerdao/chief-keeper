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

from tinydb import TinyDB, Query
from web3 import Web3, HTTPProvider

from src.database import SimpleDatabase

from pymaker import Address, Contract
from pymaker.util import is_contract_at
from pymaker.gas import DefaultGasPrice, FixedGasPrice
from pymaker.auctions import Flipper, Flapper, Flopper
from pymaker.keys import register_keys
from pymaker.lifecycle import Lifecycle
from pymaker.numeric import Wad, Rad, Ray
from pymaker.token import ERC20Token
from pymaker.deployment import DssDeployment
from pymaker.dss import Ilk, Urn

class DSSSpell(Contract):
    """A client for the `DSPause` contract, which schedules function calls after a predefined delay.

    You can find the source code of the `DSSSpell` contract here:

    Attributes:
        web3: An instance of `Web` from `web3.py`.
        address: Ethereum address of the `DSSSpell` contract.
    """

    # This ABI and BIN was used from the Mcd Ilk Line Spell
    # https://etherscan.io/address/0x3438Ae150d4De7F356251675B40B9863d4FD97F0
    abi = Contract._load_abi(__name__, 'abi/McdIlkLineSpell.abi')
    bin = Contract._load_bin(__name__, 'abi/McdIlkLineSpell.bin')

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

    def deploy(self, web3: Web3):
        return DSSSpell(web3=web3, address=Contract._deploy(web3, McdIlkLineSpell.abi, McdIlkLineSpell.bin, []))

    def schedule(self):
        return Transact(self, self.web3, self.abi, self.address, self._contract, 'schedule', [])

    def cast(self):
        return Transact(self, self.web3, self.abi, self.address, self._contract, 'cast', [])
