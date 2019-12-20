/**
 *Submitted for verification at Etherscan.io on 2019-12-17
*/

// Verified using https://dapp.tools

// hevm: flattened sources of src/McdIlkLineSpell.sol
pragma solidity >0.4.13 >=0.5.12 <0.6.0;

////// lib/ds-math/src/math.sol
/// math.sol -- mixin for inline numerical wizardry

// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.

// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.

// You should have received a copy of the GNU General Public License
// along with this program.  If not, see <http://www.gnu.org/licenses/>.

/* pragma solidity >0.4.13; */

contract DSMath {
    function add(uint x, uint y) internal pure returns (uint z) {
        require((z = x + y) >= x, "ds-math-add-overflow");
    }
    function sub(uint x, uint y) internal pure returns (uint z) {
        require((z = x - y) <= x, "ds-math-sub-underflow");
    }
    function mul(uint x, uint y) internal pure returns (uint z) {
        require(y == 0 || (z = x * y) / y == x, "ds-math-mul-overflow");
    }

    function min(uint x, uint y) internal pure returns (uint z) {
        return x <= y ? x : y;
    }
    function max(uint x, uint y) internal pure returns (uint z) {
        return x >= y ? x : y;
    }
    function imin(int x, int y) internal pure returns (int z) {
        return x <= y ? x : y;
    }
    function imax(int x, int y) internal pure returns (int z) {
        return x >= y ? x : y;
    }

    uint constant WAD = 10 ** 18;
    uint constant RAY = 10 ** 27;

    function wmul(uint x, uint y) internal pure returns (uint z) {
        z = add(mul(x, y), WAD / 2) / WAD;
    }
    function rmul(uint x, uint y) internal pure returns (uint z) {
        z = add(mul(x, y), RAY / 2) / RAY;
    }
    function wdiv(uint x, uint y) internal pure returns (uint z) {
        z = add(mul(x, WAD), y / 2) / y;
    }
    function rdiv(uint x, uint y) internal pure returns (uint z) {
        z = add(mul(x, RAY), y / 2) / y;
    }

    // This famous algorithm is called "exponentiation by squaring"
    // and calculates x^n with x as fixed-point and n as regular unsigned.
    //
    // It's O(log n), instead of O(n) for naive repeated multiplication.
    //
    // These facts are why it works:
    //
    //  If n is even, then x^n = (x^2)^(n/2).
    //  If n is odd,  then x^n = x * x^(n-1),
    //   and applying the equation for even x gives
    //    x^n = x * (x^2)^((n-1) / 2).
    //
    //  Also, EVM division is flooring and
    //    floor[(n-1) / 2] = floor[n / 2].
    //
    function rpow(uint x, uint n) internal pure returns (uint z) {
        z = n % 2 != 0 ? x : RAY;

        for (n /= 2; n != 0; n /= 2) {
            x = rmul(x, x);

            if (n % 2 != 0) {
                z = rmul(z, x);
            }
        }
    }
}

////// lib/dss-interfaces/src/dapp/DSAuthorityAbstract.sol
/* pragma solidity ^0.5.12; */

// https://github.com/dapphub/ds-auth
contract DSAuthorityAbstract {
    function canCall(address, address, bytes4) public view returns (bool);
}

contract DSAuthEventsAbstract {
    event LogSetAuthority (address indexed);
    event LogSetOwner (address indexed);
}

contract DSAuthAbstract is DSAuthEventsAbstract {
    // DSAuthority  public  authority;
    function authority() public view returns (DSAuthorityAbstract);
    // address      public  owner;
    function owner() public view returns (address);
    function setOwner(address) public;
    function setAuthority(DSAuthorityAbstract) public;
}

////// lib/dss-interfaces/src/dapp/DSPauseProxyAbstract.sol
/* pragma solidity ^0.5.12; */

// https://github.com/dapphub/ds-pause
contract DSPauseProxyAbstract {
    // address public owner;
    function owner() public view returns (address);
    function exec(address, bytes memory) public returns (bytes memory);
}
////// lib/dss-interfaces/src/dapp/DSPauseAbstract.sol
/* pragma solidity ^0.5.12; */

/* import { DSPauseProxyAbstract } from "./DSPauseProxyAbstract.sol"; */
/* import { DSAuthorityAbstract } from "./DSAuthorityAbstract.sol"; */

// https://github.com/dapphub/ds-pause
contract DSPauseAbstract {
    function setOwner(address) public;
    function setAuthority(DSAuthorityAbstract) public;
    function setDelay(uint256) public;
    // mapping (bytes32 => bool) public plans;
    function plans(bytes32) public view returns (bool);
    // DSProxyAbstract public proxy;
    function proxy() public view returns (DSPauseProxyAbstract);
    // uint256 public delay;
    function delay() public view returns (uint256);
    function plot(address, bytes32, bytes memory, uint256) public;
    function drop(address, bytes32, bytes memory, uint256) public;
    function exec(address, bytes32, bytes memory, uint256) public returns (bytes memory);
}

