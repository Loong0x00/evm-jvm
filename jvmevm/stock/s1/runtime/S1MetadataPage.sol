// SPDX-License-Identifier: MIT
pragma solidity 0.8.30;

import {S1ClassError} from "./S1Types.sol";

/// Immutable schema-2 metadata. Runtime is exactly STOP || payload.
contract S1MetadataPage {
    constructor(bytes memory payload) {
        uint256 n = payload.length;
        if (n == 0 || n > 8191) revert S1ClassError(5, 0);
        bytes memory runtime = new bytes(n + 1);
        for (uint256 i; i < n; ++i) runtime[i + 1] = payload[i];
        assembly ("memory-safe") { return(add(runtime, 0x20), mload(runtime)) }
    }
}
