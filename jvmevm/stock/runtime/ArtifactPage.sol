// SPDX-License-Identifier: MIT
pragma solidity 0.8.30;

error StockPageError(uint256 code);

/// An immutable ordinary EVM code page. Runtime code is exactly STOP || payload.
contract ArtifactPage {
    constructor(bytes memory payload) {
        uint256 n = payload.length;
        if (n == 0 || n > 4096) revert StockPageError(1);
        bytes memory runtime = new bytes(n + 1);
        for (uint256 i; i < n; ++i) runtime[i + 1] = payload[i];
        assembly ("memory-safe") {
            return(add(runtime, 0x20), mload(runtime))
        }
    }
}
