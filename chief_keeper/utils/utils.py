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

import asyncio

from web3 import Web3

from chief_keeper.utils.big_number import Wad


def chain(web3: Web3) -> str:
    block_0 = web3.eth.getBlock(0)['hash']
    if block_0 == "0xd4e56740f876aef8c010b86a40d5f56745a118d0906a34e69aec8c0db1cb8fa3":
        return "ethlive"
    elif block_0 == "0xa3c565fc15c7478862d50ccd6561e3c06b24cc509bf388941c25ea985ce32cb9":
        return "kovan"
    elif block_0 == "0x41941023680923e0fe4d74a34bdac8141f2540e3ae90623718e47d66d1ca4a2d":
        return "ropsten"
    elif block_0 == "0x0cd786a2425d16f152c658316c423e6ce1181e15c3295826d7c9904cba9ce303":
        return "morden"
    else:
        return "unknown"


def http_response_summary(response) -> str:
    text = response.text.replace('\r', '').replace('\n', '')[:2048]
    return f"{response.status_code} {response.reason} ({text})"


# CAUTION: Used by Transact class, this breaks applications running their own asyncio event loop.
def synchronize(futures) -> list:
    if len(futures) > 0:
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(asyncio.gather(*futures, loop=loop))
        finally:
            loop.close()
    else:
        return []


def eth_balance(web3: Web3, address) -> Wad:
    return Wad(web3.eth.getBalance(address.address))


def is_contract_at(web3: Web3, address):
    code = web3.eth.getCode(address.address)
    return (code is not None) and (code != "0x") and (code != "0x0") and (code != b"\x00") and (code != b"")


def int_to_bytes32(value: int) -> bytes:
    assert(isinstance(value, int))
    return value.to_bytes(32, byteorder='big')


def bytes_to_int(value) -> int:
    if isinstance(value, bytes) or isinstance(value, bytearray):
        return int.from_bytes(value, byteorder='big')
    elif isinstance(value, str):
        b = bytearray()
        b.extend(map(ord, value))
        return int.from_bytes(b, byteorder='big')
    else:
        raise AssertionError


def bytes_to_hexstring(value) -> str:
    if isinstance(value, bytes) or isinstance(value, bytearray):
        return "0x" + "".join(map(lambda b: format(b, "02x"), value))
    elif isinstance(value, str):
        b = bytearray()
        b.extend(map(ord, value))
        return "0x" + "".join(map(lambda b: format(b, "02x"), b))
    else:
        raise AssertionError


def hexstring_to_bytes(value: str) -> bytes:
    assert(isinstance(value, str))
    assert(value.startswith("0x"))
    return Web3.toBytes(hexstr=value)

