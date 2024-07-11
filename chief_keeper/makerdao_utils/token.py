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

from web3 import Web3

import chief_keeper.utils.address as address_utils
import chief_keeper.utils.contract as contract_utils
import chief_keeper.utils.transact as transact_utils
import chief_keeper.utils.big_number as big_number_utils

# Lazy import of transact_utils to avoid circular import issues
transact_utils = None

class ERC20Token(contract_utils.Contract):
    """A client for a standard ERC20 token contract.

    Attributes:
        web3: An instance of `Web` from `web3.py`.
        address: Ethereum address of the ERC20 token.
    """

    abi = contract_utils.Contract._load_abi(__name__, 'abi/ERC20Token.abi')
    registry = {}

    def __init__(self, web3: Web3, address: address_utils.Address):
        assert(isinstance(web3, Web3))
        assert(isinstance(address, address_utils.Address))

        self.web3 = web3
        self.address = address
        self._contract = self._get_contract(web3, self.abi, address)

        # # Lazy import for transact_utils
        # global transact_utils
        # if 'transact_utils' not in globals():
        #     import chief_keeper.utils.transact as transact_utils
        #     globals()['transact_utils'] = transact_utils


    def name(self) -> str:
        abi_with_string = json.loads("""[{"constant":true,"inputs":[],"name":"name","outputs":[{"name":"","type":"string"}],"payable":false,"stateMutability":"view","type":"function"}]""")
        abi_with_bytes32 = json.loads("""[{"constant":true,"inputs":[],"name":"name","outputs":[{"name":"","type":"bytes32"}],"payable":false,"stateMutability":"view","type":"function"}]""")

        contract_with_string = self._get_contract(self.web3, abi_with_string, self.address)
        contract_with_bytes32 = self._get_contract(self.web3, abi_with_bytes32, self.address)

        try:
            return contract_with_string.functions.name().call()
        except:
            return str(contract_with_bytes32.functions.name().call(), "utf-8").strip('\x00')

    def symbol(self) -> str:
        abi_with_string = json.loads("""[{"constant":true,"inputs":[],"name":"symbol","outputs":[{"name":"","type":"string"}],"payable":false,"stateMutability":"view","type":"function"}]""")
        abi_with_bytes32 = json.loads("""[{"constant":true,"inputs":[],"name":"symbol","outputs":[{"name":"","type":"bytes32"}],"payable":false,"stateMutability":"view","type":"function"}]""")

        contract_with_string = self._get_contract(self.web3, abi_with_string, self.address)
        contract_with_bytes32 = self._get_contract(self.web3, abi_with_bytes32, self.address)

        try:
            return contract_with_string.functions.symbol().call()
        except:
            return str(contract_with_bytes32.functions.symbol().call(), "utf-8").strip('\x00')

    def total_supply(self) -> big_number_utils.Wad:
        """Returns the total supply of the token.

        Returns:
            The total supply of the token.
        """
        return big_number_utils.Wad(self._contract.functions.totalSupply().call())

    def balance_of(self, address: address_utils.Address) -> big_number_utils.Wad:
        """Returns the token balance of a given address.

        Args:
            address: The address to check the balance of.

        Returns:
            The token balance of the address specified.
        """
        assert(isinstance(address, address_utils.Address))

        return big_number_utils.Wad(self._contract.functions.balanceOf(address.address).call())

    def balance_at_block(self, address: address_utils.Address, block_identifier: int = 'latest') -> big_number_utils.Wad:
        """Returns the token balance of a given address.

        Args:
            address: The address to check the balance of.
            block_identifier: block at which to retrieve the balance

        Returns:
            The token balance of the address specified.
        """
        assert(isinstance(address, address_utils.Address))
        assert(isinstance(block_identifier, int) or block_identifier == 'latest')

        return big_number_utils.Wad(self._contract.functions.balanceOf(address.address).call(block_identifier=block_identifier))

    def allowance_of(self, address: address_utils.Address, payee: address_utils.Address) -> big_number_utils.Wad:
        """Returns the current allowance of a specified `payee` (delegate account).

        Allowance is an ERC20 concept allowing the `payee` (delegate account) to spend a fixed amount of tokens
        on behalf of the token owner (`address`).

        Args:
            address: The address to check the allowance for (it's the address the tokens can be spent from).
            payee: The address of the delegate account (it's the address that can spend the tokens).

        Returns:
            The allowance of the `payee` specified in regards to the `address`.
        """
        assert(isinstance(address, address_utils.Address))
        assert(isinstance(payee, address_utils.Address))

        return big_number_utils.Wad(self._contract.functions.allowance(address.address, payee.address).call())

    def transfer(self, address: address_utils.Address, value: big_number_utils.Wad) -> 'transact_utils.Transact':
        """Transfers tokens to a specified address.

        Args:
            address: Destination address to transfer the tokens to.
            value: The value of tokens to transfer.

        Returns:
            A :py:class:`transact_utils.Transact` instance, which can be used to trigger the transaction.
        """
        assert(isinstance(address, address_utils.Address))
        assert(isinstance(value, big_number_utils.Wad))

        return transact_utils.Transact(self, self.web3, self.abi, self.address, self._contract, 'transfer', [address.address, value.value])

    def transfer_from(self, source_address: address_utils.Address, destination_address: address_utils.Address, value: big_number_utils.Wad) -> 'transact_utils.Transact':
        """Transfers tokens to a specified address.

        Args:
            source_address: Source address to transfer the tokens from.
            destination_address: Destination address to transfer the tokens to.
            value: The value of tokens to transfer.

        Returns:
            A :py:class:`transact_utils.Transact` instance, which can be used to trigger the transaction.
        """
        assert(isinstance(source_address, address_utils.Address))
        assert(isinstance(destination_address, address_utils.Address))
        assert(isinstance(value, big_number_utils.Wad))

        return transact_utils.Transact(self, self.web3, self.abi, self.address, self._contract, 'transferFrom', [source_address.address,
                                                                                                  destination_address.address,
                                                                                                  value.value])

    def approve(self, payee: address_utils.Address, limit: big_number_utils.Wad = big_number_utils.Wad(2**256 - 1)) -> 'transact_utils.Transact':
        """Modifies the current allowance of a specified `payee` (delegate account).

        Allowance is an ERC20 concept allowing the `payee` (delegate account) to spend a fixed amount of tokens
        (`limit`) on behalf of the token owner.

        If `limit` is omitted, a maximum possible value is granted.

        Args:
            payee: The address of the delegate account (it's the address that can spend the tokens).
            limit: The value of the allowance i.e. the value of tokens that the `payee` (delegate account)
                can spend on behalf of their owner.

        Returns:
            A :py:class:`transact_utils.Transact` instance, which can be used to trigger the transaction.
        """
        assert(isinstance(payee, address_utils.Address))
        assert(isinstance(limit, big_number_utils.Wad))

        return transact_utils.Transact(self, self.web3, self.abi, self.address, self._contract,
                        'approve(address,uint256)', [payee.address, limit.value])

    def __eq__(self, other):
        return self.address == other.address

    def __repr__(self):
        return f"ERC20Token('{self.address}')"


