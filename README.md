# chief-keeper

[![Build Status](https://travis-ci.org/makerdao/chief-keeper.svg?branch=master)](https://travis-ci.org/makerdao/chief-keeper)
[![codecov](https://codecov.io/gh/makerdao/chief-keeper/branch/master/graph/badge.svg)](https://codecov.io/gh/makerdao/chief-keeper)


The `chief-keeper` monitors and interacts with [DSChief](https://github.com/dapphub/ds-chief) and DSSSpells, which is the executive voting contract and a type of proposal object of the [Maker Protocol](https://github.com/makerdao/dss).

Its purpose is to lift the `hat` in DSChief as well as streamline executive actions.

To `lift` a spell, that spell must have more approvals than the current `hat`. The approvals of this spell can fluctuate and be surpassed by other spells, some of which could be malicious. This keeper "guards" the `hat` by ensuring the spell with the most approval is always the `hat`.  The `chief-keeper` does this in order to maximize the barrier of entry (approval) to `lift` a spell to the hat, thus acting as a "guard" against malicious governance actions.

While in operation, the `chief-keeper`:
* Monitors each new block for a change in the state of executive votes
* `lift`s the hat for the spell (`yay`) most favored (`approvals[yay]`)
* Schedules spells in the GSM by calling `DSSSpell.schedule()`
* Executes spells after their `eta` has elapsed in the GSM by calling `DSSSpell.cast()`

### Review
The following section assumes familiarity with the [DSChief](https://github.com/dapphub/ds-chief), DSSSpells, and [DSPause](https://github.com/dapphub/ds-pause) (Governance Security Module), as well as the processes within [MakerDAO Governance](https://community-development.makerdao.com/governance).

## Architecture
![alt text](operation.jpeg)

`chief-keeper` interacts directly with the `DS-Chief` and `DSSSpell`s.

## Operation

This keeper is run continuously, and saves a local database of `yays` (spell addresses) and an `yay:eta` dictionary to reduce chain state reads.
If you'd like to create your own database from scratch, first delete `src/database/db_mainnet.json` before running `bin/chief-keeper`; the initial query could take up to 15 minutes.

### Installation

Prerequisites:
- [Python v3.6.6](https://www.python.org/downloads/release/python-366/)
- [virtualenv](https://virtualenv.pypa.io/en/latest/)
    - This project requires *virtualenv* to be installed if you want to use Maker's python tools. This helps with making sure that you are running the right version of python and checks that all of the pip packages that are installed in the **install.sh** are in the right place and have the right versions.

In order to clone the project and install required third-party packages please execute:
```
git clone https://github.com/makerdao/chief-keeper.git
cd chief-keeper
git submodule update --init --recursive
./install.sh
```
If `tinydb` isn't visible/installed through `./install.sh`, simply run `pip3 install tinydb` after the commands above.

For some known Ubuntu and macOS issues see the [pymaker](https://github.com/makerdao/pymaker) README.


### Sample Startup Script

Make a run-chief-keeper.sh to easily spin up the chief-keeper.

```
#!/bin/bash
/full/path/to/chief-keeper/bin/chief-keeper \
	--rpc-host 'sample.ParityNode.com' \
	--network 'kovan' \
	--eth-from '0xABCAddress' \
	--eth-key 'key_file=/full/path/to/keystoreFile.json,pass_file=/full/path/to/passphrase/file.txt' \
	--chief-deployment-block 14374534
```


## Testing

- Download [docker and docker-compose](https://www.docker.com/get-started)

This project uses [pytest](https://docs.pytest.org/en/latest/) for unit testing.  Testing of Multi-collateral Dai is
performed on a Dockerized local testchain included in `tests\config`.

In order to be able to run tests, please install development dependencies first by executing:
```
./install-dev.sh
```

You can then run all tests with:
```
./test.sh
```

## Roadmap
- [ ]  [Dynamic gas pricing strategy](https://github.com/makerdao/market-maker-keeper/blob/master/market_maker_keeper/gas.py)


## License

See [COPYING](https://github.com/makerdao/chief-keeper/blob/master/COPYING) file.

### Disclaimer

YOU (MEANING ANY INDIVIDUAL OR ENTITY ACCESSING, USING OR BOTH THE SOFTWARE INCLUDED IN THIS GITHUB REPOSITORY) EXPRESSLY UNDERSTAND AND AGREE THAT YOUR USE OF THE SOFTWARE IS AT YOUR SOLE RISK.
THE SOFTWARE IN THIS GITHUB REPOSITORY IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
YOU RELEASE AUTHORS OR COPYRIGHT HOLDERS FROM ALL LIABILITY FOR YOU HAVING ACQUIRED OR NOT ACQUIRED CONTENT IN THIS GITHUB REPOSITORY. THE AUTHORS OR COPYRIGHT HOLDERS MAKE NO REPRESENTATIONS CONCERNING ANY CONTENT CONTAINED IN OR ACCESSED THROUGH THE SERVICE, AND THE AUTHORS OR COPYRIGHT HOLDERS WILL NOT BE RESPONSIBLE OR LIABLE FOR THE ACCURACY, COPYRIGHT COMPLIANCE, LEGALITY OR DECENCY OF MATERIAL CONTAINED IN OR ACCESSED THROUGH THIS GITHUB REPOSITORY.
