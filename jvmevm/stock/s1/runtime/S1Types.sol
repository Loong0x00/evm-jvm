// SPDX-License-Identifier: MIT
pragma solidity 0.8.30;

error StockPageError(uint256 code);
error S1ClassError(uint256 code, uint256 offset);
error S1MethodError(uint256 code, uint256 index);
error S1BytecodeError(uint256 code, uint256 pc);
error S1ControlError(uint256 code);

library S1Types {
    uint8 internal constant RUNNABLE = 0;
    uint8 internal constant RETURNED = 1;
    uint8 internal constant STEP_LIMIT = 2;

    struct MachineV2 {
        uint32 pc;
        uint8 sp;
        uint8 initialized;
        uint8 lifecycle;
        uint256[8] stack;
        uint256[8] locals;
        int32 result;
    }

    struct ProgramContext {
        address parser;
        bytes32 parserCodeHash;
        bytes32 classId;
        address rawPage;
        bytes32 rawPageHash;
        bytes32 payloadHash;
        address metadataPage;
        bytes32 metadataHash;
        uint16 methodIndex;
        bytes32 programId;
    }
}
