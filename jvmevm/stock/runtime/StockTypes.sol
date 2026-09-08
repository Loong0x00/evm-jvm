// SPDX-License-Identifier: MIT
pragma solidity 0.8.30;

library StockTypes {
    struct Machine {
        uint32 pc;
        uint8 sp;
        uint8 initialized;
        uint256[8] stack;
        uint256[4] locals;
        bool done;
        int32 result;
    }
}
