# This file is part of Maker Keeper Framework.
#
# Copyright (C) 2018-2019 reverendus, bargst, EdNoepel
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
import logging
from pprint import pformat
from typing import List
from web3 import Web3

from web3._utils.events import get_event_data

from eth_abi.codec import ABICodec
from eth_abi.registry import registry as default_registry

from chief_keeper.utils.address import Address
from chief_keeper.utils.contract import Contract
from chief_keeper.utils.transact import Transact
from chief_keeper.utils.big_number import Wad, Rad, Ray

from chief_keeper.makerdao_utils.dss import Dog, Vat
from chief_keeper.makerdao_utils.token import ERC20Token

from pymaker.logging import LogNote



def toBytes(string: str):
    assert(isinstance(string, str))
    return string.encode('utf-8').ljust(32, bytes(1))


logger = logging.getLogger()


class AuctionContract(Contract):
    """Abstract baseclass shared across all auction contracts."""
    def __init__(self, web3: Web3, address: Address, abi: list):
        if self.__class__ == AuctionContract:
            raise NotImplemented('Abstract class; please call Clipper, Flapper, Flipper, or Flopper ctor')
        assert isinstance(web3, Web3)
        assert isinstance(address, Address)
        assert isinstance(abi, list)

        self.web3 = web3
        self.address = address
        self.abi = abi
        self._contract = self._get_contract(web3, abi, address)

        self.log_note_abi = None
        self.kick_abi = None
        for member in abi:
            if not self.log_note_abi and member.get('name') == 'LogNote':
                self.log_note_abi = member
            elif not self.kick_abi and member.get('name') == 'Kick':
                self.kick_abi = member

    def approve(self, source: Address, approval_function):
        """Approve the auction to access our collateral, Dai, or MKR so we can participate in auctions.

        For available approval functions (i.e. approval modes) see `directly` and `hope_directly`
        in `pymaker.approval`.

        Args:
            source: Address of the contract or token relevant to the auction (for Flipper and Flopper pass Vat address,
            for Flapper pass MKR token address)
            approval_function: Approval function (i.e. approval mode)
        """
        assert isinstance(source, Address)
        assert(callable(approval_function))

        approval_function(token=ERC20Token(web3=self.web3, address=source),
                          spender_address=self.address, spender_name=self.__class__.__name__)

    def wards(self, address: Address) -> bool:
        assert isinstance(address, Address)

        return bool(self._contract.functions.wards(address.address).call())

    def vat(self) -> Address:
        """Returns the `vat` address.
         Returns:
            The address of the `vat` contract.
        """
        return Address(self._contract.functions.vat().call())

    def get_past_lognotes(self, abi: list, from_block: int, to_block: int = None, chunk_size=20000) -> List[LogNote]:
        current_block = self._contract.web3.eth.blockNumber
        assert isinstance(from_block, int)
        assert from_block < current_block
        if to_block is None:
            to_block = current_block
        else:
            assert isinstance(to_block, int)
            assert to_block >= from_block
            assert to_block <= current_block
        assert chunk_size > 0
        assert isinstance(abi, list)

        logger.debug(f"Consumer requested auction data from block {from_block} to {to_block}")
        start = from_block
        end = None
        chunks_queried = 0
        events = []
        while end is None or start <= to_block:
            chunks_queried += 1
            end = min(to_block, start + chunk_size)

            filter_params = {
                'address': self.address.address,
                'fromBlock': start,
                'toBlock': end
            }
            logger.debug(f"Querying logs from block {start} to {end} ({end-start} blocks); "
                         f"accumulated {len(events)} events in {chunks_queried-1} requests")

            logs = self.web3.eth.getLogs(filter_params)
            events.extend(list(map(lambda l: self.parse_event(l), logs)))
            start += chunk_size

        return list(filter(lambda l: l is not None, events))

    def parse_event(self, event):
        raise NotImplemented()