class DSToken(ERC20Token):
    """A client for the `DSToken` contract.

    You can find the source code of the `DSToken` contract here:
    <https://github.com/dapphub/ds-token>.

    Attributes:
        web3: An instance of `Web` from `web3.py`.
        address: Ethereum address of the `DSToken` contract.
    """

    abi = contract_utils.Contract._load_abi(__name__, 'abi/DSToken.abi')
    bin = contract_utils.Contract._load_bin(__name__, 'abi/DSToken.bin')

    @staticmethod
    def deploy(web3: Web3, symbol: str):
        """Deploy a new instance of the `DSToken` contract.

        Args:
            web3: An instance of `Web` from `web3.py`.
            symbol: Symbol of the new token.

        Returns:
            A `DSToken` class instance.
        """
        assert(isinstance(symbol, str))
        return DSToken(web3=web3, address=contract_utils.Contract._deploy(web3, DSToken.abi, DSToken.bin, [bytes(symbol, "utf-8")]))

    def authority(self) -> address_utils.Address:
        """Return the current `authority` of a `DSAuth`-ed contract.

        Returns:
            The address of the current `authority`.
        """
        return address_utils.Address(self._contract.functions.authority().call())

    def set_authority(self, address: address_utils.Address) -> 'transact_utils.Transact':
        """Set the `authority` of a `DSAuth`-ed contract.

        Args:
            address: The address of the new `authority`.

        Returns:
            A :py:class:`transact_utils.Transact` instance, which can be used to trigger the transaction.
        """
        assert(isinstance(address, address_utils.Address))
        return transact_utils.Transact(self, self.web3, self.abi, self.address, self._contract, 'setAuthority', [address.address])

    def mint(self, amount: big_number_utils.Wad) -> 'transact_utils.Transact':
        """Increase the total supply of the token.

        Args:
            amount: The amount to increase the total supply by.

        Returns:
            A :py:class:`transact_utils.Transact` instance, which can be used to trigger the transaction.
        """
        assert(isinstance(amount, big_number_utils.Wad))
        return transact_utils.Transact(self, self.web3, self.abi, self.address, self._contract, 'mint(uint256)', [amount.value])

    def mint_to(self, address: address_utils.Address, amount: big_number_utils.Wad) -> 'transact_utils.Transact':
        """Increase the total supply of the token.

        Args:
            address: The address to credit the new tokens to.
            amount: The amount to increase the total supply by.

        Returns:
            A :py:class:`transact_utils.Transact` instance, which can be used to trigger the transaction.
        """
        assert(isinstance(amount, big_number_utils.Wad))
        assert(isinstance(address, address_utils.Address))
        return transact_utils.Transact(self, self.web3, self.abi, self.address, self._contract, 'mint(address,uint256)', [address.address,
                                                                                                           amount.value])

    def burn(self, amount: big_number_utils.Wad) -> 'transact_utils.Transact':
        """Decrease the total supply of the token.

        Args:
            amount: The amount to decrease the total supply by.

        Returns:
            A :py:class:`transact_utils.Transact` instance, which can be used to trigger the transaction.
        """
        assert(isinstance(amount, big_number_utils.Wad))
        return transact_utils.Transact(self, self.web3, self.abi, self.address, self._contract, 'burn(uint256)', [amount.value])

    def burn_from(self, address: address_utils.Address, amount: big_number_utils.Wad) -> 'transact_utils.Transact':
        """Decrease the total supply of the token.

        Args:
            address: The address to burn the tokens from.
            amount: The amount to decrease the total supply by.

        Returns:
            A :py:class:`transact_utils.Transact` instance, which can be used to trigger the transaction.
        """
        assert(isinstance(amount, big_number_utils.Wad))
        return transact_utils.Transact(self, self.web3, self.abi, self.address, self._contract, 'burn(address,uint256)', [address.address,
                                                                                                           amount.value])

    def __repr__(self):
        return f"DSToken('{self.address}')"


