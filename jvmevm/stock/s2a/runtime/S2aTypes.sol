// SPDX-License-Identifier: MIT
pragma solidity 0.8.30;

error StockPageError(uint256 code);
error S2aClassError(uint256 code, uint256 offset);
error S2aMethodError(uint256 code, uint256 index);
error S2aBytecodeError(uint256 code, uint256 pc);
error S2aControlError(uint256 code);

library S2aTypes {
    uint8 internal constant RUNNABLE = 0;
    uint8 internal constant RETURNED = 1;
    uint8 internal constant STEP_LIMIT = 2;
    uint8 internal constant JAVA_FAULT = 3;
    uint8 internal constant ARITHMETIC_FAULT = 1;

    struct MachineV3 {
        uint32 pc;
        uint8 sp;
        uint8 initialized;
        uint8 lifecycle;
        uint256[8] stack;
        uint256[8] locals;
        int32 result;
        uint8 javaFaultKind;
        uint32 faultPC;
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