class DealableAuctionContract(AuctionContract):
    """Abstract baseclass shared across original auction contracts."""

    class DealLog:
        def __init__(self, lognote: LogNote):
            # This is whoever called `deal`, which could differ from the `guy` who won the auction
            self.usr = Address(lognote.usr)
            self.id = Web3.toInt(lognote.arg1)
            self.block = lognote.block
            self.tx_hash = lognote.tx_hash

        def __repr__(self):
            return f"AuctionContract.DealLog({pformat(vars(self))})"

    def __init__(self, web3: Web3, address: Address, abi: list, bids: callable):
        if self.__class__ == DealableAuctionContract:
            raise NotImplemented('Abstract class; please call Flipper, Flapper, or Flopper ctor')
        super(DealableAuctionContract, self).__init__(web3, address, abi)

        self._bids = bids

    def active_auctions(self) -> list:
        active_auctions = []
        auction_count = self.kicks()+1
        for index in range(1, auction_count):
            bid = self._bids(index)
            if bid.guy != Address("0x0000000000000000000000000000000000000000"):
                now = datetime.now().timestamp()
                if (bid.tic == 0 or now < bid.tic) and now < bid.end:
                    active_auctions.append(bid)
            index += 1
        return active_auctions

    def beg(self) -> Wad:
        """Returns the percentage minimum bid increase.

        Returns:
            The percentage minimum bid increase.
        """
        return Wad(self._contract.functions.beg().call())

    def ttl(self) -> int:
        """Returns the bid lifetime.

        Returns:
            The bid lifetime (in seconds).
        """
        return int(self._contract.functions.ttl().call())

    def tau(self) -> int:
        """Returns the total auction length.

        Returns:
            The total auction length (in seconds).
        """
        return int(self._contract.functions.tau().call())

    def kicks(self) -> int:
        """Returns the number of auctions started so far.

        Returns:
            The number of auctions started so far.
        """
        return int(self._contract.functions.kicks().call())

    def deal(self, id: int) -> Transact:
        assert(isinstance(id, int))

        return Transact(self, self.web3, self.abi, self.address, self._contract, 'deal', [id])

    def tick(self, id: int) -> Transact:
        """Resurrect an auction which expired without any bids."""
        assert(isinstance(id, int))

        return Transact(self, self.web3, self.abi, self.address, self._contract, 'tick', [id])


