# This file is part of Maker Keeper Framework.
#
# Copyright (C) 2017-2018 reverendus
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
import re
from threading import Lock
from weakref import WeakKeyDictionary


from web3 import Web3
from web3._utils.contracts import get_function_info, encode_abi

from chief_keeper.utils.utils import bytes_to_hexstring

filter_threads = []
endpoint_behavior = WeakKeyDictionary()
next_nonce = {}
transaction_lock = Lock()
logger = logging.getLogger()

class Calldata:
    """Represents Ethereum calldata.

    Attributes:
        value: Calldata as either a string starting with `0x`, or as bytes.
    """
    def __init__(self, value):
        if isinstance(value, str):
            assert(value.startswith('0x'))
            self.value = value

        elif isinstance(value, bytes):
            self.value = bytes_to_hexstring(value)

        else:
            raise Exception(f"Unable to create calldata from '{value}'")

    @classmethod
    def from_signature(cls, web3: Web3, fn_sign: str, fn_args: list):
        """ Allow to create a `Calldata` from a function signature and a list of arguments.

        :param fn_sign: the function signature ie. "function(uint256,address)"
        :param fn_args: arguments to the function ie. [123, "0x00...00"]
        """
        assert isinstance(fn_sign, str)
        assert isinstance(fn_args, list)

        fn_split = re.split('[(),]', fn_sign)
        fn_name = fn_split[0]
        fn_args_type = [{"type": type} for type in fn_split[1:] if type]

        fn_abi = {"type": "function", "name": fn_name, "inputs": fn_args_type}
        fn_abi, fn_selector, fn_arguments = get_function_info("test", abi_codec=web3.codec, fn_abi=fn_abi, args=fn_args)

        calldata = encode_abi(web3, fn_abi, fn_arguments, fn_selector)

        return cls(calldata)

    @classmethod
    def from_contract_abi(cls, web3: Web3, fn_sign: str, fn_args: list, contract_abi):
        """ Create a `Calldata` according to the given contract abi """
        assert isinstance(web3, Web3)
        assert isinstance(fn_sign, str)
        assert isinstance(fn_args, list)

        fn_split = re.split('[(),]', fn_sign)
        fn_name = fn_split[0]

        fn_abi, fn_selector, fn_arguments = get_function_info(fn_name, abi_codec=web3.codec, contract_abi=contract_abi, args=fn_args)
        calldata = encode_abi(web3, fn_abi, fn_arguments, fn_selector)

        return cls(calldata)

    def as_bytes(self) -> bytes:
        """Return the calldata as a byte array."""
        return bytes.fromhex(self.value.replace('0x', ''))

    def __str__(self):
        return f"{self.value}"

    def __repr__(self):
        return f"Calldata('{self.value}')"

    def __hash__(self):
        return self.value.__hash__()

    def __eq__(self, other):
        assert(isinstance(other, Calldata))