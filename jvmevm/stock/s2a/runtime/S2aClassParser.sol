// SPDX-License-Identifier: MIT
pragma solidity 0.8.30;

import {
    StockPageError, S2aClassError
} from "./S2aTypes.sol";
import {S2aMetadataPage} from "./S2aMetadataPage.sol";

/// EVM classfile parser and append-only factory for immutable schema-3 metadata.
contract S2aClassParser {
    bytes32 private constant METADATA_MAGIC = keccak256("JVMEVM:S2A:METADATA:3");
    bytes32 private constant DCLASS = keccak256("JVMEVM:S2A:CLASS");

    struct Record { address metadataPage; bytes32 metadataHash; }
    mapping(bytes32 => Record) private records;
    mapping(bytes32 => bytes32) private registrations;

    event ClassRegistered(
        bytes32 indexed classId,
        address indexed rawPage,
        address metadataPage,
        bytes32 metadataHash,
        uint16 declaredMethods
    );

    struct CP {
        uint8[] tags;
        uint32[] offsets;
        uint16[] utfLengths;
    }

    struct MethodRecord {
        bytes32 nameHash;
        bytes32 descriptorHash;
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

    struct CodeInfo {
        bool valid;
        uint32 codeOffset;
        uint16 codeLength;
        uint8 maxStack;
        uint8 maxLocals;
    }

    struct Analysis {
        uint8 errorCode;
        uint32 errorPC;
        uint256 starts;
        uint16 literalCount;
        uint16[] literalPC;
        uint32[] literalBits;
    }

    function classRecord(bytes32 classId) external view returns (address metadataPage, bytes32 metadataHash) {
        Record storage r = records[classId];
        return (r.metadataPage, r.metadataHash);
    }

    function registerClass(address page, bytes32 expectedPageHash, bytes32 expectedPayloadHash)
        external returns (bytes32 classId, address metadataPage, bytes32 metadataHash, uint16 declaredMethods)
    {
        bytes memory raw = _page(page, expectedPageHash, expectedPayloadHash);
        bytes32 registrationKey = keccak256(abi.encode(page, expectedPageHash, expectedPayloadHash));
        classId = registrations[registrationKey];
        if (classId != bytes32(0)) {
            Record storage old = records[classId];
            if (old.metadataPage == address(0) || old.metadataHash == bytes32(0)) {
                revert S2aClassError(6, 0);
            }
            metadataPage = old.metadataPage;
            metadataHash = old.metadataHash;
            declaredMethods = _metadataMethodCount(metadataPage, metadataHash);
            return (classId, metadataPage, metadataHash, declaredMethods);
        }

        bytes memory payload;
        (payload, declaredMethods) = _parse(raw, page, expectedPageHash, expectedPayloadHash);
        try new S2aMetadataPage(payload) returns (S2aMetadataPage created) {
            metadataPage = address(created);
        } catch {
            revert S2aClassError(6, 0);
        }
        assembly ("memory-safe") { metadataHash := extcodehash(metadataPage) }
        if (metadataHash == bytes32(0)) revert S2aClassError(6, 0);
        bytes32 parserCodeHash;
        assembly ("memory-safe") { parserCodeHash := extcodehash(address()) }
        classId = keccak256(abi.encode(
            DCLASS, uint32(3), parserCodeHash, page, expectedPageHash,
            expectedPayloadHash, metadataHash
        ));
        Record storage existing = records[classId];
        if (classId == bytes32(0) || existing.metadataPage != address(0) || existing.metadataHash != bytes32(0)) {
            revert S2aClassError(6, 0);
        }
        records[classId] = Record(metadataPage, metadataHash);
        registrations[registrationKey] = classId;
        emit ClassRegistered(classId, page, metadataPage, metadataHash, declaredMethods);
    }

    function _parse(bytes memory d, address page, bytes32 pageHash, bytes32 payloadHash)
        private pure returns (bytes memory metadata, uint16 methodCount)
    {
        uint256 n = d.length;
        _need(n, 0, 10, n);
        if (_u4(d, 0) != 0xcafebabe || _u2(d, 4) != 0 || _u2(d, 6) != 52) {
            revert S2aClassError(2, _u4(d, 0) != 0xcafebabe ? 0 : 4);
        }
        uint16 cpCount = _u2(d, 8);
        if (cpCount < 1 || cpCount > 512) revert S2aClassError(3, 8);
        CP memory cp;
        cp.tags = new uint8[](cpCount);
        cp.offsets = new uint32[](cpCount);
        cp.utfLengths = new uint16[](cpCount);
        uint256 pos = 10;
        for (uint256 i = 1; i < cpCount; ++i) {
            _need(n, pos, 1, n);
            uint8 tag = uint8(d[pos]);
            cp.tags[i] = tag;
            cp.offsets[i] = uint32(pos);
            unchecked { ++pos; }
            if (tag == 1) {
                _need(n, pos, 2, n);
                uint16 len = _u2(d, pos);
                cp.utfLengths[i] = len;
                pos += 2;
                _need(n, pos, len, n);
                pos += len;
            } else if (tag == 3 || tag == 4) {
                _need(n, pos, 4, n); pos += 4;
            } else if (tag == 5 || tag == 6) {
                if (i + 1 >= cpCount) revert S2aClassError(3, cp.offsets[i]);
                _need(n, pos, 8, n); pos += 8; unchecked { ++i; }
            } else if (tag == 7 || tag == 8 || tag == 16) {
                _need(n, pos, 2, n); pos += 2;
            } else if (tag == 9 || tag == 10 || tag == 11 || tag == 12 || tag == 18) {
                _need(n, pos, 4, n); pos += 4;
            } else if (tag == 15) {
                _need(n, pos, 3, n); pos += 3;
            } else {
                revert S2aClassError(3, cp.offsets[i]);
            }
        }
        _validateCP(d, cp);

        _need(n, pos, 8, n);
        uint16 classAccess = _u2(d, pos);
        uint16 thisIndex = _u2(d, pos + 2);
        uint16 superIndex = _u2(d, pos + 4);
        uint16 interfaceCount = _u2(d, pos + 6);
        if ((classAccess & 0x0001) == 0 || (classAccess & ~uint16(0x0431)) != 0
            || (classAccess & 0x0410) == 0x0410 || interfaceCount != 0) {
            revert S2aClassError(4, pos);
        }
        bytes32 classNameHash = _className(d, cp, thisIndex, false, pos + 2);
        _className(d, cp, superIndex, true, pos + 4);
        pos += 8;
        _need(n, pos, uint256(interfaceCount) * 2 + 2, n);
        pos += uint256(interfaceCount) * 2;
        uint16 fieldCount = _u2(d, pos); pos += 2;
        if (fieldCount != 0) revert S2aClassError(4, pos - 2);

        _need(n, pos, 2, n);
        uint256 methodCountOffset = pos;
        methodCount = _u2(d, pos); pos += 2;
        if (methodCount > 32) revert S2aClassError(5, methodCountOffset);
        MethodRecord[] memory methods = new MethodRecord[](methodCount);
        uint16[] memory literalMethods = new uint16[](256);
        uint16[] memory literalPCs = new uint16[](256);
        uint32[] memory literalBits = new uint32[](256);
        uint16 totalLiterals;

        for (uint16 m; m < methodCount; ++m) {
            _need(n, pos, 8, n);
            uint16 methodAccess = _u2(d, pos);
            uint16 nameIndex = _u2(d, pos + 2);
            uint16 descriptorIndex = _u2(d, pos + 4);
            uint16 attrCount = _u2(d, pos + 6);
            _utfIndex(cp, nameIndex, pos + 2);
            _utfIndex(cp, descriptorIndex, pos + 4);
            MethodRecord memory r;
            r.nameHash = _utfHash(d, cp, nameIndex);
            r.descriptorHash = _utfHash(d, cp, descriptorIndex);
            r.access = methodAccess;
            bool clinit = _utfEq(d, cp, nameIndex, bytes("<clinit>"));
            bool reserved = _utfEq(d, cp, nameIndex, bytes("<init>"));
            if (clinit) revert S2aClassError(4, pos);
            pos += 8;

            uint256 codeCount;
            CodeInfo memory code;
            for (uint256 a; a < attrCount; ++a) {
                _need(n, pos, 6, n);
                uint16 attrName = _u2(d, pos);
                _utfIndex(cp, attrName, pos);
                uint32 attrLen = _u4(d, pos + 2);
                pos += 6;
                _need(n, pos, attrLen, n);
                if (_utfEq(d, cp, attrName, bytes("Code"))) {
                    ++codeCount;
                    if (codeCount == 1) code = _readCode(d, pos, attrLen, cp);
                }
                pos += attrLen;
            }

            (bool descriptorOK, uint8 argc) = _descriptor(d, cp, descriptorIndex);
            bool visibility = (methodAccess & 0x0001) != 0 && (methodAccess & 0x0006) == 0;
            bool accessOK = visibility && (methodAccess & 0x0008) != 0
                && (methodAccess & 0x0520) == 0 && (methodAccess & ~uint16(0x1dff)) == 0;
            if (reserved) {
                r = _methodError(r, 6, m);
            } else if (!accessOK) {
                r = _methodError(r, 3, m);
            } else if (!descriptorOK) {
                r = _methodError(r, 4, m);
            } else if (codeCount != 1 || !code.valid || code.maxLocals < argc) {
                r = _methodError(r, 5, m);
            } else {
                Analysis memory a = _analyze(d, code, cp, argc);
                if (a.errorCode != 0) {
                    r.errorDomain = 2;
                    r.errorCode = a.errorCode;
                    r.errorLocation = a.errorPC;
                } else {
                    if (uint256(totalLiterals) + a.literalCount > 256) revert S2aClassError(5, 0);
                    r.codeOffset = code.codeOffset;
                    r.codeLength = code.codeLength;
                    r.maxStack = code.maxStack;
                    r.maxLocals = code.maxLocals;
                    r.argc = argc;
                    r.literalBase = totalLiterals;
                    r.literalCount = a.literalCount;
                    r.starts = a.starts;
                    for (uint16 j; j < a.literalCount; ++j) {
                        uint16 at = totalLiterals + j;
                        literalMethods[at] = m;
                        literalPCs[at] = a.literalPC[j];
                        literalBits[at] = a.literalBits[j];
                    }
                    totalLiterals += a.literalCount;
                }
            }
            methods[m] = r;
        }

        _need(n, pos, 2, n);
        uint16 classAttrs = _u2(d, pos); pos += 2;
        for (uint256 a; a < classAttrs; ++a) {
            _need(n, pos, 6, n);
            uint16 attrName = _u2(d, pos);
            _utfIndex(cp, attrName, pos);
            uint32 attrLen = _u4(d, pos + 2);
            pos += 6;
            _need(n, pos, attrLen, n);
            pos += attrLen;
        }
        if (pos != n) revert S2aClassError(1, pos);

        metadata = new bytes(192 + uint256(methodCount) * 128 + uint256(totalLiterals) * 8);
        _putWord(metadata, 0, METADATA_MAGIC);
        _putWord(metadata, 1, bytes32(uint256(uint160(page)) | (uint256(classAccess) << 160)));
        _putWord(metadata, 2, pageHash);
        _putWord(metadata, 3, payloadHash);
        _putWord(metadata, 4, classNameHash);
        _putWord(metadata, 5, bytes32(
            uint256(uint32(n)) | (uint256(cpCount) << 32) | (uint256(methodCount) << 48)
                | (uint256(totalLiterals) << 64)
        ));
        for (uint16 m; m < methodCount; ++m) {
            MethodRecord memory r = methods[m];
            uint256 base = 6 + uint256(m) * 4;
            _putWord(metadata, base, r.nameHash);
            _putWord(metadata, base + 1, r.descriptorHash);
            uint256 packed = uint256(m) | (uint256(r.access) << 16)
                | (uint256(r.codeOffset) << 32) | (uint256(r.codeLength) << 64)
                | (uint256(r.maxStack) << 80) | (uint256(r.maxLocals) << 88)
                | (uint256(r.argc) << 96) | (uint256(r.errorDomain) << 104)
                | (uint256(r.errorCode) << 112) | (uint256(r.errorLocation) << 120)
                | (uint256(r.literalBase) << 152) | (uint256(r.literalCount) << 168);
            _putWord(metadata, base + 2, bytes32(packed));
            _putWord(metadata, base + 3, bytes32(r.starts));
        }
        uint256 literalOffset = 192 + uint256(methodCount) * 128;
        for (uint16 i; i < totalLiterals; ++i) {
            _putU2(metadata, literalOffset, literalMethods[i]);
            _putU2(metadata, literalOffset + 2, literalPCs[i]);
            _putU4(metadata, literalOffset + 4, literalBits[i]);
            literalOffset += 8;
        }
    }

    function _readCode(bytes memory d, uint256 body, uint256 len, CP memory cp)
        private pure returns (CodeInfo memory out)
    {
        uint256 end = body + len;
        if (len < 12) return out;
        uint16 maxStack = _u2(d, body);
        uint16 maxLocals = _u2(d, body + 2);
        uint32 codeLen = _u4(d, body + 4);
        if (maxStack > 8 || maxLocals > 8 || codeLen == 0 || codeLen > 256) return out;
        uint256 codeOffset = body + 8;
        if (!_fits(codeOffset, codeLen, end)) return out;
        uint256 p = codeOffset + codeLen;
        if (!_fits(p, 2, end)) return out;
        uint16 handlers = _u2(d, p); p += 2;
        if (handlers != 0 || !_fits(p, uint256(handlers) * 8 + 2, end)) return out;
        p += uint256(handlers) * 8;
        uint16 attrs = _u2(d, p); p += 2;
        for (uint256 i; i < attrs; ++i) {
            if (!_fits(p, 6, end)) return out;
            uint16 name = _u2(d, p);
            if (!_isUtf(cp, name)) return out;
            uint32 nestedLen = _u4(d, p + 2);
            p += 6;
            if (!_fits(p, nestedLen, end)) return out;
            p += nestedLen;
        }
        if (p != end) return out;
        out.valid = true;
        out.codeOffset = uint32(codeOffset);
        out.codeLength = uint16(codeLen);
        out.maxStack = uint8(maxStack);
        out.maxLocals = uint8(maxLocals);
    }

    function _analyze(bytes memory d, CodeInfo memory code, CP memory cp, uint8 argc)
        private pure returns (Analysis memory a)
    {
        uint256 len = code.codeLength;
        a.literalPC = new uint16[](len);
        a.literalBits = new uint32[](len);
        uint256 pc;
        while (pc < len) {
            a.starts |= uint256(1) << pc;
            uint8 op = uint8(d[uint256(code.codeOffset) + pc]);
            uint256 width = _width(op);
            if (width == 0) return _analysisError(a, 6, pc);
            if (pc + width > len) return _analysisError(a, 2, pc);
            if (op == 0x12 || op == 0x13) {
                uint16 index = op == 0x12
                    ? uint16(uint8(d[uint256(code.codeOffset) + pc + 1]))
                    : _u2(d, uint256(code.codeOffset) + pc + 1);
                if (index == 0 || index >= cp.tags.length || cp.tags[index] != 3
                    || cp.offsets[index] == 0) return _analysisError(a, 6, pc);
                a.literalPC[a.literalCount] = uint16(pc);
                a.literalBits[a.literalCount] = _u4(d, uint256(cp.offsets[index]) + 1);
                ++a.literalCount;
            }
            if (op == 0x15 || op == 0x36 || op == 0x84) {
                if (uint8(d[uint256(code.codeOffset) + pc + 1]) >= code.maxLocals) {
                    return _analysisError(a, 8, pc);
                }
            } else if ((op >= 0x1a && op <= 0x1d) && op - 0x1a >= code.maxLocals) {
                return _analysisError(a, 8, pc);
            } else if ((op >= 0x3b && op <= 0x3e) && op - 0x3b >= code.maxLocals) {
                return _analysisError(a, 8, pc);
            }
            pc += width;
        }
        // Widths and operands are known before signed targets are interpreted.
        pc = 0;
        while (pc < len) {
            uint8 op = uint8(d[uint256(code.codeOffset) + pc]);
            if ((op >= 0x99 && op <= 0xa4) || op == 0xa7) {
                int256 target = int256(pc) + int256(int16(_u2(d, uint256(code.codeOffset) + pc + 1)));
                if (target < 0 || uint256(target) >= len
                    || (a.starts & (uint256(1) << uint256(target))) == 0) {
                    return _analysisError(a, 15, pc);
                }
            }
            uint256 width = _width(op);
            if (pc + width == len && op != 0xac && op != 0xa7) {
                return _analysisError(a, 7, pc);
            }
            pc += width;
        }
        return _verifyFlow(d, code, argc, a);
    }

    function _verifyFlow(bytes memory d, CodeInfo memory code, uint8 argc, Analysis memory a)
        private pure returns (Analysis memory)
    {
        uint256 len = code.codeLength;
        uint16[] memory heights = new uint16[](len);
        uint8[] memory initialized = new uint8[](len);
        for (uint256 i; i < len; ++i) heights[i] = type(uint16).max;
        // A PC is first enqueued once, then at most once for each of the
        // eight initialized bits removed by predecessor intersection.
        uint16[] memory queue = new uint16[](len * 9 + 1);
        heights[0] = 0;
        initialized[0] = argc == 0 ? 0 : uint8((uint16(1) << argc) - 1);
        queue[0] = 0;
        uint256 head;
        uint256 tail = 1;
        while (head < tail) {
            uint256 pc = queue[head++];
            uint16 h = heights[pc];
            uint8 init = initialized[pc];
            uint8 op = uint8(d[uint256(code.codeOffset) + pc]);
            uint256 width = _width(op);
            uint16 need;
            int16 delta;
            bool terminal;
            if (op == 0x00 || op == 0x84 || op == 0xa7) {
                delta = 0;
            } else if ((op >= 0x02 && op <= 0x08) || op == 0x10 || op == 0x11
                || op == 0x12 || op == 0x13 || op == 0x15 || (op >= 0x1a && op <= 0x1d)) {
                delta = 1;
            } else if (op == 0x36 || (op >= 0x3b && op <= 0x3e) || op == 0x74) {
                need = 1;
                if (op != 0x74) delta = -1;
            } else if (op == 0x60 || op == 0x64 || op == 0x68
                || op == 0x6c || op == 0x70 || op == 0x78 || op == 0x7a
                || op == 0x7c || op == 0x7e || op == 0x80 || op == 0x82) {
                need = 2; delta = -1;
            } else if (op == 0x91 || op == 0x92 || op == 0x93) {
                need = 1;
            } else if (op >= 0x99 && op <= 0x9e) {
                need = 1; delta = -1;
            } else if (op >= 0x9f && op <= 0xa4) {
                need = 2; delta = -2;
            } else if (op == 0xac) {
                if (h != 1) return _analysisError(a, 5, pc);
                terminal = true;
            }
            if (h < need) return _analysisError(a, 3, pc);
            uint16 nextHeight = uint16(int16(h) + delta);
            if (nextHeight > code.maxStack) return _analysisError(a, 9, pc);

            if (op == 0x15 || (op >= 0x1a && op <= 0x1d) || op == 0x84) {
                uint8 local = op == 0x15 || op == 0x84
                    ? uint8(d[uint256(code.codeOffset) + pc + 1]) : op - 0x1a;
                if ((init & (uint8(1) << local)) == 0) return _analysisError(a, 11, pc);
            } else if (op == 0x36 || (op >= 0x3b && op <= 0x3e)) {
                uint8 local = op == 0x36
                    ? uint8(d[uint256(code.codeOffset) + pc + 1]) : op - 0x3b;
                init |= uint8(1) << local;
            }
            if (terminal) continue;

            if (op == 0xa7) {
                uint16 target = uint16(uint256(int256(pc) + int256(int16(
                    _u2(d, uint256(code.codeOffset) + pc + 1)))));
                (tail, a) = _merge(target, nextHeight, init, heights, initialized, queue, tail, a);
            } else if (op >= 0x99 && op <= 0xa4) {
                uint16 target = uint16(uint256(int256(pc) + int256(int16(
                    _u2(d, uint256(code.codeOffset) + pc + 1)))));
                (tail, a) = _merge(target, nextHeight, init, heights, initialized, queue, tail, a);
                if (a.errorCode != 0) return a;
                if (pc + width >= len) return _analysisError(a, 7, pc);
                (tail, a) = _merge(uint16(pc + width), nextHeight, init, heights, initialized, queue, tail, a);
            } else {
                if (pc + width >= len) return _analysisError(a, 7, pc);
                (tail, a) = _merge(uint16(pc + width), nextHeight, init, heights, initialized, queue, tail, a);
            }
            if (a.errorCode != 0) return a;
        }
        return a;
    }

    function _merge(
        uint16 target, uint16 height, uint8 init,
        uint16[] memory heights, uint8[] memory initialized, uint16[] memory queue,
        uint256 tail, Analysis memory a
    ) private pure returns (uint256, Analysis memory) {
        if (heights[target] == type(uint16).max) {
            heights[target] = height;
            initialized[target] = init;
            if (tail >= queue.length) return (tail, _analysisError(a, 14, target));
            queue[tail++] = target;
        } else if (heights[target] != height) {
            return (tail, _analysisError(a, 5, target));
        } else {
            uint8 joined = initialized[target] & init;
            if (joined != initialized[target]) {
                initialized[target] = joined;
                if (tail >= queue.length) return (tail, _analysisError(a, 14, target));
                queue[tail++] = target;
            }
        }
        return (tail, a);
    }

    function _width(uint8 op) private pure returns (uint256) {
        if (op == 0x10 || op == 0x12 || op == 0x15 || op == 0x36) return 2;
        if (op == 0x11 || op == 0x13 || op == 0x84 || (op >= 0x99 && op <= 0xa4) || op == 0xa7) return 3;
        if (op == 0x00 || (op >= 0x02 && op <= 0x08)
            || (op >= 0x1a && op <= 0x1d) || (op >= 0x3b && op <= 0x3e)
            || op == 0x60 || op == 0x64 || op == 0x68 || op == 0x6c
            || op == 0x70 || op == 0x74 || op == 0x78 || op == 0x7a
            || op == 0x7c || op == 0x7e || op == 0x80 || op == 0x82
            || op == 0x91 || op == 0x92 || op == 0x93 || op == 0xac) return 1;
        return 0;
    }

    function _validateCP(bytes memory d, CP memory cp) private pure {
        for (uint16 i = 1; i < cp.tags.length; ++i) {
            uint8 tag = cp.tags[i];
            uint256 p = uint256(cp.offsets[i]) + 1;
            if (tag == 0) continue;
            if (tag == 7 || tag == 8 || tag == 16) {
                _requireTag(cp, _u2(d, p), 1, cp.offsets[i]);
            } else if (tag == 9 || tag == 10 || tag == 11) {
                _requireTag(cp, _u2(d, p), 7, cp.offsets[i]);
                _requireTag(cp, _u2(d, p + 2), 12, cp.offsets[i]);
            } else if (tag == 12) {
                _requireTag(cp, _u2(d, p), 1, cp.offsets[i]);
                _requireTag(cp, _u2(d, p + 2), 1, cp.offsets[i]);
            } else if (tag == 15) {
                uint8 kind = uint8(d[p]);
                uint16 ref = _u2(d, p + 1);
                if (kind < 1 || kind > 9 || ref == 0 || ref >= cp.tags.length) {
                    revert S2aClassError(3, cp.offsets[i]);
                }
                uint8 refTag = cp.tags[ref];
                bool validRef = kind <= 4 ? refTag == 9
                    : kind == 5 || kind == 8 ? refTag == 10
                    : kind == 9 ? refTag == 11
                    : refTag == 10 || refTag == 11;
                if (!validRef) revert S2aClassError(3, cp.offsets[i]);
            } else if (tag == 18) {
                _requireTag(cp, _u2(d, p + 2), 12, cp.offsets[i]);
            }
        }
    }

    function _className(bytes memory d, CP memory cp, uint16 index, bool mustObject, uint256 off)
        private pure returns (bytes32 nameHash)
    {
        if (index == 0 || index >= cp.tags.length || cp.tags[index] != 7) revert S2aClassError(3, off);
        uint16 name = _u2(d, uint256(cp.offsets[index]) + 1);
        _utfIndex(cp, name, off);
        uint256 start = uint256(cp.offsets[name]) + 3;
        uint256 len = cp.utfLengths[name];
        if (len == 0) revert S2aClassError(3, off);
        bool component;
        for (uint256 i; i < len; ++i) {
            uint8 c = uint8(d[start + i]);
            if (c == 0 || c >= 0x80 || c == 0x2e || c == 0x3b || c == 0x5b) revert S2aClassError(3, off);
            if (c == 0x2f) {
                if (!component || i + 1 == len) revert S2aClassError(3, off);
                component = false;
            } else component = true;
        }
        bool isObject = _utfEq(d, cp, name, bytes("java/lang/Object"));
        if ((mustObject && !isObject) || (!mustObject && isObject)) revert S2aClassError(4, off);
        nameHash = _utfHash(d, cp, name);
    }

    function _descriptor(bytes memory d, CP memory cp, uint16 index) private pure returns (bool, uint8 argc) {
        uint256 len = cp.utfLengths[index];
        if (len < 3 || len > 7) return (false, 0);
        uint256 p = uint256(cp.offsets[index]) + 3;
        if (d[p] != 0x28 || d[p + len - 2] != 0x29 || d[p + len - 1] != 0x49) return (false, 0);
        uint256 argsLen = len - 3;
        if (argsLen > 4) return (false, 0);
        for (uint256 i; i < argsLen; ++i) if (d[p + 1 + i] != 0x49) return (false, 0);
        return (true, uint8(argsLen));
    }

    function _methodError(MethodRecord memory r, uint8 code, uint16 index)
        private pure returns (MethodRecord memory)
    {
        r.errorDomain = 1;
        r.errorCode = code;
        r.errorLocation = index;
        return r;
    }

    function _analysisError(Analysis memory a, uint8 code, uint256 pc)
        private pure returns (Analysis memory)
    {
        a.errorCode = code;
        a.errorPC = uint32(pc);
        a.starts = 0;
        a.literalCount = 0;
        return a;
    }

    function _metadataMethodCount(address page, bytes32 expectedHash) private view returns (uint16 count) {
        uint256 size;
        bytes32 hash;
        bytes32 h5;
        assembly ("memory-safe") {
            size := extcodesize(page)
            hash := extcodehash(page)
            extcodecopy(page, 0, 161, 32)
            h5 := mload(0)
        }
        uint256 packed = uint256(h5);
        count = uint16(packed >> 48);
        uint16 literals = uint16(packed >> 64);
        if (size != 1 + 192 + uint256(count) * 128 + uint256(literals) * 8
            || size > 8192 || hash != expectedHash || packed >> 80 != 0) revert S2aClassError(6, 0);
    }

    function _page(address page, bytes32 expectedPageHash, bytes32 expectedPayloadHash)
        private view returns (bytes memory payload)
    {
        uint256 size;
        bytes32 actualHash;
        bytes32 first;
        assembly ("memory-safe") {
            size := extcodesize(page)
            actualHash := extcodehash(page)
            extcodecopy(page, 0, 0, 1)
            first := mload(0)
        }
        if (size < 2 || size > 4097) revert StockPageError(1);
        if (bytes1(first) != 0x00) revert StockPageError(2);
        if (actualHash != expectedPageHash) revert StockPageError(3);
        payload = new bytes(size - 1);
        assembly ("memory-safe") { extcodecopy(page, add(payload, 0x20), 1, sub(size, 1)) }
        if (keccak256(payload) != expectedPayloadHash) revert StockPageError(4);
    }

    function _utfIndex(CP memory cp, uint16 index, uint256 off) private pure {
        if (!_isUtf(cp, index)) revert S2aClassError(3, off);
    }
    function _isUtf(CP memory cp, uint16 index) private pure returns (bool) {
        return index != 0 && index < cp.tags.length && cp.tags[index] == 1;
    }
    function _requireTag(CP memory cp, uint16 index, uint8 tag, uint256 off) private pure {
        if (index == 0 || index >= cp.tags.length || cp.tags[index] != tag) revert S2aClassError(3, off);
    }
    function _utfEq(bytes memory d, CP memory cp, uint16 index, bytes memory value) private pure returns (bool) {
        if (cp.utfLengths[index] != value.length) return false;
        uint256 p = uint256(cp.offsets[index]) + 3;
        for (uint256 i; i < value.length; ++i) if (d[p + i] != value[i]) return false;
        return true;
    }
    function _utfHash(bytes memory d, CP memory cp, uint16 index) private pure returns (bytes32 out) {
        uint256 p = uint256(cp.offsets[index]) + 3;
        uint256 len = cp.utfLengths[index];
        assembly ("memory-safe") { out := keccak256(add(add(d, 0x20), p), len) }
    }
    function _need(uint256 actual, uint256 pos, uint256 amount, uint256 boundary) private pure {
        if (pos > boundary || amount > boundary - pos || boundary > actual) revert S2aClassError(1, pos);
    }
    function _fits(uint256 pos, uint256 amount, uint256 boundary) private pure returns (bool) {
        return pos <= boundary && amount <= boundary - pos;
    }
    function _u2(bytes memory d, uint256 p) private pure returns (uint16) {
        return (uint16(uint8(d[p])) << 8) | uint16(uint8(d[p + 1]));
    }
    function _u4(bytes memory d, uint256 p) private pure returns (uint32) {
        return (uint32(uint8(d[p])) << 24) | (uint32(uint8(d[p + 1])) << 16)
            | (uint32(uint8(d[p + 2])) << 8) | uint32(uint8(d[p + 3]));
    }
    function _putWord(bytes memory d, uint256 index, bytes32 value) private pure {
        assembly ("memory-safe") { mstore(add(add(d, 0x20), mul(index, 0x20)), value) }
    }
    function _putU2(bytes memory d, uint256 p, uint16 value) private pure {
        d[p] = bytes1(uint8(value >> 8)); d[p + 1] = bytes1(uint8(value));
    }
    function _putU4(bytes memory d, uint256 p, uint32 value) private pure {
        d[p] = bytes1(uint8(value >> 24)); d[p + 1] = bytes1(uint8(value >> 16));
        d[p + 2] = bytes1(uint8(value >> 8)); d[p + 3] = bytes1(uint8(value));
    }
}