class Flipper(DealableAuctionContract):
    """A client for the `Flipper` contract, used to interact with collateral auctions.

    You can find the source code of the `Flipper` contract here:
    <https://github.com/makerdao/dss/blob/master/src/flip.sol>.

    Attributes:
        web3: An instance of `Web` from `web3.py`.
        address: Ethereum address of the `Flipper` contract.

    Event signatures:
        0x65fae35e: (deployment-related)
        0x9c52a7f1: (deployment-related)
        0x29ae8114: file
        0xc84ce3a1172f0dec3173f04caaa6005151a4bfe40d4c9f3ea28dba5f719b2a7a: kick
        0x4b43ed12: tend
        0x5ff3a382: dent
        0xc959c42b: deal
    """

    abi = Contract._load_abi(__name__, 'abi/Flipper.abi')
    bin = Contract._load_bin(__name__, 'abi/Flipper.bin')

    class Bid:
        def __init__(self, id: int, bid: Rad, lot: Wad, guy: Address, tic: int, end: int,
                     usr: Address, gal: Address, tab: Rad):
            assert(isinstance(id, int))
            assert(isinstance(bid, Rad))
            assert(isinstance(lot, Wad))
            assert(isinstance(guy, Address))
            assert(isinstance(tic, int))
            assert(isinstance(end, int))
            assert(isinstance(usr, Address))
            assert(isinstance(gal, Address))
            assert(isinstance(tab, Rad))

            self.id = id
            self.bid = bid
            self.lot = lot
            self.guy = guy
            self.tic = tic
            self.end = end
            self.usr = usr
            self.gal = gal
            self.tab = tab

        def __repr__(self):
            return f"Flipper.Bid({pformat(vars(self))})"

    class KickLog:
        def __init__(self, log):
            args = log['args']
            self.id = args['id']
            self.lot = Wad(args['lot'])
            self.bid = Rad(args['bid'])
            self.tab = Rad(args['tab'])
            self.usr = Address(args['usr'])
            self.gal = Address(args['gal'])
            self.block = log['blockNumber']
            self.tx_hash = log['transactionHash'].hex()

        def __repr__(self):
            return f"Flipper.KickLog({pformat(vars(self))})"

    class TendLog:
        def __init__(self, lognote: LogNote):
            self.guy = Address(lognote.usr)
            self.id = Web3.toInt(lognote.arg1)
            self.lot = Wad(Web3.toInt(lognote.arg2))
            self.bid = Rad(Web3.toInt(lognote.get_bytes_at_index(2)))
            self.block = lognote.block
            self.tx_hash = lognote.tx_hash

        def __repr__(self):
            return f"Flipper.TendLog({pformat(vars(self))})"

    class DentLog:
        def __init__(self, lognote: LogNote):
            self.guy = Address(lognote.usr)
            self.id = Web3.toInt(lognote.arg1)
            self.lot = Wad(Web3.toInt(lognote.arg2))
            self.bid = Rad(Web3.toInt(lognote.get_bytes_at_index(2)))
            self.block = lognote.block
            self.tx_hash = lognote.tx_hash

        def __repr__(self):
            return f"Flipper.DentLog({pformat(vars(self))})"

    def __init__(self, web3: Web3, address: Address):
        super(Flipper, self).__init__(web3, address, Flipper.abi, self.bids)

    def bids(self, id: int) -> Bid:
        """Returns the auction details.

        Args:
            id: Auction identifier.

        Returns:
            The auction details.
        """
        assert(isinstance(id, int))

        array = self._contract.functions.bids(id).call()

        return Flipper.Bid(id=id,
                           bid=Rad(array[0]),
                           lot=Wad(array[1]),
                           guy=Address(array[2]),
                           tic=int(array[3]),
                           end=int(array[4]),
                           usr=Address(array[5]),
                           gal=Address(array[6]),
                           tab=Rad(array[7]))

    def tend(self, id: int, lot: Wad, bid: Rad) -> Transact:
        assert(isinstance(id, int))
        assert(isinstance(lot, Wad))
        assert(isinstance(bid, Rad))

        return Transact(self, self.web3, self.abi, self.address, self._contract, 'tend', [id, lot.value, bid.value])

    def dent(self, id: int, lot: Wad, bid: Rad) -> Transact:
        assert(isinstance(id, int))
        assert(isinstance(lot, Wad))
        assert(isinstance(bid, Rad))

        return Transact(self, self.web3, self.abi, self.address, self._contract, 'dent', [id, lot.value, bid.value])

    def past_logs(self, from_block: int, to_block: int = None, chunk_size=20000):
        logs = super().get_past_lognotes(Flipper.abi, from_block, to_block, chunk_size)

        history = []
        for log in logs:
            if log is None:
                continue
            elif isinstance(log, Flipper.KickLog):
                history.append(log)
            elif log.sig == '0x4b43ed12':
                history.append(Flipper.TendLog(log))
            elif log.sig == '0x5ff3a382':
                history.append(Flipper.DentLog(log))
            elif log.sig == '0xc959c42b':
                history.append(DealableAuctionContract.DealLog(log))
        return history

    def parse_event(self, event):
        signature = Web3.toHex(event['topics'][0])
        codec = ABICodec(default_registry)
        if signature == "0xc84ce3a1172f0dec3173f04caaa6005151a4bfe40d4c9f3ea28dba5f719b2a7a":
            event_data = get_event_data(codec, self.kick_abi, event)
            return Flipper.KickLog(event_data)
        else:
            event_data = get_event_data(codec, self.log_note_abi, event)
            return LogNote(event_data)

    def __repr__(self):
        return f"Flipper('{self.address}')"


