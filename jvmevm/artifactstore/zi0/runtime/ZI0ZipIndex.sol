// SPDX-License-Identifier: MIT
pragma solidity 0.8.30;

error ZI0Error(uint256 code);

interface IAS0ZI0 {
    function read(uint32 offset, uint32 length) external view returns (bytes memory);
    function isSealed() external view returns (bool);
    function contentCommitment() external view returns (bytes32);
    function declaredLength() external view returns (uint32);
}

/// A bounded EVM-derived index over one sealed MC-AS0 ZIP byte artifact.
/// Names and compressed ranges remain opaque; this contract does not inflate or
/// verify plaintext CRCs and has no host catalogue/import path.
contract ZI0ZipIndex {
    bytes32 private constant AS0_CODEHASH =
        hex"c8cec283e80fd82b15254bd50a9f2aea3a91305ba71f756f834439280600f896";
    uint32 private constant MAX_LENGTH = 33554432;
    uint32 private constant MAX_ENTRIES = 32768;
    uint32 private constant MAX_CD = 4194304;
    uint16 private constant MAX_NAME = 256;
    uint16 private constant MAX_EXTRA = 1024;
    uint16 private constant MAX_COMMENT = 1024;
    bytes32 private constant INDEX_DOMAIN = keccak256("MC-ZI0/index/v1");
    bytes32 private constant ENTRY_DOMAIN = keccak256("MC-ZI0/entry/v1");

    // All instance identity fields are constructor-written storage, deliberately
    // not immutables, so deployed runtime code is identical for every binding.
    address public owner;
    address public store;
    bytes32 public content;
    uint32 public length;

    // 0 BOUND, 1 STAGING, 2 FINAL.
    uint8 public phase;
    uint32 public eocd;
    uint32 public cdOffset;
    uint32 public cdSize;
    uint32 public count;
    uint32 public nextEntry;
    uint32 public cdCursor;
    bytes32 public rolling;
    bytes32 public finalRoot;

    uint32 private previousLocal;
    uint32 private previousEnd;
    mapping(uint32 index => uint256 packedRecord) private records;
    mapping(bytes32 nameHash => uint32 indexPlusOne) private nameIndex;

    constructor(address sealedAS0, bytes32 assertedContent) {
        // This check is intentionally first, before code or dependency calls.
        if (msg.sender == address(0)) revert ZI0Error(1);

        owner = msg.sender;
        store = sealedAS0;
        content = assertedContent;

        _codeBinding();
        IAS0ZI0 artifact = IAS0ZI0(sealedAS0);
        uint32 actualLength = artifact.declaredLength();
        if (
            assertedContent == bytes32(0) ||
            !artifact.isSealed() ||
            artifact.contentCommitment() != assertedContent ||
            actualLength == 0 ||
            actualLength > MAX_LENGTH
        ) revert ZI0Error(3);
        length = actualLength;
    }

    function _codeBinding() private view {
        bytes32 actual;
        address target = store;
        assembly ("memory-safe") {
            actual := extcodehash(target)
        }
        if (actual != AS0_CODEHASH) revert ZI0Error(2);
    }

    function _binding() private view {
        _codeBinding();
        IAS0ZI0 artifact = IAS0ZI0(store);
        if (
            content == bytes32(0) ||
            !artifact.isSealed() ||
            artifact.contentCommitment() != content ||
            artifact.declaredLength() != length ||
            length == 0 ||
            length > MAX_LENGTH
        ) revert ZI0Error(3);
    }

    function _u16(bytes memory raw, uint256 at) private pure returns (uint16) {
        return uint16(uint8(raw[at])) | (uint16(uint8(raw[at + 1])) << 8);
    }

    function _u32(bytes memory raw, uint256 at) private pure returns (uint32) {
        return uint32(_u16(raw, at)) | (uint32(_u16(raw, at + 2)) << 16);
    }

    function _part(uint32 at, uint32 size) private view returns (bytes memory out) {
        if (size > 4096 || uint256(at) + size > length) revert ZI0Error(16);
        out = IAS0ZI0(store).read(at, size);
        if (out.length != size) revert ZI0Error(3);
    }

    function _equal(bytes memory left, bytes memory right) private pure returns (bool) {
        if (left.length != right.length) return false;
        for (uint256 i; i < left.length; ++i) {
            if (left[i] != right[i]) return false;
        }
        return true;
    }

    function _extraOK(bytes memory raw, uint256 start, uint256 size) private pure returns (bool) {
        uint256 cursor = start;
        uint256 end = start + size;
        while (cursor < end) {
            if (cursor + 4 > end) return false;
            uint16 id = _u16(raw, cursor);
            uint16 fieldSize = _u16(raw, cursor + 2);
            if (id == 1 || cursor + 4 + fieldSize > end) return false;
            cursor += 4 + fieldSize;
        }
        return cursor == end;
    }

    function discover() external {
        if (msg.sender != owner) revert ZI0Error(1);
        if (phase != 0) revert ZI0Error(4);
        _binding();

        uint32 archiveSize = length;
        if (archiveSize < 22) revert ZI0Error(5);
        uint32 tailSize = archiveSize > 65557 ? 65557 : archiveSize;
        bytes memory tail = new bytes(tailSize);
        uint32 copied;
        while (copied < tailSize) {
            uint32 take = tailSize - copied;
            if (take > 4096) take = 4096;
            bytes memory fragment = _part(archiveSize - tailSize + copied, take);
            for (uint256 j; j < take; ++j) tail[copied + j] = fragment[j];
            copied += take;
        }

        uint256 candidates;
        uint256 candidateAt;
        for (uint256 p; p + 22 <= tailSize; ++p) {
            if (
                _u32(tail, p) == 0x06054b50 &&
                uint256(archiveSize - tailSize) + p + 22 + _u16(tail, p + 20) == archiveSize
            ) {
                uint16 disk = _u16(tail, p + 4);
                uint16 centralDisk = _u16(tail, p + 6);
                uint16 diskEntries = _u16(tail, p + 8);
                uint16 totalEntries = _u16(tail, p + 10);
                uint32 centralSize = _u32(tail, p + 12);
                uint32 centralOffset = _u32(tail, p + 16);
                if (
                    disk == 0 &&
                    centralDisk == 0 &&
                    diskEntries == totalEntries &&
                    uint256(centralOffset) + centralSize == uint256(archiveSize - tailSize) + p
                ) {
                    ++candidates;
                    candidateAt = p;
                }
            }
        }
        if (candidates != 1) revert ZI0Error(6);

        uint32 foundEOCD = uint32(uint256(archiveSize - tailSize) + candidateAt);
        uint32 foundOffset = _u32(tail, candidateAt + 16);
        uint32 foundSize = _u32(tail, candidateAt + 12);
        uint32 foundCount = _u16(tail, candidateAt + 10);
        if (
            foundCount > MAX_ENTRIES ||
            foundSize > MAX_CD ||
            (foundCount == 0) != (foundSize == 0) ||
            uint256(foundOffset) + foundSize != foundEOCD
        ) revert ZI0Error(7);

        // The only prefix signature inspected by policy is an empty archive's
        // exact ZIP64-locator prelude position. Opaque payload/name bytes are not
        // searched for ZIP64 markers.
        if (foundCount == 0 && foundEOCD >= 20) {
            bytes memory locator = _part(foundEOCD - 20, 4);
            if (_u32(locator, 0) == 0x07064b50) revert ZI0Error(9);
        }

        eocd = foundEOCD;
        cdOffset = foundOffset;
        cdSize = foundSize;
        count = foundCount;
        cdCursor = foundOffset;
        rolling = keccak256(
            abi.encode(
                INDEX_DOMAIN,
                address(this),
                owner,
                store,
                AS0_CODEHASH,
                content,
                length,
                foundEOCD,
                foundOffset,
                foundSize,
                foundCount
            )
        );
        phase = 1;
    }

    function _name(uint256 packed) private view returns (bytes memory) {
        uint32 at = uint32(packed & 0x1ffffff);
        uint16 nameLength = uint16((packed >> 164) & 0x1ff);
        return _part(at, nameLength);
    }

    function scan(
        uint32 expectedEntry,
        uint32 expectedCursor,
        bytes32 expectedRolling,
        uint16 units
    ) external {
        if (msg.sender != owner) revert ZI0Error(1);
        if (phase != 1) revert ZI0Error(4);
        _binding();
        if (
            expectedEntry != nextEntry ||
            expectedCursor != cdCursor ||
            expectedRolling != rolling
        ) revert ZI0Error(10);
        // Correctly-CASed scans must still perform bounded positive work.
        if (units == 0 || units > 64 || nextEntry >= count) revert ZI0Error(11);

        uint32 stop = nextEntry + units;
        if (stop > count) stop = count;
        uint32 cursor = cdCursor;
        uint32 priorLocal = previousLocal;
        uint32 priorEnd = previousEnd;
        bytes32 root = rolling;
        uint32 centralEnd = cdOffset + cdSize;

        for (uint32 index = nextEntry; index < stop; ++index) {
            if (uint256(cursor) + 46 > centralEnd) revert ZI0Error(16);
            bytes memory header = _part(cursor, 46);
            if (_u32(header, 0) != 0x02014b50) revert ZI0Error(12);

            uint16 flags = _u16(header, 8);
            uint16 method = _u16(header, 10);
            uint32 crc = _u32(header, 16);
            uint32 compressed = _u32(header, 20);
            uint32 plain = _u32(header, 24);
            uint16 nameLength = _u16(header, 28);
            uint16 extraLength = _u16(header, 30);
            uint16 commentLength = _u16(header, 32);
            uint16 disk = _u16(header, 34);
            uint32 local = _u32(header, 42);

            if (
                nameLength == 0 ||
                nameLength > MAX_NAME ||
                extraLength > MAX_EXTRA ||
                commentLength > MAX_COMMENT
            ) revert ZI0Error(13);
            if (
                (flags & 0xf7f1) != 0 ||
                (method == 0 && (flags & 6) != 0) ||
                disk != 0 ||
                compressed == type(uint32).max ||
                plain == type(uint32).max ||
                local == type(uint32).max
            ) revert ZI0Error(14);
            if ((method != 0 && method != 8) || (method == 0 && compressed != plain)) {
                revert ZI0Error(15);
            }

            uint32 centralLength = uint32(46 + nameLength + extraLength + commentLength);
            if (uint256(cursor) + centralLength > centralEnd) revert ZI0Error(16);
            bytes memory central = _part(cursor, centralLength);
            if (!_extraOK(central, 46 + nameLength, extraLength)) revert ZI0Error(17);

            bytes memory rawName = new bytes(nameLength);
            for (uint256 j; j < nameLength; ++j) rawName[j] = central[46 + j];
            bytes32 nameHash = keccak256(rawName);
            uint32 occupied = nameIndex[nameHash];
            if (occupied != 0) {
                bytes memory oldName = _name(records[occupied - 1]);
                if (_equal(oldName, rawName)) revert ZI0Error(18);
                revert ZI0Error(19);
            }

            if (uint256(local) + 30 > cdOffset) revert ZI0Error(20);
            bytes memory localHeader = _part(local, 30);
            if (
                _u32(localHeader, 0) != 0x04034b50 ||
                _u16(localHeader, 6) != flags ||
                _u16(localHeader, 8) != method
            ) revert ZI0Error(20);
            uint16 localNameLength = _u16(localHeader, 26);
            uint16 localExtraLength = _u16(localHeader, 28);
            if (localNameLength != nameLength || localExtraLength > MAX_EXTRA) {
                revert ZI0Error(21);
            }

            uint32 localFraming = uint32(30 + localNameLength + localExtraLength);
            if (uint256(local) + localFraming > cdOffset) revert ZI0Error(21);
            bytes memory localRecord = _part(local, localFraming);
            if (!_extraOK(localRecord, 30 + localNameLength, localExtraLength)) {
                revert ZI0Error(22);
            }
            bytes memory localName = new bytes(localNameLength);
            for (uint256 j; j < localNameLength; ++j) localName[j] = localRecord[30 + j];
            if (!_equal(rawName, localName)) revert ZI0Error(22);

            uint32 dataStart = local + localFraming;
            uint256 dataEndWide = uint256(dataStart) + compressed;
            if (dataEndWide > cdOffset) revert ZI0Error(23);
            uint32 dataEnd = uint32(dataEndWide);
            uint32 recordEnd = dataEnd;
            uint8 descriptor;

            if ((flags & 8) == 0) {
                if (
                    _u32(localHeader, 14) != crc ||
                    _u32(localHeader, 18) != compressed ||
                    _u32(localHeader, 22) != plain
                ) revert ZI0Error(24);
            } else {
                if (
                    _u32(localHeader, 14) != 0 ||
                    _u32(localHeader, 18) != 0 ||
                    _u32(localHeader, 22) != 0
                ) revert ZI0Error(24);

                uint32 beforeCentral = cdOffset - dataEnd;
                if (beforeCentral < 12) revert ZI0Error(26);
                uint32 descriptorRead = beforeCentral < 16 ? beforeCentral : 16;
                bytes memory encoded = _part(dataEnd, descriptorRead);
                if (
                    descriptorRead == 16 &&
                    _u32(encoded, 0) == 0x08074b50 &&
                    _u32(encoded, 4) == crc &&
                    _u32(encoded, 8) == compressed &&
                    _u32(encoded, 12) == plain
                ) {
                    recordEnd += 16;
                    descriptor = 2;
                } else if (
                    _u32(encoded, 0) == crc &&
                    _u32(encoded, 4) == compressed &&
                    _u32(encoded, 8) == plain
                ) {
                    recordEnd += 12;
                    descriptor = 1;
                } else {
                    revert ZI0Error(25);
                }
            }

            if (recordEnd > cdOffset) revert ZI0Error(26);
            if (index > 0 && (local <= priorLocal || local < priorEnd)) revert ZI0Error(27);
            priorLocal = local;
            priorEnd = recordEnd;

            uint32 namePosition = cursor + 46;
            if (
                namePosition >= MAX_LENGTH ||
                local >= MAX_LENGTH ||
                dataStart >= MAX_LENGTH ||
                compressed >= MAX_LENGTH
            ) revert ZI0Error(14);

            uint256 packed =
                uint256(namePosition) |
                (uint256(local) << 25) |
                (uint256(dataStart) << 50) |
                (uint256(compressed) << 75) |
                (uint256(plain) << 100) |
                (uint256(crc) << 132) |
                (uint256(nameLength) << 164) |
                (uint256(flags) << 173) |
                (uint256(method) << 189) |
                (uint256(descriptor) << 193);
            records[index] = packed;
            nameIndex[nameHash] = index + 1;

            uint32 centralRecordEnd = cursor + centralLength;
            root = keccak256(
                abi.encode(
                    ENTRY_DOMAIN,
                    root,
                    index,
                    nameHash,
                    nameLength,
                    flags,
                    method,
                    crc,
                    compressed,
                    plain,
                    local,
                    dataStart,
                    dataEnd,
                    recordEnd,
                    centralRecordEnd
                )
            );
            cursor = centralRecordEnd;
        }

        nextEntry = stop;
        cdCursor = cursor;
        previousLocal = priorLocal;
        previousEnd = priorEnd;
        rolling = root;
    }

    function finish(
        uint32 expectedCount,
        uint32 expectedCursor,
        bytes32 expectedRolling
    ) external {
        if (msg.sender != owner) revert ZI0Error(1);
        if (phase != 1) revert ZI0Error(4);
        _binding();
        if (
            expectedCount != count ||
            nextEntry != count ||
            expectedCursor != cdCursor ||
            cdCursor != cdOffset + cdSize ||
            expectedRolling != rolling
        ) revert ZI0Error(29);
        finalRoot = rolling;
        phase = 2;
    }

    function entry(uint32 index) external view returns (bytes memory rawName, bytes32 packedRecord) {
        _binding();
        if (phase != 2) revert ZI0Error(30);
        if (index >= count) revert ZI0Error(31);
        uint256 packed = records[index];
        return (_name(packed), bytes32(packed));
    }

    function lookup(bytes calldata rawName)
        external
        view
        returns (bool found, uint32 index, bytes32 packedRecord)
    {
        _binding();
        if (phase != 2) revert ZI0Error(30);
        if (rawName.length == 0 || rawName.length > MAX_NAME) revert ZI0Error(32);
        uint32 bucket = nameIndex[keccak256(rawName)];
        if (bucket == 0) return (false, 0, bytes32(0));
        uint256 packed = records[bucket - 1];
        if (!_equal(_name(packed), rawName)) revert ZI0Error(19);
        return (true, bucket - 1, bytes32(packed));
    }
}
