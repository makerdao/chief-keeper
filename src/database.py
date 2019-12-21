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

from src.spell import DSSSpell

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


class SimpleDatabase:
    def __init__(self, web3: Web3, block: int, network: str, deployment: DssDeployment):
        self.web3 = web3
        self.deployment_block = block
        self.network = network
        self.dss = deployment


    def create(self):
        basepath = os.path.dirname(__file__)
        filepath = os.path.abspath(os.path.join(basepath, "db_"+self.network+".json"))

        if os.path.isfile(filepath) and os.access(filepath, os.R_OK):
        # checks if file exists
            result = "Simple database exists and is readable"
            self.db = TinyDB(filepath)
        else:
            result = "Either file is missing or is not readable, creating simple database"
            self.db = TinyDB(filepath)

            blockNumber = self.web3.eth.blockNumber
            self.db.insert({'last_block_checked_for_yays': blockNumber})

            yays = self.get_yays(self.deployment_block, blockNumber)
            self.db.insert({'yays': yays})

            etas = self.get_etas(yays, blockNumber)
            self.db.insert({'upcoming_etas': etas})

        return result


    def get_eta_inUnix(self, spell: DSSSpell) -> int:
        eta = spell.eta()
        etaInUnix = eta.replace(tzinfo=timezone.utc).timestamp()

        return etaInUnix

    def update_db_etas(self, blockNumber: int):
        """ Add yays with etas that have yet to be passed """
        yays = self.db.get(doc_id=2)["yays"]
        etas = self.get_etas(yays, blockNumber)

        self.db.update({'upcoming_etas': etas}, doc_ids=[3])



    def get_etas(self, yays, blockNumber: int):
        """ Get all etas that are scheduled in the future """
        etas = {}
        for yay in yays:

            #Check if yay is an address to an EOA or a contract
            if is_contract_at(self.web3, Address(yay)):
                spell = DSSSpell(self.web3, Address(yay))
                eta = self.get_eta_inUnix(spell)

                if eta >= self.web3.eth.getBlock(blockNumber).timestamp:
                    etas[spell.address.address] = eta

        return etas


    def update_db_yays(self, currentBlockNumber: int):

        DBblockNumber = self.db.get(doc_id=1)["last_block_checked_for_yays"]
        currentYays = self.get_yays(DBblockNumber,currentBlockNumber)
        oldYays = self.db.get(doc_id=2)["yays"]

        # Take out any duplicates
        newYays = list(dict.fromkeys(oldYays + currentYays))

        self.db.update({'yays': newYays}, doc_ids=[2])
        self.db.update({'last_block_checked_for_yays': currentBlockNumber}, doc_ids=[1])



    def get_yays(self, beginBlock: int, endBlock: int):

        etches = self.dss.ds_chief.past_etch_in_range(beginBlock, endBlock)
        maxYays = self.dss.ds_chief.get_max_yays()

        yays = []
        for etch in etches:
            yays = yays + self.unpack_slate(etch.slate, maxYays)

        return yays if not None else []

    # inspiration -> https://github.com/makerdao/dai-plugin-governance/blob/master/src/ChiefService.js#L153
    # When I have time
    # def unpack_slate(self, slate, i = 0):
    #     try:
    #         return [self.dss.ds_chief.get_yay(slate, i)].extend(
    #             self.unpack_slate(slate, i + 1))
    #     except:
    #         return []

    def unpack_slate(self, slate, maxYays: int) -> List:
        yays = []

        for i in range(0, maxYays):
            try:
                yay = [self.dss.ds_chief.get_yay(slate,i)]
            except ValueError:
                break
            yays = yays + yay

        return yays
