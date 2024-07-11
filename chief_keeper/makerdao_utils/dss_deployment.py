# This file is part of Maker Keeper Framework.
#
# Copyright (C) 2017-2018 reverendus, bargst
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
import os
import re

from typing import Dict, List, Optional
from web3 import Web3

from chief_keeper.utils.address import Address

from chief_keeper.makerdao_utils.auctions import Clipper, Flapper, Flipper, Flopper
from chief_keeper.makerdao_utils.dss import Cat, Dog, Jug, Pot, Spotter, TokenFaucet, Vat, Vow
from chief_keeper.makerdao_utils.collateral import Collateral
from chief_keeper.makerdao_utils.join import DaiJoin, GemJoin, GemJoin5
from chief_keeper.makerdao_utils.proxy import ProxyRegistry, DssProxyActionsDsr
from chief_keeper.makerdao_utils.feed import DSValue
from chief_keeper.makerdao_utils.governance import DSPause, DSChief
from chief_keeper.makerdao_utils.token import DSToken, DSEthToken
from chief_keeper.makerdao_utils.oracles import OSM
from chief_keeper.makerdao_utils.shutdown import ShutdownModule, End
from chief_keeper.makerdao_utils.cdp_manager import CdpManager
from chief_keeper.makerdao_utils.dsr_manager import DsrManager

