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

import json
import logging

import eth_utils
import pkg_resources

from web3 import Web3

from chief_keeper.utils.address import Address

from chief_keeper.utils.utils import bytes_to_hexstring, is_contract_at

class Contract:
    logger = logging.getLogger()

    @staticmethod
    def _deploy(web3: Web3, abi: list, bytecode: str, args: list) -> Address:
        assert(isinstance(web3, Web3))
        assert(isinstance(abi, list))
        assert(isinstance(bytecode, str))
        assert(isinstance(args, list))

        contract = web3.eth.contract(abi=abi, bytecode=bytecode)
        tx_hash = contract.constructor(*args).transact(
            transaction={'from': eth_utils.to_checksum_address(web3.eth.defaultAccount)})
        receipt = web3.eth.getTransactionReceipt(tx_hash)
        return Address(receipt['contractAddress'])

    @staticmethod
    def _get_contract(web3: Web3, abi: list, address: Address):
        assert(isinstance(web3, Web3))
        assert(isinstance(abi, list))
        assert(isinstance(address, Address))

        if not is_contract_at(web3, address):
            raise Exception(f"No contract found at {address}")

        return web3.eth.contract(abi=abi)(address=address.address)

    def _past_events(self, contract, event, cls, number_of_past_blocks, event_filter) -> list:
        block_number = contract.web3.eth.blockNumber
        return self._past_events_in_block_range(contract, event, cls, max(block_number-number_of_past_blocks, 0),
                                                block_number, event_filter)

    def _past_events_in_block_range(self, contract, event, cls, from_block, to_block, event_filter) -> list:
        assert(isinstance(from_block, int))
        assert(isinstance(to_block, int))
        assert(isinstance(event_filter, dict) or (event_filter is None))

        def _event_callback(cls, past):
            def callback(log):
                if past:
                    self.logger.debug(f"Past event {log['event']} discovered, block_number={log['blockNumber']},"
                                      f" tx_hash={bytes_to_hexstring(log['transactionHash'])}")
                else:
                    self.logger.debug(f"Event {log['event']} discovered, block_number={log['blockNumber']},"
                                      f" tx_hash={bytes_to_hexstring(log['transactionHash'])}")
                return cls(log)

            return callback

        result = contract.events[event].createFilter(fromBlock=from_block, toBlock=to_block,
                                                     argument_filters=event_filter).get_all_entries()

        return list(map(_event_callback(cls, True), result))

    @staticmethod
    def _load_abi(package, resource) -> list:
        return json.loads(pkg_resources.resource_string(package, resource))

    @staticmethod
    def _load_bin(package, resource) -> str:
        return str(pkg_resources.resource_string(package, resource), "utf-8")
