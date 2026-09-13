// SPDX-License-Identifier: GPL-3.0
pragma solidity 0.8.30;

/// @notice Fixed, constructor-bound generated-class package coordinator.
/// It reads the selected FINAL DI0 resources entirely inside the EVM and delegates
/// execution to the fixed LOCAL VFS0a interpreter. It is not a ClassLoader.
contract MCEntryCoordinator {
    error MR0Error(uint256 code);

    struct SeedFile {
        bytes path;
        bytes data;
        bool readOnly;
    }

    address private constant ENGINE = address(bytes20(hex"4d432d505249564143542d504152454e54310001"));
    // COPY-only repair engine pin; this coordinator remains otherwise ABI-identical.
    bytes32 private constant ENGINE_CODEHASH = hex"327a60e7a0a32a621291ed39875df8e9ef18be6dc37374fb6b5a9dbcf6435729";
    bytes32 private constant AS0_CODEHASH = hex"c8cec283e80fd82b15254bd50a9f2aea3a91305ba71f756f834439280600f896";
    bytes32 private constant ZI0_CODEHASH = hex"0c22eca78e00865ce03e8e298708bfe51ce9856cff138d1046905fc285ad5a77";
    bytes32 private constant DI0_CODEHASH = hex"946686a0a4f09ec9a03e3eb63e9bbeac008212061d6f316586034cf800380c37";
    bytes32 private constant PACKAGE_DOMAIN = keccak256("MC-PRIVILEGED-ACTION-PARENT1/package/v1");
    bytes32 private constant RESOURCE_DOMAIN = keccak256("MC-PRIVILEGED-ACTION-PARENT1/resource/v1");
    bytes32 private constant VM_DOMAIN = keccak256("MC-PRIVILEGED-ACTION-PARENT1/vm/v1");

    address public owner;
    address public finalIndex;
    bytes32 public finalIndexRoot;
    bytes32 public packageRoot;
    bytes32 public instanceId;
    uint32 public totalClassBytes;
    uint8 public classCount;

    address[24] private decoders;
    bytes32[24] private resourceRoots;
    uint32[24] private classSizes;
    bytes[24] private rawNames;

    constructor(
        address fixedOwner,
        bytes32 fixedInstanceSalt,
        address[] memory fixedDecoders,
        bytes[] memory fixedRawNames,
        bytes32[] memory assertedIndexRoots,
        bytes32[] memory assertedResourceRoots,
        bytes32 assertedPackageRoot
    ) {
        if (fixedOwner == address(0) || fixedOwner != msg.sender) revert MR0Error(1);
        uint256 n = fixedDecoders.length;
        if (
            n == 0 || n > 24 || fixedRawNames.length != n ||
            assertedIndexRoots.length != n || assertedResourceRoots.length != n
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
            if (!_validRawName(name)) revert MR0Error(6);
            if (_u8(decoder, bytes4(keccak256("phase()"))) != 4) revert MR0Error(7);
            if (_b32(decoder, bytes4(keccak256("nameHash()"))) != nameHash) revert MR0Error(8);

            bytes32 indexRoot = assertedIndexRoots[i];
            if (indexRoot == bytes32(0) || _b32(decoder, bytes4(keccak256("indexRoot()"))) != indexRoot) revert MR0Error(9);
            bytes32 resourceRoot = assertedResourceRoots[i];
            if (resourceRoot == bytes32(0) || _b32(decoder, bytes4(keccak256("finalRoot()"))) != resourceRoot) revert MR0Error(10);
            uint32 size = _u32(decoder, bytes4(keccak256("plainSize()")));
            if (size == 0 || size > 262144) revert MR0Error(11);
            if (uint256(total) + size > 262144) revert MR0Error(12);
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
            resourceRoots[i] = resourceRoot;
            classSizes[i] = size;
            rolling = keccak256(abi.encode(
                RESOURCE_DOMAIN, rolling, uint8(i), decoder, nameHash,
                indexRoot, resourceRoot, size
            ));
        }
        if (
            commonIndex.codehash != ZI0_CODEHASH ||
            _u8(commonIndex, bytes4(keccak256("phase()"))) != 2 ||
            _b32(commonIndex, bytes4(keccak256("finalRoot()"))) != commonIndexRoot ||
            _address(commonIndex, bytes4(keccak256("owner()"))) != fixedOwner
        ) revert MR0Error(15);

        finalIndex = commonIndex;
        finalIndexRoot = commonIndexRoot;
        totalClassBytes = total;
        bytes32 root = keccak256(abi.encode(PACKAGE_DOMAIN, rolling, total, commonIndex, commonIndexRoot));
        if (root == bytes32(0) || root != assertedPackageRoot) revert MR0Error(16);
        packageRoot = root;
        instanceId = keccak256(abi.encode(VM_DOMAIN, address(this), root, fixedInstanceSalt));
    }

    modifier onlyOwner() {
        if (msg.sender != owner) revert MR0Error(17);
        _;
    }

    function classBinding(uint8 at) external view returns (
        address decoder, bytes memory rawName, bytes32 resourceRoot, uint32 classSize
    ) {
        if (at >= classCount) revert MR0Error(19);
        return (decoders[at], rawNames[at], resourceRoots[at], classSizes[at]);
    }

    /// @notice Fixed direct `main(String[])` selection; no host argument vector exists.
    function startMain(bytes32 assertedPackageRoot, uint8 entryAt, uint64 maxJvmSteps, uint32 maxInternalSteps)
        external onlyOwner returns (bytes memory engineReturn)
    {
        if (assertedPackageRoot != packageRoot) revert MR0Error(18);
        if (entryAt >= classCount) revert MR0Error(19);
        bytes[] memory classes = _loadAll();
        SeedFile[] memory seeds = new SeedFile[](0);
        return _engineCall(abi.encodeWithSignature(
            "startMain(bytes32,bytes[],string,(bytes,bytes,bool)[],uint64,uint32)",
            instanceId, classes, _internalName(rawNames[entryAt]), seeds, maxJvmSteps, maxInternalSteps));
    }

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
        if (
            finalIndex.codehash != ZI0_CODEHASH ||
            _u8(finalIndex, bytes4(keccak256("phase()"))) != 2 ||
            _b32(finalIndex, bytes4(keccak256("finalRoot()"))) != finalIndexRoot ||
            _address(finalIndex, bytes4(keccak256("owner()"))) != owner
        ) revert MR0Error(15);
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
                _b32(decoder, bytes4(keccak256("finalRoot()"))) != resourceRoots[i] ||
                _address(decoder, bytes4(keccak256("index()"))) != finalIndex ||
                _address(decoder, bytes4(keccak256("owner()"))) != owner ||
                _u32(decoder, bytes4(keccak256("plainSize()"))) != classSizes[i]
            ) revert MR0Error(20);

            uint32 size = classSizes[i];
            bytes memory klass = new bytes(size);
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
                    mcopy(add(add(klass, 32), offset), add(fragment, 32), length)
                }
                offset += length;
            }
            classes[i] = klass;
        }
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

    function _validRawName(bytes memory name) private pure returns (bool) {
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

    function _internalName(bytes memory name) private pure returns (string memory) {
        bytes memory internalName = new bytes(name.length - 6);
        for (uint256 i; i < internalName.length; ++i) internalName[i] = name[i];
        return string(internalName);
    }

    function _bubble(bytes memory data) private pure {
        assembly ("memory-safe") { revert(add(data, 32), mload(data)) }
    }
}