class Flapper(DealableAuctionContract):
    """A client for the `Flapper` contract, used to interact with surplus auctions.

    You can find the source code of the `Flapper` contract here:
    <https://github.com/makerdao/dss/blob/master/src/flap.sol>.

    Attributes:
        web3: An instance of `Web` from `web3.py`.
        address: Ethereum address of the `Flapper` contract.

    Event signatures:
        0x65fae35e: (deployment-related)
        0x9c52a7f1: (deployment-related)
        0xe6dde59cbc017becba89714a037778d234a84ce7f0a137487142a007e580d609: kick
        0x29ae8114: file
        0x4b43ed12: tend
        0xc959c42b: deal
    """

    abi = Contract._load_abi(__name__, 'abi/Flapper.abi')
    bin = Contract._load_bin(__name__, 'abi/Flapper.bin')

    class Bid:
        def __init__(self, id: int, bid: Wad, lot: Rad, guy: Address, tic: int, end: int):
            assert(isinstance(id, int))
            assert(isinstance(bid, Wad))        # MKR
            assert(isinstance(lot, Rad))        # DAI
            assert(isinstance(guy, Address))
            assert(isinstance(tic, int))
            assert(isinstance(end, int))

            self.id = id
            self.bid = bid
            self.lot = lot
            self.guy = guy
            self.tic = tic
            self.end = end

        def __repr__(self):
            return f"Flapper.Bid({pformat(vars(self))})"

    class KickLog:
        def __init__(self, log):
            args = log['args']
            self.id = args['id']
            self.lot = Rad(args['lot'])
            self.bid = Wad(args['bid'])
            self.block = log['blockNumber']
            self.tx_hash = log['transactionHash'].hex()

        def __repr__(self):
            return f"Flapper.KickLog({pformat(vars(self))})"

    class TendLog:
        def __init__(self, lognote: LogNote):
            self.guy = Address(lognote.usr)
            self.id = Web3.toInt(lognote.arg1)
            self.lot = Rad(Web3.toInt(lognote.arg2))
            self.bid = Wad(Web3.toInt(lognote.get_bytes_at_index(2)))
            self.block = lognote.block
            self.tx_hash = lognote.tx_hash

        def __repr__(self):
            return f"Flapper.TendLog({pformat(vars(self))})"

    def __init__(self, web3: Web3, address: Address):
        super(Flapper, self).__init__(web3, address, Flapper.abi, self.bids)

    def live(self) -> bool:
        return self._contract.functions.live().call() > 0

    def bids(self, id: int) -> Bid:
        """Returns the auction details.

        Args:
            id: Auction identifier.

        Returns:
            The auction details.
        """
        assert(isinstance(id, int))

        array = self._contract.functions.bids(id).call()

        return Flapper.Bid(id=id,
                           bid=Wad(array[0]),
                           lot=Rad(array[1]),
                           guy=Address(array[2]),
                           tic=int(array[3]),
                           end=int(array[4]))

    def tend(self, id: int, lot: Rad, bid: Wad) -> Transact:
        assert(isinstance(id, int))
        assert(isinstance(lot, Rad))
        assert(isinstance(bid, Wad))

        return Transact(self, self.web3, self.abi, self.address, self._contract, 'tend', [id, lot.value, bid.value])

    def yank(self, id: int) -> Transact:
        """While `cage`d, refund current bid to the bidder"""
        assert (isinstance(id, int))

        return Transact(self, self.web3, self.abi, self.address, self._contract, 'yank', [id])

    def past_logs(self, from_block: int, to_block: int = None, chunk_size=20000):
        logs = super().get_past_lognotes(Flapper.abi, from_block, to_block, chunk_size)

        history = []
        for log in logs:
            if log is None:
                continue
            elif isinstance(log, Flapper.KickLog):
                history.append(log)
            elif log.sig == '0x4b43ed12':
                history.append(Flapper.TendLog(log))
            elif log.sig == '0xc959c42b':
                history.append(DealableAuctionContract.DealLog(log))
        return history

    def parse_event(self, event):
        signature = Web3.toHex(event['topics'][0])
        codec = ABICodec(default_registry)
        if signature == "0xe6dde59cbc017becba89714a037778d234a84ce7f0a137487142a007e580d609":
            event_data = get_event_data(codec, self.kick_abi, event)
            return Flapper.KickLog(event_data)
        else:
            event_data = get_event_data(codec, self.log_note_abi, event)
            return LogNote(event_data)

    def __repr__(self):
        return f"Flapper('{self.address}')"


