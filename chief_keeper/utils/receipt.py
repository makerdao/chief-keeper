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

from hexbytes import HexBytes
from web3._utils.events import get_event_data

from eth_abi.codec import ABICodec
from eth_abi.registry import registry as default_registry

from chief_keeper.utils.address import Address
from chief_keeper.utils.big_number import Wad

class Receipt:
    """Represents a receipt for an Ethereum transaction.

    Attributes:
        raw_receipt: Raw receipt received from the Ethereum node.
        transaction_hash: Hash of the Ethereum transaction.
        gas_used: Amount of gas used by the Ethereum transaction.
        transfers: A list of ERC20 token transfers resulting from the execution
            of this Ethereum transaction. Each transfer is an instance of the
            :py:class:`pymaker.Transfer` class.
        result: Transaction-specific return value (i.e. new order id for Oasis
            order creation transaction).
        successful: Boolean flag which is `True` if the Ethereum transaction
            was successful. We consider transaction successful if the contract
            method has been executed without throwing.
    """
    def __init__(self, receipt):
        self.raw_receipt = receipt
        self.transaction_hash = receipt['transactionHash']
        self.gas_used = receipt['gasUsed']
        self.transfers = []
        self.result = None

        receipt_logs = receipt['logs']
        if (receipt_logs is not None) and (len(receipt_logs) > 0):
            self.successful = True
            for receipt_log in receipt_logs:
                if len(receipt_log['topics']) > 0:
                    # $ seth keccak $(seth --from-ascii "Transfer(address,address,uint256)")
                    # 0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef
                    if receipt_log['topics'][0] == HexBytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'):
                        from pymaker.token import ERC20Token
                        transfer_abi = [abi for abi in ERC20Token.abi if abi.get('name') == 'Transfer'][0]
                        codec = ABICodec(default_registry)
                        try:
                            event_data = get_event_data(codec, transfer_abi, receipt_log)
                            self.transfers.append(Transfer(token_address=Address(event_data['address']),
                                                           from_address=Address(event_data['args']['from']),
                                                           to_address=Address(event_data['args']['to']),
                                                           value=Wad(event_data['args']['value'])))
                        # UniV3 Mint logIndex: 3 has an NFT mint of 1, from null, to a given address, but only 2 types (address, address)
                        except LogTopicError:
                            continue

                    # $ seth keccak $(seth --from-ascii "Mint(address,uint256)")
                    # 0x0f6798a560793a54c3bcfe86a93cde1e73087d944c0ea20544137d4121396885
                    if receipt_log['topics'][0] == HexBytes('0x0f6798a560793a54c3bcfe86a93cde1e73087d944c0ea20544137d4121396885'):
                        from pymaker.token import DSToken
                        transfer_abi = [abi for abi in DSToken.abi if abi.get('name') == 'Mint'][0]
                        codec = ABICodec(default_registry)
                        event_data = get_event_data(codec, transfer_abi, receipt_log)
                        self.transfers.append(Transfer(token_address=Address(event_data['address']),
                                                       from_address=Address('0x0000000000000000000000000000000000000000'),
                                                       to_address=Address(event_data['args']['guy']),
                                                       value=Wad(event_data['args']['wad'])))

                    # $ seth keccak $(seth --from-ascii "Burn(address,uint256)")
                    # 0xcc16f5dbb4873280815c1ee09dbd06736cffcc184412cf7a71a0fdb75d397ca5
                    if receipt_log['topics'][0] == HexBytes('0xcc16f5dbb4873280815c1ee09dbd06736cffcc184412cf7a71a0fdb75d397ca5'):
                        from pymaker.token import DSToken
                        transfer_abi = [abi for abi in DSToken.abi if abi.get('name') == 'Burn'][0]
                        codec = ABICodec(default_registry)
                        event_data = get_event_data(codec, transfer_abi, receipt_log)
                        self.transfers.append(Transfer(token_address=Address(event_data['address']),
                                                       from_address=Address(event_data['args']['guy']),
                                                       to_address=Address('0x0000000000000000000000000000000000000000'),
                                                       value=Wad(event_data['args']['wad'])))

        else:
            self.successful = False

    @property
    def logs(self):
        return self.raw_receipt['logs']