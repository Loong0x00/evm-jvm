// SPDX-License-Identifier: MIT
pragma solidity 0.8.30;

import {S2aTypes, S2aControlError} from "./S2aTypes.sol";

interface IS2aClassRegistry {
    function classRecord(bytes32 classId) external view returns (address metadataPage, bytes32 metadataHash);
}

library S2aCodec {
    bytes32 internal constant METADATA_MAGIC = keccak256("JVMEVM:S2A:METADATA:3");
    bytes32 internal constant DCLASS = keccak256("JVMEVM:S2A:CLASS");
    bytes32 internal constant DPROGRAM = keccak256("JVMEVM:S2A:PROGRAM");
    bytes32 internal constant DINPUT = keccak256("JVMEVM:S2A:INPUT");

    struct ClassView {
        address rawPage;
        bytes32 rawPageHash;
        bytes32 payloadHash;
        address metadataPage;
        bytes32 metadataHash;
        uint16 classAccess;
        uint32 rawLength;
        uint16 cpCount;
        uint16 methodCount;
        uint16 literalCount;
    }

    struct MethodView {
        bytes32 nameHash;
        bytes32 descriptorHash;
        uint16 declaredIndex;
        uint16 access;
        uint32 codeOffset;
        uint16 codeLength;
        uint8 maxStack;
        uint8 maxLocals;
        uint8 argc;
        uint8 errorDomain;
        uint8 errorCode;
        uint32 errorLocation;
        uint16 literalBase;
        uint16 literalCount;
        uint256 starts;
    }

    function codeInfo(address target) internal view returns (uint256 size, bytes32 hash) {
        assembly ("memory-safe") {
            size := extcodesize(target)
            hash := extcodehash(target)
        }
    }

    function loadClass(address parser, bytes32 parserCodeHash, bytes32 classId)
        internal view returns (ClassView memory c)
    {
        (uint256 parserSize, bytes32 actualParserHash) = codeInfo(parser);
        if (parserSize == 0 || actualParserHash != parserCodeHash) revert S2aControlError(2);

        (bool ok, bytes memory answer) = parser.staticcall(
            abi.encodeCall(IS2aClassRegistry.classRecord, (classId))
        );
        if (!ok || answer.length != 64) revert S2aControlError(2);
        uint256 pageWord;
        bytes32 recordedHash;
        assembly ("memory-safe") {
            pageWord := mload(add(answer, 0x20))
            recordedHash := mload(add(answer, 0x40))
        }
        if (pageWord >> 160 != 0 || pageWord == 0 || recordedHash == bytes32(0)) {
            revert S2aControlError(2);
        }
        c.metadataPage = address(uint160(pageWord));
        c.metadataHash = recordedHash;

        (uint256 metadataSize, bytes32 actualMetadataHash) = codeInfo(c.metadataPage);
        if (metadataSize < 193 || metadataSize > 8192 || actualMetadataHash != c.metadataHash) {
            revert S2aControlError(2);
        }
        // Only the fixed header is needed here. Callers fetch selected method
        // records and literal slices separately rather than copying the page.
        bytes memory header = new bytes(193);
        address metadataTarget = c.metadataPage;
        assembly ("memory-safe") {
            extcodecopy(metadataTarget, add(header, 0x20), 0, 193)
        }
        if (header[0] != 0x00 || word(header, 0) != METADATA_MAGIC) revert S2aControlError(2);

        uint256 h1 = uint256(word(header, 1));
        if (h1 >> 176 != 0) revert S2aControlError(2);
        c.rawPage = address(uint160(h1));
        c.classAccess = uint16(h1 >> 160);
        if ((c.classAccess & 0x0001) == 0 || (c.classAccess & ~uint16(0x0431)) != 0
            || (c.classAccess & 0x0410) == 0x0410) revert S2aControlError(2);
        c.rawPageHash = word(header, 2);
        c.payloadHash = word(header, 3);
        // H4 is bound through the immutable metadata code hash.
        uint256 h5 = uint256(word(header, 5));
        if (h5 >> 80 != 0) revert S2aControlError(2);
        c.rawLength = uint32(h5);
        c.cpCount = uint16(h5 >> 32);
        c.methodCount = uint16(h5 >> 48);
        c.literalCount = uint16(h5 >> 64);
        if (c.rawLength == 0 || c.rawLength > 4096 || c.cpCount == 0 || c.cpCount > 512
            || c.methodCount > 32 || c.literalCount > 256) revert S2aControlError(2);
        uint256 expectedMetadataSize = 1 + 192 + uint256(c.methodCount) * 128
            + uint256(c.literalCount) * 8;
        if (metadataSize != expectedMetadataSize) revert S2aControlError(2);

        (uint256 rawSize, bytes32 actualRawHash) = codeInfo(c.rawPage);
        if (rawSize != uint256(c.rawLength) + 1 || actualRawHash != c.rawPageHash) {
            revert S2aControlError(2);
        }
        bytes32 first;
        address rawTarget = c.rawPage;
        assembly ("memory-safe") {
            extcodecopy(rawTarget, 0, 0, 1)
            first := mload(0)
        }
        if (bytes1(first) != 0x00) revert S2aControlError(2);
        // The parser-issued metadata binds payloadHash, while rawPageHash binds
        // every raw runtime byte. Execution therefore copies only selected Code.

        bytes32 computedClassId = keccak256(abi.encode(
            DCLASS, uint32(3), parserCodeHash, c.rawPage, c.rawPageHash,
            c.payloadHash, c.metadataHash
        ));
        if (computedClassId != classId) revert S2aControlError(2);

    }

    function loadMethod(ClassView memory c, uint16 index)
        internal view returns (MethodView memory m)
    {
        if (index >= c.methodCount) revert S2aControlError(2);
        bytes memory record = new bytes(128);
        address target = c.metadataPage;
        uint256 sourceOffset = 1 + 192 + uint256(index) * 128;
        assembly ("memory-safe") {
            extcodecopy(target, add(record, 0x20), sourceOffset, 128)
        }
        m.nameHash = recordWord(record, 0);
        m.descriptorHash = recordWord(record, 1);
        uint256 p = uint256(recordWord(record, 2));
        m.starts = uint256(recordWord(record, 3));
        if (p >> 184 != 0) revert S2aControlError(2);
        m.declaredIndex = uint16(p);
        m.access = uint16(p >> 16);
        m.codeOffset = uint32(p >> 32);
        m.codeLength = uint16(p >> 64);
        m.maxStack = uint8(p >> 80);
        m.maxLocals = uint8(p >> 88);
        m.argc = uint8(p >> 96);
        m.errorDomain = uint8(p >> 104);
        m.errorCode = uint8(p >> 112);
        m.errorLocation = uint32(p >> 120);
        m.literalBase = uint16(p >> 152);
        m.literalCount = uint16(p >> 168);
        if (m.declaredIndex != index || m.errorDomain > 2) revert S2aControlError(2);
        if (m.errorDomain == 0) {
            bool visibility = (m.access & 0x0001) != 0 && (m.access & 0x0006) == 0;
            if (!visibility || (m.access & 0x0008) == 0 || (m.access & 0x0520) != 0
                || (m.access & ~uint16(0x1dff)) != 0 || m.errorCode != 0
                || m.errorLocation != 0 || m.codeLength == 0
                || m.codeLength > 256 || m.maxStack > 8 || m.maxLocals > 8
                || m.argc > 4 || m.maxLocals < m.argc
                || uint256(m.codeOffset) + m.codeLength > c.rawLength
                || uint256(m.literalBase) + m.literalCount > c.literalCount
                || (m.codeLength < 256 && (m.starts >> m.codeLength) != 0)
                || (m.starts & 1) == 0) revert S2aControlError(2);
        } else {
            if (m.errorCode == 0 || m.codeOffset != 0 || m.codeLength != 0
                || m.maxStack != 0 || m.maxLocals != 0 || m.argc != 0
                || m.literalBase != 0 || m.literalCount != 0 || m.starts != 0) {
                revert S2aControlError(2);
            }
            bool bytecodeError = m.errorCode == 2 || m.errorCode == 3 || m.errorCode == 5
                || m.errorCode == 6 || m.errorCode == 7 || m.errorCode == 8
                || m.errorCode == 9 || m.errorCode == 11 || m.errorCode == 12
                || m.errorCode == 14 || m.errorCode == 15 || m.errorCode == 16;
            if ((m.errorDomain == 1 && (m.errorCode < 3 || m.errorCode > 6
                    || m.errorLocation != index))
                || (m.errorDomain == 2 && !bytecodeError)) revert S2aControlError(2);
        }
    }

    function word(bytes memory runtime, uint256 payloadWord) internal pure returns (bytes32 out) {
        // runtime[0] is STOP, then payload words are naturally unaligned by one.
        uint256 offset = 1 + payloadWord * 32;
        assembly ("memory-safe") { out := mload(add(add(runtime, 0x20), offset)) }
    }

    function recordWord(bytes memory record, uint256 index) private pure returns (bytes32 out) {
        assembly ("memory-safe") { out := mload(add(add(record, 0x20), mul(index, 0x20))) }
    }

    function programId(bytes32 classId, MethodView memory m, bytes32 moduleCodeHash)
        internal pure returns (bytes32)
    {
        return keccak256(abi.encode(
            DPROGRAM, uint32(3), classId, m.declaredIndex,
            m.nameHash, m.descriptorHash, moduleCodeHash
        ));
    }

    function inputRoot(bytes32 program, bytes32 argsHash, uint64 maxTotalSteps)
        internal pure returns (bytes32)
    {
        return keccak256(abi.encode(DINPUT, program, argsHash, maxTotalSteps));
    }
}
