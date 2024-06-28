# This module provides a simplified Lifecycle class for managing the lifecycle 
# of keeper operations. It includes functionality for registering startup and 
# block processing callbacks, handling termination signals, and monitoring 
# blockchain events.
#
# Class:
# - Lifecycle: Manages the lifecycle of keeper operations.
#
# Methods:
# - on_startup: Registers a callback to be run on keeper startup.
# - on_block: Registers a callback to be run for each new block received.
# - terminate: Initiates a graceful shutdown of the keeper.
#
# Usage:
# 1. Initialize a Lifecycle instance with a Web3 instance.
# 2. Use the on_startup method to register a startup callback.
# 3. Use the on_block method to register a block processing callback.
# 4. The class handles SIGINT and SIGTERM signals for graceful shutdown.
#
# Example:
# web3 = Web3(Web3.HTTPProvider('http://localhost:8545'))
# with Lifecycle(web3) as lifecycle:
#     lifecycle.on_startup(startup_function)
#     lifecycle.on_block(block_processing_function)


import logging
import threading
import signal
import time
import datetime
import pytz
from typing import Callable, Optional
from web3 import Web3
from web3.middleware import geth_poa_middleware

class Lifecycle:
    """Simplified Lifecycle for keeper operations."""
    logger = logging.getLogger()

    def __init__(self, web3: Optional[Web3] = None):
        self.web3 = web3

        if self.web3:
            # Add PoA middleware for compatibility with certain chains
            self.web3.middleware_onion.inject(geth_poa_middleware, layer=0)

        self.startup_function: Optional[Callable] = None
        self.block_function: Optional[Callable] = None

        self.terminated_internally = False
        self.terminated_externally = False
        self.fatal_termination = False
        self._last_block_time: Optional[datetime.datetime] = None
        self._on_block_callback: Optional[Callable] = None

    def __enter__(self) -> 'Lifecycle':
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.logger.info("Shutting down the keeper")

    def on_startup(self, callback: Callable) -> None:
        """Register the specified callback to be run on keeper startup."""
        assert callable(callback)
        assert self.startup_function is None
        self.startup_function = callback
        self.logger.info("Executing keeper startup logic")
        self.startup_function()

    def on_block(self, callback: Callable) -> None:
        """Register the specified callback to be run for each new block received by the node."""
        assert callable(callback)
        assert self.web3 is not None
        assert self.block_function is None
        self.block_function = callback
        self._start_watching_blocks()

    def terminate(self, message: Optional[str] = None) -> None:
        if message:
            self.logger.warning(message)
        self.terminated_internally = True

    def _sigint_sigterm_handler(self, sig, frame) -> None:
        if self.terminated_externally:
            self.logger.warning("Graceful keeper termination due to SIGINT/SIGTERM already in progress")
        else:
            self.logger.warning("Keeper received SIGINT/SIGTERM signal, will terminate gracefully")
            self.terminated_externally = True

    def _start_watching_blocks(self) -> None:
        def new_block_callback(block_hash):
            self._last_block_time = datetime.datetime.now(tz=pytz.UTC)
            block = self.web3.eth.get_block(block_hash)
            block_number = block['number']
            if not self.web3.eth.syncing:
                max_block_number = self.web3.eth.block_number
                if block_number >= max_block_number:
                    def on_start():
                        self.logger.debug(f"Processing block #{block_number} ({block_hash.hex()})")

                    def on_finish():
                        self.logger.debug(f"Finished processing block #{block_number} ({block_hash.hex()})")

                    if not self.terminated_internally and not self.terminated_externally and not self.fatal_termination:
                        if not self.block_function():
                            self.logger.debug(f"Ignoring block #{block_number} ({block_hash.hex()}), as previous callback is still running")
                    else:
                        self.logger.debug(f"Ignoring block #{block_number} as keeper is already terminating")
                else:
                    self.logger.debug(f"Ignoring block #{block_number} ({block_hash.hex()}), as there is already block #{max_block_number} available")
            else:
                self.logger.info(f"Ignoring block #{block_number} ({block_hash.hex()}), as the node is syncing")

        def new_block_watch():
            event_filter = self.web3.eth.filter('latest')
            logging.debug(f"Created event filter: {event_filter}")
            while True:
                try:
                    for event in event_filter.get_new_entries():
                        new_block_callback(event)
                except Exception as ex:
                    self.logger.warning(f"Node dropped event emitter; recreating latest block filter: {ex}")
                    event_filter = self.web3.eth.filter('latest')
                finally:
                    time.sleep(1)

        if self.block_function:
            block_filter = threading.Thread(target=new_block_watch, daemon=True)
            block_filter.start()
            self.logger.info("Watching for new blocks")

    def _main_loop(self) -> None:
        signal.signal(signal.SIGINT, self._sigint_sigterm_handler)
        signal.signal(signal.SIGTERM, self._sigint_sigterm_handler)

        while not self.terminated_internally and not self.terminated_externally:
            time.sleep(1)
