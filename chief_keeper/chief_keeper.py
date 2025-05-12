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

import argparse
import logging
import sys
import os
import requests
import time
import types

from web3 import Web3, HTTPProvider
from web3.exceptions import TimeExhausted

from urllib.parse import urlparse

from chief_keeper.database import SimpleDatabase
from chief_keeper.spell import DSSSpell
from chief_keeper.metrics import (
    MetricsServer, 
    record_new_hat_event, 
    set_hat_validity, 
    record_schedule_called, 
    record_lift_called, 
    record_invalid_lift_called
)

from pymaker import Address, web3_via_http
from pymaker.util import is_contract_at
from pymaker.gas import GeometricGasPrice
from pymaker.keys import register_keys
from pymaker.lifecycle import Lifecycle
from pymaker.deployment import DssDeployment

HEALTHCHECK_FILE_PATH = "/tmp/health.log"
BACKOFF_MAX_TIME = 120

class ExitOnCritical(logging.StreamHandler):
    """Custom class to terminate script execution once
    log records with severity level ERROR or higher occurred"""

    def emit(self, record):
        super().emit(record)
        if record.levelno > logging.ERROR:
            sys.exit(1)


logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S%z",
    force=True,
    handlers=[ExitOnCritical()],
)
logger = logging.getLogger()
log_level = logging.getLevelName(os.environ.get("LOG_LEVEL") or "INFO")
logger.setLevel(log_level)


def healthy(func):
    def wrapper(*args, **kwargs):
        ts = int(time.time())
        print(f"Health-check passed, timestamp: {ts}")
        with open(HEALTHCHECK_FILE_PATH, "w") as f:
            f.write(str(ts) + "\n")
        return func(*args, **kwargs)

    return wrapper


