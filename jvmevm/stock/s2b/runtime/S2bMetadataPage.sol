// SPDX-License-Identifier: MIT
pragma solidity 0.8.30;

import {S2bClassError} from "./S2bTypes.sol";

/// Immutable schema-4 metadata. Runtime is exactly STOP || payload.
contract S2bMetadataPage {
    constructor(bytes memory payload) {
        uint256 n = payload.length;
        if (n == 0 || n > 8191) revert S2bClassError(5, 0);
        bytes memory runtime = new bytes(n + 1);
        // Preserve exact STOP || payload bytes without a byte-at-a-time copy.
        // Both ranges are bounded allocations; MCOPY is a standard Cancun opcode.
        assembly ("memory-safe") {
            mcopy(add(runtime, 0x21), add(payload, 0x20), n)
            return(add(runtime, 0x20), mload(runtime))
        }
    }
}