////// lib/dss-interfaces/src/dss/VatAbstract.sol
/* pragma solidity ^0.5.12; */

// https://github.com/makerdao/dss/blob/master/src/vat.sol
contract VatAbstract {
    // mapping (address => uint) public wards;
    function wards(address) public view returns (uint256);
    function rely(address) external;
    function deny(address) external;
    struct Ilk {
        uint256 Art;   // Total Normalised Debt     [wad]
        uint256 rate;  // Accumulated Rates         [ray]
        uint256 spot;  // Price with Safety Margin  [ray]
        uint256 line;  // Debt Ceiling              [rad]
        uint256 dust;  // Urn Debt Floor            [rad]
    }
    struct Urn {
        uint256 ink;   // Locked Collateral  [wad]
        uint256 art;   // Normalised Debt    [wad]
    }
    // mapping (address => mapping (address => uint256)) public can;
    function can(address, address) public view returns (uint256);
    function hope(address) external;
    function nope(address) external;
    // mapping (bytes32 => Ilk) public ilks;
    function ilks(bytes32) external view returns (uint256, uint256, uint256, uint256, uint256);
    // mapping (bytes32 => mapping (address => Urn)) public urns;
    function urns(bytes32, address) public view returns (uint256, uint256);
    // mapping (bytes32 => mapping (address => uint256)) public gem;  // [wad]
    function gem(bytes32, address) public view returns (uint256);
    // mapping (address => uint256) public dai;  // [rad]
    function dai(address) public view returns (uint256);
    // mapping (address => uint256) public sin;  // [rad]
    function sin(address) public view returns (uint256);
    // uint256 public debt;  // Total Dai Issued    [rad]
    function debt() public view returns (uint256);
    // uint256 public vice;  // Total Unbacked Dai  [rad]
    function vice() public view returns (uint256);
    // uint256 public Line;  // Total Debt Ceiling  [rad]
    function Line() public view returns (uint256);
    // uint256 public live;  // Access Flag
    function live() public view returns (uint256);
    function init(bytes32) external;
    function file(bytes32, uint256) external;
    function file(bytes32, bytes32, uint256) external;
    function cage() external;
    function slip(bytes32, address, int256) external;
    function flux(bytes32, address, address, uint256) external;
    function move(address, address, uint256) external;
    function frob(bytes32, address, address, address, int256, int256) external;
    function fork(bytes32, address, address, int256, int256) external;
    function grab(bytes32, address, address, address, int256, int256) external;
    function heal(uint256) external;
    function suck(address, address, uint256) external;
    function fold(bytes32, address, int256) external;
}


////// src/McdIlkLineSpell.sol
// Copyright (C) 2019 Maker Foundation
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU Affero General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU Affero General Public License for more details.
//
// You should have received a copy of the GNU Affero General Public License
// along with this program.  If not, see <https://www.gnu.org/licenses/>.

/* pragma solidity ^0.5.12; */

/* import "ds-math/math.sol"; */

/* import "lib/dss-interfaces/src/dss/VatAbstract.sol"; */
/* import "lib/dss-interfaces/src/dapp/DSPauseAbstract.sol"; */

contract SpellAction is DSMath {
    address constant VAT = 0xbA987bDB501d131f766fEe8180Da5d81b34b69d9;

    // not provided in DSMath
    uint constant RAD = 10 ** 45;

    function execute() public {
        uint256 newIlkLine = mul(0, RAD);
        (,,, uint256 oldIlkLine,) = VatAbstract(VAT).ilks("ETH-A");

        uint256 vatLine = (newIlkLine > oldIlkLine) ?
            add(VatAbstract(VAT).Line(), sub(newIlkLine, oldIlkLine)) :
            sub(VatAbstract(VAT).Line(), sub(oldIlkLine, newIlkLine));

        VatAbstract(VAT).file("ETH-A", "line", newIlkLine);
        VatAbstract(VAT).file("Line", vatLine);
    }
}

contract McdIlkLineSpell is DSMath {
    DSPauseAbstract public pause;
    address         public action;
    bytes32         public tag;
    uint256         public eta;
    bytes           public sig;
    bool            public done;

    constructor(address pauseAdd) public {
        pause = DSPauseAbstract(pauseAdd);
        sig = abi.encodeWithSignature("execute()");
        action = address(new SpellAction());
        bytes32 _tag;
        address _action = action;
        assembly { _tag := extcodehash(_action) }
        tag = _tag;
    }

    function schedule() public {
        require(eta == 0, "spell-already-scheduled");
        eta = add(now, DSPauseAbstract(pause).delay());
        pause.plot(action, tag, sig, eta);
    }

    function cast() public {
        require(!done, "spell-already-cast");
        done = true;
        pause.exec(action, tag, sig, eta);
    }
}