class DSEthToken(ERC20Token):
    """A client for the `DSEthToken` contract.

    `DSEthToken`, also known as ETH Wrapper or W-ETH, is a contract into which you can deposit
    raw ETH and then deal with it like with any other ERC20 token. In addition to the `deposit()`
    and `withdraw()` methods, it implements the standard ERC20 token API.

    You can find the source code of the `DSEthToken` contract here:
    <https://github.com/dapphub/ds-eth-token>.

    Attributes:
        web3: An instance of `Web` from `web3.py`.
        address: Ethereum address of the `DSEthToken` contract.
    """

    abi = contract_utils.Contract._load_abi(__name__, 'abi/DSEthToken.abi')
    bin = contract_utils.Contract._load_bin(__name__, 'abi/DSEthToken.bin')

    @staticmethod
    def deploy(web3: Web3):
        """Deploy a new instance of the `DSEthToken` contract.

        Args:
            web3: An instance of `Web` from `web3.py`.

        Returns:
            A `DSEthToken` class instance.
        """
        return DSEthToken(web3=web3, address=contract_utils.Contract._deploy(web3, DSEthToken.abi, DSEthToken.bin, []))

    def __init__(self, web3, address):
        super().__init__(web3, address)
        self._contract = self._get_contract(web3, self.abi, address)

    def deposit(self, amount: big_number_utils.Wad) -> 'transact_utils.Transact':
        """Deposits `amount` of raw ETH to `DSEthToken`.

        Args:
            amount: Amount of raw ETH to be deposited to `DSEthToken`.

        Returns:
            A :py:class:`transact_utils.Transact` instance, which can be used to trigger the transaction.
        """
        assert(isinstance(amount, big_number_utils.Wad))
        return transact_utils.Transact(self, self.web3, self.abi, self.address, self._contract, 'deposit', [], {'value': amount.value})

    def withdraw(self, amount: big_number_utils.Wad) -> 'transact_utils.Transact':
        """Withdraws `amount` of raw ETH from `DSEthToken`.

        The withdrawn ETH will get transferred to the calling account.

        Args:
            amount: Amount of raw ETH to be withdrawn from `DSEthToken`.

        Returns:
            A :py:class:`transact_utils.Transact` instance, which can be used to trigger the transaction.
        """
        assert(isinstance(amount, big_number_utils.Wad))
        return transact_utils.Transact(self, self.web3, self.abi, self.address, self._contract, 'withdraw', [amount.value])

    def __repr__(self):
        return f"DSEthToken('{self.address}')"


class EthToken():
    """Basic ETH token.

        Attributes:
         web3: An instance of `Web` from `web3.py`.
         address: Ethereum address of the original ETH token.
    """

    def __init__(self, web3: Web3, address: address_utils.Address):
        assert(isinstance(web3, Web3))
        assert(isinstance(address, address_utils.Address))

        self.web3 = web3
        self.address = address

    def balance_of(self, address):
        """Returns the ETH balance of a given Ethereum address.

         Args:
             address: The address to check the balance of.

         Returns:
             The ETH balance of the address specified.
         """
        assert(isinstance(address, address_utils.Address))

        return big_number_utils.Wad(self.web3.eth.getBalance(address.address))