class Flopper(DealableAuctionContract):
    """A client for the `Flopper` contract, used to interact with debt auctions.

    You can find the source code of the `Flopper` contract here:
    <https://github.com/makerdao/dss/blob/master/src/flop.sol>.

    Attributes:
        web3: An instance of `Web` from `web3.py`.
        address: Ethereum address of the `Flopper` contract.

    Event signatures:
        0x65fae35e: (deployment-related)
        0x9c52a7f1: (deployment-related)
        0x29ae8114: file
        0x7e8881001566f9f89aedb9c5dc3d856a2b81e5235a8196413ed484be91cc0df6: kick
        0x5ff3a382: dent
        0xc959c42b: deal
    """

    abi = Contract._load_abi(__name__, 'abi/Flopper.abi')
    bin = Contract._load_bin(__name__, 'abi/Flopper.bin')

    class Bid:
        def __init__(self, id: int, bid: Rad, lot: Wad, guy: Address, tic: int, end: int):
            assert(isinstance(id, int))
            assert(isinstance(bid, Rad))
            assert(isinstance(lot, Wad))
            assert(isinstance(guy, Address))
            assert(isinstance(tic, int))
            assert(isinstance(end, int))

            self.id = id
            self.bid = bid
            self.lot = lot
            self.guy = guy
            self.tic = tic
            self.end = end

        def __repr__(self):
            return f"Flopper.Bid({pformat(vars(self))})"

    class KickLog:
        def __init__(self, log):
            args = log['args']
            self.id = args['id']
            self.lot = Wad(args['lot'])
            self.bid = Rad(args['bid'])
            self.gal = Address(args['gal'])
            self.block = log['blockNumber']
            self.tx_hash = log['transactionHash'].hex()

        def __repr__(self):
            return f"Flopper.KickLog({pformat(vars(self))})"

    class DentLog:
        def __init__(self, lognote: LogNote):
            self.guy = Address(lognote.usr)
            self.id = Web3.toInt(lognote.arg1)
            self.lot = Wad(Web3.toInt(lognote.arg2))
            self.bid = Rad(Web3.toInt(lognote.get_bytes_at_index(2)))
            self.block = lognote.block
            self.tx_hash = lognote.tx_hash

        def __repr__(self):
            return f"Flopper.DentLog({pformat(vars(self))})"

    def __init__(self, web3: Web3, address: Address):
        assert isinstance(web3, Web3)
        assert isinstance(address, Address)

        super(Flopper, self).__init__(web3, address, Flopper.abi, self.bids)

    def live(self) -> bool:
        return self._contract.functions.live().call() > 0

    def pad(self) -> Wad:
        """Returns the lot increase applied after an auction has been `tick`ed."""

        return Wad(self._contract.functions.pad().call())

    def bids(self, id: int) -> Bid:
        """Returns the auction details.

        Args:
            id: Auction identifier.

        Returns:
            The auction details.
        """
        assert(isinstance(id, int))

        array = self._contract.functions.bids(id).call()

        return Flopper.Bid(id=id,
                           bid=Rad(array[0]),
                           lot=Wad(array[1]),
                           guy=Address(array[2]),
                           tic=int(array[3]),
                           end=int(array[4]))

    def dent(self, id: int, lot: Wad, bid: Rad) -> Transact:
        assert(isinstance(id, int))
        assert(isinstance(lot, Wad))
        assert(isinstance(bid, Rad))

        return Transact(self, self.web3, self.abi, self.address, self._contract, 'dent', [id, lot.value, bid.value])

    def yank(self, id: int) -> Transact:
        """While `cage`d, refund current bid to the bidder"""
        assert (isinstance(id, int))

        return Transact(self, self.web3, self.abi, self.address, self._contract, 'yank', [id])

    def past_logs(self, from_block: int, to_block: int = None, chunk_size=20000):
        logs = super().get_past_lognotes(Flopper.abi, from_block, to_block, chunk_size)

        history = []
        for log in logs:
            if log is None:
                continue
            elif isinstance(log, Flopper.KickLog):
                history.append(log)
            elif log.sig == '0x5ff3a382':
                history.append(Flopper.DentLog(log))
            elif log.sig == '0xc959c42b':
                history.append(DealableAuctionContract.DealLog(log))
        return history

    def parse_event(self, event):
        signature = Web3.toHex(event['topics'][0])
        codec = ABICodec(default_registry)
        if signature == "0x7e8881001566f9f89aedb9c5dc3d856a2b81e5235a8196413ed484be91cc0df6":
            event_data = get_event_data(codec, self.kick_abi, event)
            return Flopper.KickLog(event_data)
        else:
            event_data = get_event_data(codec, self.log_note_abi, event)
            return LogNote(event_data)

    def __repr__(self):
        return f"Flopper('{self.address}')"


