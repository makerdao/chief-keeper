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
import requests
import time
import types

from web3 import Web3, HTTPProvider

from chief_keeper.database import SimpleDatabase
from chief_keeper.spell import DSSSpell

from pymaker import Address, web3_via_http
from pymaker.util import is_contract_at
from pymaker.gas import GeometricGasPrice
from pymaker.keys import register_keys
from pymaker.lifecycle import Lifecycle
from pymaker.deployment import DssDeployment

# from auction_keeper.gas import DynamicGasPrice

HEALTHCHECK_FILE_PATH = "/tmp/health.log"


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

    logger = logging.getLogger("chief-keeper")

    def __init__(self, args: list, **kwargs):
        """Pass in arguements assign necessary variables/objects and instantiate other Classes"""

        parser = argparse.ArgumentParser("chief-keeper")

        parser.add_argument(
            "--rpc-host",
            type=str,
            required=True,
            help="JSON-RPC host url",
        )

        parser.add_argument(
            "--rpc-timeout",
            type=int,
            default=60,
            help="JSON-RPC timeout (in seconds, default: 60)",
        )

        parser.add_argument(
            "--network",
            type=str,
            required=True,
            help="Network that you're running the Keeper on (options, 'mainnet', 'kovan', 'testnet')",
        )

        parser.add_argument(
            "--eth-from",
            type=str,
            required=True,
            help="Ethereum address from which to send transactions; checksummed (e.g. '0x12AebC')",
        )

        parser.add_argument(
            "--eth-key",
            type=str,
            nargs="*",
            help="Ethereum private key(s) to use (e.g. 'key_file=/path/to/keystore.json,pass_file=/path/to/passphrase.txt')",
        )

        parser.add_argument(
            "--dss-deployment-file",
            type=str,
            required=False,
            help="Json description of all the system addresses (e.g. /Full/Path/To/configFile.json)",
        )

        parser.add_argument(
            "--chief-deployment-block",
            type=int,
            required=False,
            default=0,
            help=" Block that the Chief from dss-deployment-file was deployed at (e.g. 8836668",
        )

        parser.add_argument(
            "--max-errors",
            type=int,
            default=100,
            help="Maximum number of allowed errors before the keeper terminates (default: 100)",
        )

        parser.add_argument(
            "--debug", dest="debug", action="store_true", help="Enable debug output"
        )

        parser.add_argument(
            "--ethgasstation-api-key",
            type=str,
            default=None,
            help="ethgasstation API key",
        )

        parser.add_argument(
            "--blocknative-api-key",
            type=str,
            default=None,
            help="Blocknative API key",
        )

        parser.add_argument(
            "--gas-initial-multiplier",
            type=str,
            default=1.0,
            help="ethgasstation API key",
        )
        parser.add_argument(
            "--gas-reactive-multiplier",
            type=str,
            default=2.25,
            help="gas strategy tuning",
        )
        parser.add_argument(
            "--gas-maximum", type=str, default=5000, help="gas strategy tuning"
        )

        parser.set_defaults(cageFacilitated=False)
        self.arguments = parser.parse_args(args)

        self.web3 = kwargs['web3'] if 'web3' in kwargs else Web3(HTTPProvider(endpoint_uri=self.arguments.rpc_host,
                                                                      request_kwargs={"timeout": self.arguments.rpc_timeout}))

        self.web3.eth.defaultAccount = self.arguments.eth_from
        register_keys(self.web3, self.arguments.eth_key)
        self.our_address = Address(self.arguments.eth_from)

        isConnected = self.web3.isConnected()
        print(f'web3 isConntected is: {isConnected}')

        if self.arguments.dss_deployment_file:
            self.dss = DssDeployment.from_json(
                web3=self.web3,
                conf=open(self.arguments.dss_deployment_file, "r").read(),
            )
        else:
            self.dss = DssDeployment.from_network(
                web3=self.web3, network=self.arguments.network
            )
            print(f"DS-Chief: {self.dss.ds_chief.address}")
        self.deployment_block = self.arguments.chief_deployment_block

        self.max_errors = self.arguments.max_errors
        self.errors = 0

        self.confirmations = 0

        logging.basicConfig(
            format="%(asctime)-15s %(levelname)-8s %(message)s",
            level=(logging.DEBUG if self.arguments.debug else logging.INFO),
        )

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

    @staticmethod
    def get_initial_tip(arguments) -> int:
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
                logging.info(f"Using Blocknative 80% confidence tip {confidence_80_tip}")
                return int(confidence_80_tip * GeometricGasPrice.GWEI)
        except Exception as e:
            logging.error(str(e))

        return int(1.5 * GeometricGasPrice.GWEI)


    @healthy
    def process_block(self):
        """Callback called on each new block. If too many errors, terminate the keeper.
        This is the entrypoint to the Keeper's monitoring logic
        """
        isConnected = self.web3.isConnected()
        logging.info(f'web3 isConntected is: {isConnected}')

        if self.errors >= self.max_errors:
            self.lifecycle.terminate()
        else:
            self.check_hat()
            self.check_eta()

    def check_hat(self):
        """Ensures the Hat is on the proposal (spell, EOA, multisig, etc) with the most approval.

        First, the local database is updated with proposal addresses (yays) that have been `etched` in DSChief between
        the last block reviewed and the most recent block receieved. Next, it simply traverses through each address,
        checking if its approval has surpased the current Hat. If it has, it will `lift` the hat.

        If the current or new hat hasn't been casted nor plotted in the pause, it will `schedule` the spell
        """
        blockNumber = self.web3.eth.blockNumber
        self.logger.info(f"Checking Hat on block {blockNumber}")

        self.database.update_db_yays(blockNumber)
        yays = self.database.db.get(doc_id=2)["yays"]

        hat = self.dss.ds_chief.get_hat().address
        hatApprovals = self.dss.ds_chief.get_approvals(hat)

        contender, highestApprovals = hat, hatApprovals

        for yay in yays:
            contenderApprovals = self.dss.ds_chief.get_approvals(yay)
            if contenderApprovals > highestApprovals:
                contender = yay
                highestApprovals = contenderApprovals

        if contender != hat:
            self.logger.info(f"Lifting hat")
            self.logger.info(f"Old hat ({hat}) with Approvals {hatApprovals}")
            self.logger.info(f"New hat ({contender}) with Approvals {highestApprovals}")
            self.dss.ds_chief.lift(Address(contender)).transact(
                gas_strategy=gas_strategy
            )
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
            gas_strategy = GeometricGasPrice(
                web3=self.web3,
                initial_price=None,
                initial_tip=self.get_initial_tip(self.arguments),
                every_secs=180
            )
            # Functional with DSSSpells but not DSSpells (not compatiable with DSPause)
            if spell.done() == False and self.database.get_eta_inUnix(spell) == 0:
                self.logger.info(f"Scheduling spell ({yay})")
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