class ChiefKeeper:
    """Keeper that lifts the hat and streamlines executive actions"""

    def __init__(self, args: list, **kwargs):
        """Pass in arguements assign necessary variables/objects and instantiate other Classes"""

        parser = argparse.ArgumentParser("chief-keeper")

        parser.add_argument("--rpc-primary-url", type=str, required=True, help="Primary JSON-RPC host URL")
        parser.add_argument("--rpc-primary-timeout", type=int, default=1200, help="Primary JSON-RPC timeout (in seconds, default: 1200)")
        parser.add_argument("--rpc-backup-url", type=str, required=True, help="Backup JSON-RPC host URL")
        parser.add_argument("--rpc-backup-timeout", type=int, default=1200, help="Backup JSON-RPC timeout (in seconds, default: 1200)")
        parser.add_argument("--network", type=str, required=True, help="Network that you're running the Keeper on (options, 'mainnet', 'kovan', 'testnet')")
        parser.add_argument("--eth-from", type=str, required=True, help="Ethereum address from which to send transactions; checksummed (e.g. '0x12AebC')")
        parser.add_argument("--eth-key", type=str, nargs="*", help="Ethereum private key(s) to use (e.g. 'key_file=/path/to/keystore.json,pass_file=/path/to/passphrase.txt')")
        parser.add_argument("--dss-deployment-file", type=str, required=False, help="Json description of all the system addresses (e.g. /Full/Path/To/configFile.json)")
        parser.add_argument("--chief-deployment-block", type=int, required=False, default=0, help="Block that the Chief from dss-deployment-file was deployed at (e.g. 8836668")
        parser.add_argument("--max-errors", type=int, default=100, help="Maximum number of allowed errors before the keeper terminates (default: 100)")
        parser.add_argument("--debug", dest="debug", action="store_true", help="Enable debug output")
        parser.add_argument("--blocknative-api-key", type=str, default=None, help="Blocknative API key")
        parser.add_argument("--gas-initial-multiplier", type=float, default=1.0, help="gas multiplier")
        parser.add_argument("--gas-reactive-multiplier", type=float, default=2.25, help="gas strategy tuning")
        parser.add_argument("--gas-maximum", type=int, default=5000, help="gas strategy tuning")

        parser.set_defaults(cageFacilitated=False)
        self.arguments = parser.parse_args(args)

        # Initialize logger before any method that uses it
        self.logger = logger

        self.print_arguments()

        self.web3 = None
        self.node_type = None
        self._initialize_blockchain_connection()

        # Set the Ethereum address and register keys
        # self.web3.eth.defaultAccount = self.arguments.eth_from
        # register_keys(self.web3, self.arguments.eth_key)
        self.our_address = Address(self.arguments.eth_from)

        if self.arguments.dss_deployment_file:
            self.dss = DssDeployment.from_json(
                web3=self.web3,
                conf=open(self.arguments.dss_deployment_file, "r").read(),
            )
        else:
            self.dss = DssDeployment.from_network(
                web3=self.web3, network=self.arguments.network
            )
            self.logger.info(f"DS-Chief: {self.dss.ds_chief.address}")
        self.deployment_block = self.arguments.chief_deployment_block

        self.max_errors = self.arguments.max_errors
        self.errors = 0

        self.confirmations = 0
        
        # Start the metrics server
        self.metrics_server = MetricsServer()
        self.metrics_server.start()

    def print_arguments(self):
        """Print all the arguments passed to the script."""
        for arg in vars(self.arguments):
            self.logger.info(f"{arg}: {getattr(self.arguments, arg)}")

    def _initialize_blockchain_connection(self):
        """Initialize connection with Ethereum node."""
        if not self._connect_to_primary_node():
            self.logger.info("Switching to backup node.")
            if not self._connect_to_backup_node():
                self.logger.critical(
                    "Error: Couldn't connect to the primary and backup Ethereum nodes."
                )

    def _connect_to_primary_node(self):
        """Connect to the primary Ethereum node"""
        return self._connect_to_node(
            self.arguments.rpc_primary_url, self.arguments.rpc_primary_timeout, "primary"
        )

    def _connect_to_backup_node(self):
        """Connect to the backup Ethereum node"""
        return self._connect_to_node(
            self.arguments.rpc_backup_url, self.arguments.rpc_backup_timeout, "backup"
        )

    def _connect_to_node(self, rpc_url, rpc_timeout, node_type):
        """Connect to an Ethereum node"""
        try:
            _web3 = Web3(HTTPProvider(rpc_url, {"timeout": rpc_timeout}))
        except (TimeExhausted, Exception) as e:
            self.logger.error(f"Error connecting to Ethereum node: {e}")
            return False
        else:
            if _web3.isConnected():
                self.web3 = _web3
                self.node_type = node_type
                return self._configure_web3()
        return False

    def _configure_web3(self):
        """Configure Web3 connection with private key"""
        try:
            self.web3.eth.defaultAccount = self.arguments.eth_from
            register_keys(self.web3, self.arguments.eth_key)
        except Exception as e:
            self.logger.error(f"Error configuring Web3: {e}")
            return False
        else:
            node_hostname = urlparse(self.web3.provider.endpoint_uri).hostname
            self.logger.info(f"Connected to Ethereum node at {node_hostname}")
            return True

    def main(self):
        """Initialize the lifecycle and enter into the Keeper Lifecycle controller.

        Each function supplied by the lifecycle will accept a callback function that will be executed.
        The lifecycle.on_block() function will enter into an infinite loop, but will gracefully shutdown
        if it recieves a SIGINT/SIGTERM signal.
        """

        with Lifecycle(self.web3) as lifecycle:
            self.lifecycle = lifecycle
            lifecycle.on_startup(self.check_deployment)
            lifecycle.on_block(self.process_block)

    def check_deployment(self):
        self.logger.info("")
        self.logger.info("Please confirm the deployment details")
        self.logger.info(
            f"Keeper Balance: {self.web3.eth.getBalance(self.our_address.address) / (10**18)} ETH"
        )
        self.logger.info(f"DS-Chief: {self.dss.ds_chief.address}")
        self.logger.info(f"DS-Pause: {self.dss.pause.address}")
        self.logger.info("")
        self.initial_query()

    def initial_query(self):
        """Updates a locally stored database with the DS-Chief state since its last update.
        If a local database is not found, create one and query the DS-Chief state since its deployment.
        """
        self.logger.info("")
        self.logger.info(
            "Querying DS-Chief state since last update ( !! Could take up to 15 minutes !! )"
        )

        self.database = SimpleDatabase(
            self.web3, self.deployment_block, self.arguments.network, self.dss
        )
        result = self.database.create()

        self.logger.info(result)

    def get_initial_tip(self, arguments) -> int:
        try:
            result = requests.get(
                url='https://api.blocknative.com/gasprices/blockprices',
                headers={
                    'Authorization': arguments.blocknative_api_key
                },
                timeout=15
            )
            if result.ok and result.content:
                confidence_80_tip = result.json().get('blockPrices')[0]['estimatedPrices'][3]['maxPriorityFeePerGas']
                self.logger.info(f"Using Blocknative 80% confidence tip {confidence_80_tip}")
                self.logger.info(int(confidence_80_tip * GeometricGasPrice.GWEI))
                return int(confidence_80_tip * GeometricGasPrice.GWEI)
        except Exception as e:
            logging.error(str(e))

        return int(1.5 * GeometricGasPrice.GWEI)


    @healthy
    def process_block(self):
        """Callback called on each new block. If too many errors, terminate the keeper.
        This is the entrypoint to the Keeper's monitoring logic
        """
        try:
            isConnected = self.web3.isConnected()
            self.logger.info(f'web3 isConnected: {isConnected}')

            if self.errors >= self.max_errors:
                self.lifecycle.terminate()
            else:
                self.check_hat()
                self.check_eta()
        except (TimeExhausted, Exception) as e:
            self.logger.error(f"Error processing block: {e}")
            self.errors += 1

    def check_hat(self):
        """Ensures the Hat is on the proposal (spell, EOA, multisig, etc) with the most approval.

        First, the local database is updated with proposal addresses (yays) that have been `etched` in DSChief between
        the last block reviewed and the most recent block receieved. Next, it simply traverses through each address,
        checking if its approval has surpased the current Hat. If it has, it will `lift` the hat.

        If the current or new hat hasn't been casted nor plotted in the pause, it will `schedule` the spell
        """
        blockNumber = self.web3.eth.blockNumber
        self.logger.info(f"Checking Hat on block {blockNumber}")

        try:
            self.database.update_db_yays(blockNumber)
        except (TimeExhausted, Exception) as e:
            self.logger.error(f"Error updating database yays: {e}")
            self.errors += 1
            return

        yays = self.database.db.get(doc_id=2)["yays"]

        hat = self.dss.ds_chief.get_hat().address
        hatApprovals = self.dss.ds_chief.get_approvals(hat)

        # Check if hat is valid (has approvals)
        is_valid_hat = hatApprovals > 0
        set_hat_validity(is_valid_hat, hat)
        
        contender, highestApprovals = hat, hatApprovals

        gas_strategy = GeometricGasPrice(
            web3=self.web3,
            initial_price=None,
            initial_tip=self.get_initial_tip(self.arguments),
            every_secs=180
        )

        for yay in yays:
            contenderApprovals = self.dss.ds_chief.get_approvals(yay)
            if contenderApprovals > highestApprovals:
                contender = yay
                highestApprovals = contenderApprovals

        if contender != hat:
            self.logger.info(f"Lifting hat")
            self.logger.info(f"Old hat ({hat}) with Approvals {hatApprovals}")
            self.logger.info(f"New hat ({contender}) with Approvals {highestApprovals}")
            
            # Record lift attempt
            record_lift_called(hat, contender)
            
            try:
                self.dss.ds_chief.lift(Address(contender)).transact(
                    gas_strategy=gas_strategy
                )
                # Record successful hat change
                record_new_hat_event(hat, contender)
            except Exception as e:
                # Record invalid lift attempt
                record_invalid_lift_called(hat, contender)
                self.logger.error(f"Error lifting hat: {e}")
                raise
        else:
            self.logger.info(f"Current hat ({hat}) with Approvals {hatApprovals}")

        # Read the hat; either is equivalent to the contender or old hat
        hatNew = self.dss.ds_chief.get_hat().address
        if hatNew != hat:
            self.logger.info(f"Confirmed ({contender}) now has the hat")

        spell = (
            DSSSpell(self.web3, Address(hatNew))
            if is_contract_at(self.web3, Address(hatNew))
            else None
        )

        # Schedules spells that haven't been scheduled nor casted
        if spell is not None:
            # Functional with DSSSpells but not DSSpells (not compatiable with DSPause)
            if spell.done() == False and self.database.get_eta_inUnix(spell) == 0:
                self.logger.info(f"Scheduling spell ({yay})")
                
                # Record schedule attempt
                record_schedule_called(yay)
                
                spell.schedule().transact(gas_strategy=gas_strategy)
        else:
            self.logger.warning(
                f"Spell is an EOA or 0x0, so keeper will not attempt to call schedule()"
            )

    def check_eta(self):
        """Cast spells that meet their schedule.

        First, the local database is updated with spells that have been scheduled between the last block
        reviewed and the most recent block receieved. Next, it simply traverses through each spell address,
        checking if its schedule has been reached/passed. If it has, it attempts to `cast` the spell.
        """
        blockNumber = self.web3.eth.blockNumber
        now = self.web3.eth.getBlock(blockNumber).timestamp
        self.logger.info(f"Checking scheduled spells on block {blockNumber}")

        self.database.update_db_etas(blockNumber)
        etas = self.database.db.get(doc_id=3)["upcoming_etas"]

        yays = list(etas.keys())

        for yay in yays:
            if etas[yay] <= now:
                spell = (
                    DSSSpell(self.web3, Address(yay))
                    if is_contract_at(self.web3, Address(yay))
                    else None
                )

                if spell is not None:
                    gas_strategy = GeometricGasPrice(
                        web3=self.web3,
                        initial_price=None,
                        initial_tip=self.get_initial_tip(self.arguments),
                        every_secs=180
                    )
                    if spell.done() == False:
                        self.logger.info(f"Casting spell ({spell.address.address})")
                        receipt = spell.cast().transact(gas_strategy=gas_strategy)

                        if receipt is None or receipt.successful == True:
                            del etas[yay]
                    else:
                        del etas[yay]
                else:
                    self.logger.warning(
                        f"Spell is an EOA or 0x0, so keeper will not attempt to call cast()"
                    )
                    del etas[yay]

        self.database.db.update({"upcoming_etas": etas}, doc_ids=[3])


if __name__ == "__main__":
    ChiefKeeper(sys.argv[1:]).main()