class Clipper(AuctionContract):
    """A client for the `Clipper` contract, used to interact with collateral auctions.

    You can find the source code of the `Clipper` contract here:
    <https://github.com/makerdao/dss/blob/master/src/clip.sol>.

    Attributes:
        web3: An instance of `Web` from `web3.py`.
        address: Ethereum address of the `Clipper` contract.
    """

    abi = Contract._load_abi(__name__, 'abi/Clipper.abi')
    bin = Contract._load_bin(__name__, 'abi/Clipper.bin')

    class KickLog:
        def __init__(self, log):
            args = log['args']
            self.id = args['id']
            self.top = Ray(args['top'])         # starting price
            self.tab = Rad(args['tab'])         # debt
            self.lot = Wad(args['lot'])         # collateral
            self.usr = Address(args['usr'])     # liquidated vault
            self.kpr = Address(args['kpr'])     # keeper who barked
            self.coin = Rad(args['coin'])       # total kick incentive (tip + tab*chip)
            self.block = log['blockNumber']
            self.tx_hash = log['transactionHash'].hex()

        def __repr__(self):
            return f"Clipper.KickLog({pformat(vars(self))})"

    class TakeLog:
        def __init__(self, log, sender):
            args = log['args']
            self.id = args['id']
            self.max = Ray(args['max'])         # Max bid price specified
            self.price = Ray(args['price'])     # Calculated bid price
            self.owe = Rad(args['owe'])         # Dai needed to satisfy the calculated bid price
            self.tab = Rad(args['tab'])         # Remaining debt
            self.lot = Wad(args['lot'])         # Remaining lot
            self.usr = Address(args['usr'])     # Liquidated vault
            self.block = log['blockNumber']
            self.tx_hash = log['transactionHash'].hex()
            self.sender = sender

        def __repr__(self):
            return f"Clipper.TakeLog({pformat(vars(self))})"

    class RedoLog(KickLog):
        # Same fields as KickLog
        def __repr__(self):
            return f"Clipper.RedoLog({pformat(vars(self))})"

    class Sale:
        def __init__(self, id: int, pos: int, tab: Rad, lot: Wad, usr: Address, tic: int, top: Ray):
            assert(isinstance(id, int))
            assert(isinstance(pos, int))
            assert(isinstance(tab, Rad))
            assert(isinstance(lot, Wad))
            assert(isinstance(usr, Address))
            assert(isinstance(tic, int))
            assert(isinstance(top, Ray))

            self.id = id    # auction identifier
            self.pos = pos  # active index
            self.tab = tab  # dai to raise
            self.lot = lot  # collateral to sell
            self.usr = usr  # liquidated urn address
            self.tic = tic  # auction start time
            self.top = top  # starting price

        def __repr__(self):
            return f"Clipper.Sale({pformat(vars(self))})"

    def __init__(self, web3: Web3, address: Address):
        super(Clipper, self).__init__(web3, address, Clipper.abi)
        assert isinstance(web3, Web3)
        assert isinstance(address, Address)

        self.web3 = web3
        self.address = address
        self._contract = self._get_contract(web3, self.abi, address)
        # Albeit more elegant, this is inconsistent with AuctionContract.vat(), a method call
        self.calc = Address(self._contract.functions.calc().call())
        self.dog = Dog(web3, Address(self._contract.functions.dog().call()))
        self.vat = Vat(web3, Address(self._contract.functions.vat().call()))

        self.take_abi = None
        self.redo_abi = None
        for member in self.abi:
            if not self.take_abi and member.get('name') == 'Take':
                self.take_abi = member
            if not self.redo_abi and member.get('name') == 'Redo':
                self.redo_abi = member

    def active_auctions(self) -> list:
        active_auctions = []
        for index in range(1, self.kicks()+1):
            sale = self.sales(index)
            if sale.usr != Address.zero():
                active_auctions.append(sale)
            index += 1
        return active_auctions

    def ilk_name(self) -> str:
        ilk = self._contract.functions.ilk().call()
        return Web3.toText(ilk.strip(bytes(1)))

    def buf(self) -> Ray:
        """Multiplicative factor to increase starting price"""
        return Ray(self._contract.functions.buf().call())

    def tail(self) -> int:
        """Time elapsed before auction reset"""
        return int(self._contract.functions.tail().call())

    def cusp(self) -> Ray:
        """Percentage drop before auction reset"""
        return Ray(self._contract.functions.cusp().call())

    def chip(self) -> Wad:
        """Percentage of tab to suck from vow to incentivize keepers"""
        return Wad(self._contract.functions.chip().call())

    def tip(self) -> Rad:
        """Flat fee to suck from vow to incentivize keepers"""
        return Rad(self._contract.functions.tip().call())

    def chost(self) -> Rad:
        """Ilk dust times the ilk chop"""
        return Rad(self._contract.functions.chost().call())

    def kicks(self) -> int:
        """Number of auctions started so far."""
        return int(self._contract.functions.kicks().call())

    def active_count(self) -> int:
        """Number of active and redoable auctions."""
        return int(self._contract.functions.count().call())

    def status(self, id: int) -> (bool, Ray, Wad, Rad):
        """Indicates current state of the auction
        Args:
            id: Auction identifier.
        """
        assert isinstance(id, int)
        (needs_redo, price, lot, tab) = self._contract.functions.getStatus(id).call()
        logging.debug(f"Auction {id} {'needs redo ' if needs_redo else ''}with price={float(Ray(price))} " 
                      f"lot={float(Wad(lot))} tab={float(Rad(tab))}")
        return needs_redo, Ray(price), Wad(lot), Rad(tab)

    def sales(self, id: int) -> Sale:
        """Returns the auction details.
        Args:
            id: Auction identifier.
        Returns:
            The auction details.
        """
        assert(isinstance(id, int))

        array = self._contract.functions.sales(id).call()

        return Clipper.Sale(id=id,
                            pos=int(array[0]),
                            tab=Rad(array[1]),
                            lot=Wad(array[2]),
                            usr=Address(array[3]),
                            tic=int(array[4]),
                            top=Ray(array[5]))

    def validate_take(self, id: int, amt: Wad, max: Ray, our_address: Address = None):
        """Raise assertion if collateral cannot be purchased from an auction as desired"""
        assert isinstance(id, int)
        assert isinstance(amt, Wad)
        assert isinstance(max, Ray)

        if our_address:
            assert isinstance(our_address, Address)
        else:
            our_address = Address(self.web3.eth.defaultAccount)

        (done, price, lot, tab) = self.status(id)
        assert not done
        assert max >= price

        slice: Wad = min(lot, amt)          # Purchase as much as possible, up to amt
        owe: Rad = Rad(slice) * Rad(price)  # DAI needed to buy a slice of this sale
        chost = self.chost()

        if Rad(owe) > tab:
            owe = Rad(tab)
            slice = Wad(owe / Rad(price))
        elif owe < tab and slice < lot:
            if (tab - owe) < chost:
                assert tab > chost
                owe = tab - chost
                slice = Wad(owe / Rad(price))

        tab: Rad = tab - owe
        lot: Wad = lot - slice
        assert self.vat.dai(our_address) >= owe
        logger.debug(f"Validated clip.take which will leave tab={float(tab)} and lot={float(lot)}")

    def take(self, id: int, amt: Wad, max: Ray, who: Address = None, data=b'') -> Transact:
        """Buy amount of collateral from auction indexed by id.
        Args:
            id:     Auction id
            amt:    Upper limit on amount of collateral to buy
            max:    Maximum acceptable price (DAI / collateral)
            who:    Receiver of collateral and external call address
            data:   Data to pass in external call; if length 0, no call is done
        """
        assert isinstance(id, int)
        assert isinstance(amt, Wad)
        assert isinstance(max, Ray)

        if who:
            assert isinstance(who, Address)
        else:
            who = Address(self.web3.eth.defaultAccount)

        return Transact(self, self.web3, self.abi, self.address, self._contract, 'take',
                        [id, amt.value, max.value, who.address, data])

    def redo(self, id: int, kpr: Address = None) -> Transact:
        """Restart an auction which ended without liquidating all collateral.
            id:     Auction id
            kpr:    Keeper that called dog.bark()
        """
        assert isinstance(id, int)
        assert isinstance(kpr, Address) or kpr is None

        if kpr:
            assert isinstance(kpr, Address)
        else:
            kpr = Address(self.web3.eth.defaultAccount)

        return Transact(self, self.web3, self.abi, self.address, self._contract, 'redo', [id, kpr.address])

    def upchost(self):
        """Update the the cached dust*chop value following a governance change"""
        return Transact(self, self.web3, self.abi, self.address, self._contract, 'upchost', [])

    def past_logs(self, from_block: int, to_block: int = None, chunk_size=20000):
        logs = super().get_past_lognotes(Clipper.abi, from_block, to_block, chunk_size)

        history = []
        for log in logs:
            if log is None:
                continue
            elif isinstance(log, Clipper.KickLog) \
                    or isinstance(log, Clipper.TakeLog) \
                    or isinstance(log, Clipper.RedoLog):
                history.append(log)
            else:
                logger.debug(f"Found log with signature {log.sig}")
        return history

    def parse_event(self, event):
        signature = Web3.toHex(event['topics'][0])
        codec = ABICodec(default_registry)
        if signature == "0x7c5bfdc0a5e8192f6cd4972f382cec69116862fb62e6abff8003874c58e064b8":
            event_data = get_event_data(codec, self.kick_abi, event)
            return Clipper.KickLog(event_data)
        elif signature == "0x05e309fd6ce72f2ab888a20056bb4210df08daed86f21f95053deb19964d86b1":
            event_data = get_event_data(codec, self.take_abi, event)
            self._get_sender_for_eventlog(event_data)
            return Clipper.TakeLog(event_data, self._get_sender_for_eventlog(event_data))
        elif signature == "0x275de7ecdd375b5e8049319f8b350686131c219dd4dc450a08e9cf83b03c865f":
            event_data = get_event_data(codec, self.redo_abi, event)
            return Clipper.RedoLog(event_data)
        else:
            logger.debug(f"Found event signature {signature}")

    def _get_sender_for_eventlog(self, event_data) -> Address:
        tx_hash = event_data['transactionHash'].hex()
        receipt = self.web3.eth.getTransactionReceipt(tx_hash)
        return Address(receipt['from'])

    def __repr__(self):
        return f"Clipper('{self.address}')"
