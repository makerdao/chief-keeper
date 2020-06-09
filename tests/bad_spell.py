# This file is part of the Maker Keeper Framework.
#
# Copyright (C) 2020 KentonPrescott
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

from datetime import datetime

from web3 import Web3

from pymaker import Address, Contract, Transact


class DSSBadSpell(Contract):
    """A client for the `DSSBadSpell` contract, which houses logic that makes changes to the Maker Protocol.

    You can find the source code of the `DSSBadSpell` contract here:

    Attributes:
        web3: An instance of `Web` from `web3.py`.
        address: Ethereum address of the `DSSBadSpell` contract.
    """

    abi = Contract._load_abi(__name__, 'abi/DSSBadSpell.abi')
    bin = Contract._load_bin(__name__, 'abi/DSSBadSpell.bin')

    def __init__(self, web3: Web3, address: Address):
        assert (isinstance(web3, Web3))
        assert (isinstance(address, Address))

        self.web3 = web3
        self.address = address
        self._contract = self._get_contract(web3, self.abi, address)

    def done(self) -> bool:
        return self._contract.functions.done().call()

    def eta(self) -> datetime:
        try:
            timestamp = self._contract.functions.eta().call()
        except ValueError:
            timestamp = 0

        return datetime.utcfromtimestamp(timestamp)

    @staticmethod
    def deploy(web3: Web3):
        return DSSBadSpell(web3=web3, address=Contract._deploy(web3, DSSBadSpell.abi, DSSBadSpell.bin, []))

    def schedule(self):
        return Transact(self, self.web3, self.abi, self.address, self._contract, 'schedule', [])

    def cast(self):
        return Transact(self, self.web3, self.abi, self.address, self._contract, 'cast', [])
