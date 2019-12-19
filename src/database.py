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
    def __init__():

        basepath = os.path.dirname(__file__)
        filepath = os.path.abspath(os.path.join(basepath, "db_"+self.arguments.network+".json"))

        if os.path.isfile(filepath) and os.access(filepath, os.R_OK):
        # checks if file exists
            self.logger.info("Simple database exists and is readable")
            self.db = TinyDB(filepath)
        else:
            self.logger.info("Either file is missing or is not readable, creating simple database")
            self.db = TinyDB(filepath)

            blockNumber = self.web3.eth.blockNumber
            self.db.insert({'last_block_checked_for_yays': blockNumber})

            yays = self.get_yays(self.deployment_block, blockNumber)
            self.db.insert({'yays': yays})

            etas = self.get_etas(yays, blockNumber)
            self.db.insert({'upcoming_etas': etas})


    def get_eta_inUnix(self, spell: DSSSpell):
        eta = spell.eta()
        etaInUnix = eta.replace(tzinfo=timezone.utc).timestamp()

        return etaInUnix
