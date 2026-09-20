// SPDX-License-Identifier: GPL-3.0
pragma solidity 0.8.30;

/// @notice Fixed, constructor-bound generated-class package coordinator.
/// It reads class and one optional selected resource only through final DI0
/// decoders in the EVM. The resource becomes a read-only initial VFS file; this
/// contract is neither a ClassLoader nor a host resource catalogue.
contract MCEntryCoordinator {
    error MR0Error(uint256 code);

    struct SeedFile {
        bytes path;
        bytes data;
        bool readOnly;
    }

    address private constant ENGINE = address(bytes20(hex"4d432d52415734362d4259544533313138393846"));
    bytes32 private constant ENGINE_CODEHASH = hex"d2f1fa7362f7d8ee2cc038d76c543804066cf37c168dbd93aaa2d187262995a3";
    bytes32 private constant AS0_CODEHASH = hex"c8cec283e80fd82b15254bd50a9f2aea3a91305ba71f756f834439280600f896";
    bytes32 private constant ZI0_CODEHASH = hex"0c22eca78e00865ce03e8e298708bfe51ce9856cff138d1046905fc285ad5a77";
    bytes32 private constant DI0_CODEHASH = hex"946686a0a4f09ec9a03e3eb63e9bbeac008212061d6f316586034cf800380c37";
    bytes32 private constant PACKAGE_DOMAIN = keccak256("MC-RAW46-BYTE311898-P2/package/v1");
    bytes32 private constant CLASS_DOMAIN = keccak256("MC-RAW46-BYTE311898-P2/class/v1");
    bytes32 private constant SEED_DOMAIN = keccak256("MC-RAW46-BYTE311898-P2/selected-resource/v1");
    bytes32 private constant VM_DOMAIN = keccak256("MC-RAW46-BYTE311898-P2/vm/v1");
    uint32 private constant MAX_SELECTED_RESOURCE_BYTES = 4096;

    address public owner;
    address public finalIndex;
    bytes32 public finalIndexRoot;
    bytes32 public packageRoot;
    bytes32 public instanceId;
    uint32 public totalClassBytes;
    uint8 public classCount;

    address[46] private decoders;
    bytes32[46] private classRoots;
    uint32[46] private classSizes;
    bytes[46] private rawNames;

    // A scalar, rather than an array, makes one selected resource the complete
    // package surface. The all-zero tuple means no seed; no second resource can
    // be encoded by this ABI or stored state.
    address private seedDecoder;
    bytes private seedName;
    bytes32 private seedRoot;
    uint32 private seedSize;

    constructor(
        address fixedOwner,
        bytes32 fixedInstanceSalt,
        address[] memory fixedDecoders,
        bytes[] memory fixedRawNames,
        bytes32[] memory assertedIndexRoots,
        bytes32[] memory assertedClassRoots,
        address assertedSeedDecoder,
        bytes memory assertedSeedName,
        bytes32 assertedSeedIndexRoot,
        bytes32 assertedSeedRoot,
        bytes32 assertedPackageRoot
    ) {
        if (fixedOwner == address(0) || fixedOwner != msg.sender) revert MR0Error(1);
        uint256 n = fixedDecoders.length;
        if (
            n == 0 || n > 46 || fixedRawNames.length != n ||
            assertedIndexRoots.length != n || assertedClassRoots.length != n
        ) revert MR0Error(2);
        if (ENGINE.codehash != ENGINE_CODEHASH) revert MR0Error(3);

        owner = fixedOwner;
        classCount = uint8(n);
        address commonIndex;
        bytes32 commonIndexRoot;
        uint32 total;
        bytes32 rolling = keccak256(abi.encode(
            PACKAGE_DOMAIN, address(this), fixedOwner, ENGINE, ENGINE_CODEHASH,
            DI0_CODEHASH, ZI0_CODEHASH, uint8(n)
        ));
        for (uint256 i; i < n; ++i) {
            address decoder = fixedDecoders[i];
            if (decoder.codehash != DI0_CODEHASH) revert MR0Error(4);
            bytes memory name = fixedRawNames[i];
            bytes32 nameHash = keccak256(name);
            for (uint256 j; j < i; ++j) {
                if (fixedDecoders[j] == decoder || keccak256(fixedRawNames[j]) == nameHash) revert MR0Error(5);
            }
            if (!_validClassName(name)) revert MR0Error(6);
            if (_u8(decoder, bytes4(keccak256("phase()"))) != 4) revert MR0Error(7);
            if (_b32(decoder, bytes4(keccak256("nameHash()"))) != nameHash) revert MR0Error(8);

            bytes32 indexRoot = assertedIndexRoots[i];
            if (indexRoot == bytes32(0) || _b32(decoder, bytes4(keccak256("indexRoot()"))) != indexRoot) revert MR0Error(9);
            bytes32 resourceRoot = assertedClassRoots[i];
            if (resourceRoot == bytes32(0) || _b32(decoder, bytes4(keccak256("finalRoot()"))) != resourceRoot) revert MR0Error(10);
            uint32 size = _u32(decoder, bytes4(keccak256("plainSize()")));
            if (size == 0 || size > 311898) revert MR0Error(11);
            if (uint256(total) + size > 311898) revert MR0Error(12);
            total += size;

            address index = _address(decoder, bytes4(keccak256("index()")));
            if (i == 0) {
                commonIndex = index;
                commonIndexRoot = indexRoot;
            } else if (index != commonIndex || indexRoot != commonIndexRoot) {
                revert MR0Error(13);
            }
            if (_address(decoder, bytes4(keccak256("owner()"))) != fixedOwner) revert MR0Error(14);

            decoders[i] = decoder;
            rawNames[i] = name;
            classRoots[i] = resourceRoot;
            classSizes[i] = size;
            rolling = keccak256(abi.encode(
                CLASS_DOMAIN, rolling, uint8(i), decoder, nameHash,
                indexRoot, resourceRoot, size
            ));
        }
        if (
            commonIndex.codehash != ZI0_CODEHASH ||
            _u8(commonIndex, bytes4(keccak256("phase()"))) != 2 ||
            _b32(commonIndex, bytes4(keccak256("finalRoot()"))) != commonIndexRoot ||
            _address(commonIndex, bytes4(keccak256("owner()"))) != fixedOwner
        ) revert MR0Error(15);

        if (assertedSeedDecoder == address(0)) {
            if (assertedSeedName.length != 0 || assertedSeedIndexRoot != bytes32(0)
                || assertedSeedRoot != bytes32(0)) revert MR0Error(25);
        } else {
            if (!_validSeedName(assertedSeedName) || assertedSeedDecoder.codehash != DI0_CODEHASH) {
                revert MR0Error(25);
            }
            bytes32 nameHash = keccak256(assertedSeedName);
            if (_u8(assertedSeedDecoder, bytes4(keccak256("phase()"))) != 4
                || _b32(assertedSeedDecoder, bytes4(keccak256("nameHash()"))) != nameHash
                || _address(assertedSeedDecoder, bytes4(keccak256("owner()"))) != fixedOwner
                || _address(assertedSeedDecoder, bytes4(keccak256("index()"))) != commonIndex
                || assertedSeedIndexRoot != commonIndexRoot
                || _b32(assertedSeedDecoder, bytes4(keccak256("indexRoot()"))) != commonIndexRoot
                || assertedSeedRoot == bytes32(0)
                || _b32(assertedSeedDecoder, bytes4(keccak256("finalRoot()"))) != assertedSeedRoot) {
                revert MR0Error(26);
            }
            uint32 size = _u32(assertedSeedDecoder, bytes4(keccak256("plainSize()")));
            if (size == 0 || size > MAX_SELECTED_RESOURCE_BYTES) revert MR0Error(27);
            seedDecoder = assertedSeedDecoder;
            seedName = assertedSeedName;
            seedRoot = assertedSeedRoot;
            seedSize = size;
            rolling = keccak256(abi.encode(
                SEED_DOMAIN, rolling, assertedSeedDecoder, nameHash,
                commonIndexRoot, assertedSeedRoot, size
            ));
        }

        finalIndex = commonIndex;
        finalIndexRoot = commonIndexRoot;
        totalClassBytes = total;
        bytes32 root = keccak256(abi.encode(
            PACKAGE_DOMAIN, rolling, total, commonIndex, commonIndexRoot,
            uint8(assertedSeedDecoder == address(0) ? 0 : 1)
        ));
        if (root == bytes32(0) || root != assertedPackageRoot) revert MR0Error(16);
        packageRoot = root;
        instanceId = keccak256(abi.encode(VM_DOMAIN, address(this), root, fixedInstanceSalt));
    }

    modifier onlyOwner() {
        if (msg.sender != owner) revert MR0Error(17);
        _;
    }

    /// @notice The sole engine-only resource presence query. It accepts exactly
    /// the constructor-selected resource and asks its genuine common ZI0 index;
    /// classes and arbitrary ZIP entries are never a guest resource catalogue.
    function resourceExists(bytes calldata rawName) external view returns (bool found) {
        if (msg.sender != ENGINE || ENGINE.codehash != ENGINE_CODEHASH) revert MR0Error(22);
        if (!_validSeedName(rawName) || seedDecoder == address(0) || keccak256(rawName) != keccak256(seedName)) return false;
        _validateIndex();
        if (!_validSeedDecoder()) revert MR0Error(26);
        (bool ok, bytes memory returned) = finalIndex.staticcall(
            abi.encodeWithSignature("lookup(bytes)", rawName)
        );
        if (!ok || returned.length != 96) revert MR0Error(24);
        uint256 flag;
        assembly ("memory-safe") { flag := mload(add(returned, 32)) }
        if (flag != 1) revert MR0Error(24);
        return true;
    }

    function classBinding(uint8 at) external view returns (
        address decoder, bytes memory rawName, bytes32 resourceRoot, uint32 classSize
    ) {
        if (at >= classCount) revert MR0Error(19);
        return (decoders[at], rawNames[at], classRoots[at], classSizes[at]);
    }

    function selectedResource() external view returns (
        address decoder, bytes memory rawName, bytes32 resourceRoot, uint32 size
    ) {
        return (seedDecoder, seedName, seedRoot, seedSize);
    }

    /// @notice Fixed direct `main(String[])` selection; no host argument vector exists.
    function startMain(bytes32 assertedPackageRoot, uint8 entryAt, uint64 maxJvmSteps, uint32 maxInternalSteps)
        external onlyOwner returns (bytes memory engineReturn)
    {
        if (assertedPackageRoot != packageRoot) revert MR0Error(18);
        if (entryAt >= classCount) revert MR0Error(19);
        bytes[] memory classes = _loadAll();
        SeedFile[] memory seeds = _loadSelectedSeed();
        return _engineCall(abi.encodeWithSignature(
            "startMain(bytes32,bytes[],string,(bytes,bytes,bool)[],uint64,uint32)",
            instanceId, classes, _internalName(rawNames[entryAt]), seeds, maxJvmSteps, maxInternalSteps));
    }

    /// @notice Resumption never reloads seed bytes: it uses the checkpointed VFS.
    function resumeMain(bytes32 assertedPackageRoot, uint64 expectedEpoch, bytes32 expectedCheckpointRoot,
        bytes calldata checkpoint, uint64 maxJvmSteps, uint32 maxInternalSteps)
        external onlyOwner returns (bytes memory engineReturn)
    {
        if (assertedPackageRoot != packageRoot) revert MR0Error(18);
        bytes[] memory classes = _loadAll();
        return _engineCall(abi.encodeWithSignature(
            "resumeMain(bytes32,uint64,bytes32,bytes[],bytes,uint64,uint32)", instanceId,
            expectedEpoch, expectedCheckpointRoot, classes, checkpoint, maxJvmSteps, maxInternalSteps));
    }

    function _loadAll() private view returns (bytes[] memory classes) {
        if (ENGINE.codehash != ENGINE_CODEHASH) revert MR0Error(3);
        _validateIndex();
        uint256 n = classCount;
        classes = new bytes[](n);
        for (uint256 i; i < n; ++i) {
            address decoder = decoders[i];
            bytes memory name = rawNames[i];
            if (
                decoder.codehash != DI0_CODEHASH ||
                _u8(decoder, bytes4(keccak256("phase()"))) != 4 ||
                _b32(decoder, bytes4(keccak256("nameHash()"))) != keccak256(name) ||
                _b32(decoder, bytes4(keccak256("indexRoot()"))) != finalIndexRoot ||
                _b32(decoder, bytes4(keccak256("finalRoot()"))) != classRoots[i] ||
                _address(decoder, bytes4(keccak256("index()"))) != finalIndex ||
                _address(decoder, bytes4(keccak256("owner()"))) != owner ||
                _u32(decoder, bytes4(keccak256("plainSize()"))) != classSizes[i]
            ) revert MR0Error(20);
            classes[i] = _readExact(decoder, classSizes[i]);
        }
    }

    function _loadSelectedSeed() private view returns (SeedFile[] memory seeds) {
        if (seedDecoder == address(0)) return new SeedFile[](0);
        _validateIndex();
        if (!_validSeedDecoder()) revert MR0Error(26);
        seeds = new SeedFile[](1);
        seeds[0] = SeedFile(abi.encodePacked(bytes("/ro/"), seedName), _readExact(seedDecoder, seedSize), true);
    }

    function _validSeedDecoder() private view returns (bool) {
        return seedDecoder.codehash == DI0_CODEHASH
            && _u8(seedDecoder, bytes4(keccak256("phase()"))) == 4
            && _b32(seedDecoder, bytes4(keccak256("nameHash()"))) == keccak256(seedName)
            && _b32(seedDecoder, bytes4(keccak256("indexRoot()"))) == finalIndexRoot
            && _b32(seedDecoder, bytes4(keccak256("finalRoot()"))) == seedRoot
            && _address(seedDecoder, bytes4(keccak256("index()"))) == finalIndex
            && _address(seedDecoder, bytes4(keccak256("owner()"))) == owner
            && _u32(seedDecoder, bytes4(keccak256("plainSize()"))) == seedSize;
    }

    function _readExact(address decoder, uint32 size) private view returns (bytes memory out) {
        out = new bytes(size);
        for (uint32 offset; offset < size;) {
            uint32 length = size - offset;
            if (length > 4096) length = 4096;
            (bool ok, bytes memory returned) = decoder.staticcall(
                abi.encodeWithSignature("read(uint32,uint32)", offset, length)
            );
            if (!ok) _bubble(returned);
            bytes memory fragment = abi.decode(returned, (bytes));
            if (fragment.length != length) revert MR0Error(21);
            assembly ("memory-safe") {
                mcopy(add(add(out, 32), offset), add(fragment, 32), length)
            }
            offset += length;
        }
    }

    function _validateIndex() private view {
        if (
            finalIndex.codehash != ZI0_CODEHASH ||
            _u8(finalIndex, bytes4(keccak256("phase()"))) != 2 ||
            _b32(finalIndex, bytes4(keccak256("finalRoot()"))) != finalIndexRoot ||
            _address(finalIndex, bytes4(keccak256("owner()"))) != owner
        ) revert MR0Error(15);
    }

    function _engineCall(bytes memory data) private returns (bytes memory out) {
        (bool ok, bytes memory returned) = ENGINE.call(data);
        if (!ok) _bubble(returned);
        return returned;
    }

    function _view(address target, bytes4 selector) private view returns (bytes memory out) {
        (bool ok, bytes memory returned) = target.staticcall(abi.encodeWithSelector(selector));
        if (!ok) _bubble(returned);
        return returned;
    }

    function _u8(address target, bytes4 selector) private view returns (uint8) { return abi.decode(_view(target, selector), (uint8)); }
    function _u32(address target, bytes4 selector) private view returns (uint32) { return abi.decode(_view(target, selector), (uint32)); }
    function _b32(address target, bytes4 selector) private view returns (bytes32) { return abi.decode(_view(target, selector), (bytes32)); }
    function _address(address target, bytes4 selector) private view returns (address) { return abi.decode(_view(target, selector), (address)); }

    function _validClassName(bytes memory name) private pure returns (bool) {
        if (name.length <= 6 || name.length > 256) return false;
        bytes memory suffix = ".class";
        uint256 stem = name.length - 6;
        for (uint256 i; i < 6; ++i) if (name[stem + i] != suffix[i]) return false;
        for (uint256 i; i < stem; ++i) {
            bytes1 character = name[i];
            if (character == 0 || character == bytes1("\\") || character == bytes1(".")) return false;
        }
        return true;
    }

    function _validSeedName(bytes memory name) private pure returns (bool) {
        if (name.length == 0 || name.length > 256 || name[0] == bytes1("/")) return false;
        uint256 component;
        for (uint256 i; i < name.length; ++i) {
            uint8 c = uint8(name[i]);
            if (c < 0x20 || c > 0x7e || c == 0x5c) return false;
            if (c == 0x2f) {
                if (component == 0) return false;
                component = 0;
            } else {
                if (++component > 64) return false;
            }
        }
        return component != 0;
    }

    function _internalName(bytes memory name) private pure returns (string memory) {
        bytes memory internalName = new bytes(name.length - 6);
        for (uint256 i; i < internalName.length; ++i) internalName[i] = name[i];
        return string(internalName);
    }

    function _bubble(bytes memory data) private pure {
        assembly ("memory-safe") { revert(add(data, 32), mload(data)) }
    }
}