class DssDeployment:
    """Represents a Dai Stablecoin System deployment for multi-collateral Dai (MCD).

    Static method `from_json()` should be used to instantiate all the objet of
    a deployment from a json description of all the system addresses.
    """

    NETWORKS = {
        "1": "mainnet"
    }

    class Config:
        def __init__(self, pause: DSPause, vat: Vat, vow: Vow, jug: Jug, cat: Cat, dog: Dog, flapper: Flapper,
                     flopper: Flopper, pot: Pot, dai: DSToken, dai_join: DaiJoin, mkr: DSToken,
                     spotter: Spotter, ds_chief: DSChief, esm: ShutdownModule, end: End,
                     proxy_registry: ProxyRegistry, dss_proxy_actions: DssProxyActionsDsr, cdp_manager: CdpManager,
                     dsr_manager: DsrManager, faucet: TokenFaucet, collaterals: Optional[Dict[str, Collateral]] = None):
            self.pause = pause
            self.vat = vat
            self.vow = vow
            self.jug = jug
            self.cat = cat
            self.dog = dog
            self.flapper = flapper
            self.flopper = flopper
            self.pot = pot
            self.dai = dai
            self.dai_join = dai_join
            self.mkr = mkr
            self.spotter = spotter
            self.ds_chief = ds_chief
            self.esm = esm
            self.end = end
            self.proxy_registry = proxy_registry
            self.dss_proxy_actions = dss_proxy_actions
            self.cdp_manager = cdp_manager
            self.dsr_manager = dsr_manager
            self.faucet = faucet
            self.collaterals = collaterals or {}

        @staticmethod
        def from_json(web3: Web3, conf: str):
            def address_in_configs(key: str, conf: str) -> bool:
                if key not in conf:
                    return False
                elif not conf[key]:
                    return False
                elif conf[key] == "0x0000000000000000000000000000000000000000":
                    return False
                else:
                    return True

            conf = json.loads(conf)
            pause = DSPause(web3, Address(conf['MCD_PAUSE']))
            vat = Vat(web3, Address(conf['MCD_VAT']))
            vow = Vow(web3, Address(conf['MCD_VOW']))
            jug = Jug(web3, Address(conf['MCD_JUG']))
            cat = Cat(web3, Address(conf['MCD_CAT'])) if address_in_configs('MCD_CAT', conf) else None
            dog = Dog(web3, Address(conf['MCD_DOG'])) if address_in_configs('MCD_DOG', conf) else None
            dai = DSToken(web3, Address(conf['MCD_DAI']))
            dai_adapter = DaiJoin(web3, Address(conf['MCD_JOIN_DAI']))
            flapper = Flapper(web3, Address(conf['MCD_FLAP']))
            flopper = Flopper(web3, Address(conf['MCD_FLOP']))
            pot = Pot(web3, Address(conf['MCD_POT']))
            mkr = DSToken(web3, Address(conf['MCD_GOV']))
            spotter = Spotter(web3, Address(conf['MCD_SPOT']))
            ds_chief = DSChief(web3, Address(conf['MCD_ADM']))
            esm = ShutdownModule(web3, Address(conf['MCD_ESM']))
            end = End(web3, Address(conf['MCD_END']))
            proxy_registry = ProxyRegistry(web3, Address(conf['PROXY_REGISTRY']))
            dss_proxy_actions = DssProxyActionsDsr(web3, Address(conf['PROXY_ACTIONS_DSR']))
            cdp_manager = CdpManager(web3, Address(conf['CDP_MANAGER']))
            dsr_manager = DsrManager(web3, Address(conf['DSR_MANAGER']))
            faucet = TokenFaucet(web3, Address(conf['FAUCET'])) if address_in_configs('FAUCET', conf) else None

            collaterals = {}
            for name in DssDeployment.Config._infer_collaterals_from_addresses(conf.keys()):
                ilk = vat.ilk(name[0].replace('_', '-'))
                if name[1] == "ETH":
                    gem = DSEthToken(web3, Address(conf[name[1]]))
                else:
                    gem = DSToken(web3, Address(conf[name[1]]))

                if name[1] in ['USDC', 'WBTC', 'TUSD', 'USDT', 'GUSD', 'RENBTC']:
                    adapter = GemJoin5(web3, Address(conf[f'MCD_JOIN_{name[0]}']))
                else:
                    adapter = GemJoin(web3, Address(conf[f'MCD_JOIN_{name[0]}']))

                # PIP contract may be a DSValue, OSM, or bogus address.
                pip_name = f'PIP_{name[1]}'
                pip_address = Address(conf[pip_name]) if pip_name in conf and conf[pip_name] else None
                val_name = f'VAL_{name[1]}'
                val_address = Address(conf[val_name]) if val_name in conf and conf[val_name] else None
                if pip_address:     # Configure OSM as price source
                    pip = OSM(web3, pip_address)
                elif val_address:   # Configure price using DSValue
                    pip = DSValue(web3, val_address)
                else:
                    pip = None

                auction = None
                if f'MCD_FLIP_{name[0]}' in conf:
                    auction = Flipper(web3, Address(conf[f'MCD_FLIP_{name[0]}']))
                elif f'MCD_CLIP_{name[0]}' in conf:
                    auction = Clipper(web3, Address(conf[f'MCD_CLIP_{name[0]}']))

                collateral = Collateral(ilk=ilk, gem=gem, adapter=adapter, auction=auction, pip=pip, vat=vat)
                collaterals[ilk.name] = collateral

            return DssDeployment.Config(pause, vat, vow, jug, cat, dog, flapper, flopper, pot,
                                        dai, dai_adapter, mkr, spotter, ds_chief, esm, end,
                                        proxy_registry, dss_proxy_actions, cdp_manager,
                                        dsr_manager, faucet, collaterals)

        @staticmethod
        def _infer_collaterals_from_addresses(keys: List[str]) -> List:
            collaterals = []
            for key in keys:
                match = re.search(r'MCD_[CF]LIP_(?!CALC)((\w+)_\w+)', key)
                if match:
                    collaterals.append((match.group(1), match.group(2)))
                    continue
                match = re.search(r'MCD_[CF]LIP_(?!CALC)(\w+)', key)
                if match:
                    collaterals.append((match.group(1), match.group(1)))

            return collaterals

        # def to_dict(self) -> dict:
        #     conf_dict = {
        #         'MCD_PAUSE': self.pause.address.address,
        #         'MCD_VAT': self.vat.address.address,
        #         'MCD_VOW': self.vow.address.address,
        #         'MCD_JUG': self.jug.address.address,
        #         'MCD_FLAP': self.flapper.address.address,
        #         'MCD_FLOP': self.flopper.address.address,
        #         'MCD_POT': self.pot.address.address,
        #         'MCD_DAI': self.dai.address.address,
        #         'MCD_JOIN_DAI': self.dai_join.address.address,
        #         'MCD_GOV': self.mkr.address.address,
        #         'MCD_SPOT': self.spotter.address.address,
        #         'MCD_ADM': self.ds_chief.address.address,
        #         'MCD_ESM': self.esm.address.address,
        #         'MCD_END': self.end.address.address,
        #         'PROXY_REGISTRY': self.proxy_registry.address.address,
        #         'PROXY_ACTIONS_DSR': self.dss_proxy_actions.address.address,
        #         'CDP_MANAGER': self.cdp_manager.address.address,
        #         'DSR_MANAGER': self.dsr_manager.address.address
        #     }

        #     if self.cat:
        #         conf_dict['MCD_CAT'] = self.cat.address.address
        #     if self.dog:
        #         conf_dict['MCD_DOG'] = self.dog.address.address
        #     if self.faucet:
        #         conf_dict['FAUCET'] = self.faucet.address.address

        #     for collateral in self.collaterals.values():
        #         match = re.search(r'(\w+)(?:-\w+)?', collateral.ilk.name)
        #         name = (collateral.ilk.name.replace('-', '_'), match.group(1))
        #         conf_dict[name[1]] = collateral.gem.address.address
        #         if collateral.pip:
        #             conf_dict[f'PIP_{name[1]}'] = collateral.pip.address.address
        #         conf_dict[f'MCD_JOIN_{name[0]}'] = collateral.adapter.address.address
        #         if collateral.flipper:
        #             conf_dict[f'MCD_FLIP_{name[0]}'] = collateral.flipper.address.address
        #         elif collateral.clipper:
        #             conf_dict[f'MCD_CLIP_{name[0]}'] = collateral.clipper.address.address

        #     return conf_dict

        # def to_json(self) -> str:
        #     return json.dumps(self.to_dict())

    def __init__(self, web3: Web3, config: Config):
        assert isinstance(web3, Web3)
        assert isinstance(config, DssDeployment.Config)

        self.web3 = web3
        self.config = config
        # self.pause = config.pause
        # self.vat = config.vat
        # self.vow = config.vow
        # self.jug = config.jug
        # self.cat = config.cat
        # self.dog = config.dog
        # self.flapper = config.flapper
        # self.flopper = config.flopper
        # self.pot = config.pot
        # self.dai = config.dai
        # self.dai_adapter = config.dai_join
        # self.mkr = config.mkr
        # self.collaterals = config.collaterals
        # self.spotter = config.spotter
        # self.ds_chief = config.ds_chief
        # self.esm = config.esm
        # self.end = config.end
        # self.proxy_registry = config.proxy_registry
        # self.dss_proxy_actions = config.dss_proxy_actions
        # self.cdp_manager = config.cdp_manager
        # self.dsr_manager = config.dsr_manager
        # self.faucet = config.faucet

    @staticmethod
    def from_json(web3: Web3, conf: str):
        return DssDeployment(web3, DssDeployment.Config.from_json(web3, conf))

    def to_json(self) -> str:
        return self.config.to_json()

    # @staticmethod
    # def from_node(web3: Web3):
    #     assert isinstance(web3, Web3)

    #     network = DssDeployment.NETWORKS.get(web3.net.version, "testnet")

    #     return DssDeployment.from_network(web3=web3, network=network)

    @staticmethod
    def from_network(web3: Web3, network: str):
        assert isinstance(web3, Web3)
        assert isinstance(network, str)

        cwd = os.path.dirname(os.path.realpath(__file__))
        addresses_path = os.path.join(cwd, "../config", f"{network}-addresses.json")

        return DssDeployment.from_json(web3=web3, conf=open(addresses_path, "r").read())

    # def approve_dai(self, usr: Address, **kwargs):
    #     """
    #     Allows the user to draw Dai from and repay Dai to their CDPs.

    #     Args
    #         usr: Recipient of Dai from one or more CDPs
    #     """
    #     assert isinstance(usr, Address)

    #     gas_price = kwargs['gas_price'] if 'gas_price' in kwargs else DefaultGasPrice()
    #     self.dai_adapter.approve(approval_function=hope_directly(from_address=usr, gas_price=gas_price),
    #                              source=self.vat.address)
    #     self.dai.approve(self.dai_adapter.address).transact(from_address=usr, gas_price=gas_price)

    # def active_auctions(self) -> dict:
    #     flips = {}
    #     clips = {}
    #     for collateral in self.collaterals.values():
    #         # Each collateral has it's own liquidation contract; add auctions from each.
    #         if collateral.flipper:
    #             flips[collateral.ilk.name] = collateral.flipper.active_auctions()
    #         elif collateral.clipper:
    #             clips[collateral.ilk.name] = collateral.clipper.active_auctions()

    #     return {
    #         "flips": flips,
    #         "clips": clips,
    #         "flaps": self.flapper.active_auctions(),
    #         "flops": self.flopper.active_auctions()
    #     }

    def __repr__(self):
        return f'DssDeployment({self.config.to_json()})'