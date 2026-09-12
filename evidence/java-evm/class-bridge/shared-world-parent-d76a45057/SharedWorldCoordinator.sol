// SPDX-License-Identifier: GPL-3.0
pragma solidity 0.8.30;

interface ISWTypes {
    struct SeedFile { bytes path; bytes data; bool readOnly; }
}

/// Disposable shared-world coordinator preflight. Constructor-fixed generated
/// fixture package only; this is not a production ClassLoader or accepted ABI.
contract SharedWorldCoordinator {
    error CoordinatorError(uint256 code);

    address constant ENGINE = 0x4a564D45564D564653304152554e54494D450001;
    bytes32 constant ENGINE_CODEHASH = hex"e7f4de699588a3d58624e8ab717a00809759d112952ca1fac8bbc74637118c84";
    bytes32 constant DI0_CODEHASH = hex"946686a0a4f09ec9a03e3eb63e9bbeac008212061d6f316586034cf800380c37";
    bytes32 constant ZI0_CODEHASH = hex"0c22eca78e00865ce03e8e298708bfe51ce9856cff138d1046905fc285ad5a77";
    bytes32 constant PACKAGE_DOMAIN = keccak256("MC-SHARED-WORLD-PREFLIGHT/package/v1");
    bytes32 constant RESOURCE_DOMAIN = keccak256("MC-SHARED-WORLD-PREFLIGHT/resource/v1");
    bytes32 constant VM_DOMAIN = keccak256("MC-SHARED-WORLD-PREFLIGHT/vm/v1");

    address public owner;
    address public finalIndex;
    bytes32 public finalIndexRoot;
    bytes32 public packageRoot;
    bytes32 public instanceId;
    uint32 public totalClassBytes;
    uint8 public classCount;

    address[4] private decoders;
    bytes32[4] private resourceRoots;
    uint32[4] private classSizes;
    bytes[4] private rawNames;

    constructor(
        address fixedOwner,
        bytes32 fixedInstanceSalt,
        address[] memory fixedDecoders,
        bytes[] memory fixedRawNames,
        bytes32[] memory assertedIndexRoots,
        bytes32[] memory assertedResourceRoots,
        bytes32 assertedPackageRoot
    ) {
        if (fixedOwner == address(0) || fixedOwner != msg.sender) revert CoordinatorError(1);
        uint256 n = fixedDecoders.length;
        if (n == 0 || n > 4 || fixedRawNames.length != n || assertedIndexRoots.length != n || assertedResourceRoots.length != n) revert CoordinatorError(2);
        if (ENGINE.codehash != ENGINE_CODEHASH) revert CoordinatorError(3);
        owner = fixedOwner;
        classCount = uint8(n);
        address commonIndex;
        bytes32 commonIndexRoot;
        uint32 total;
        bytes32 rolling = keccak256(abi.encode(PACKAGE_DOMAIN, address(this), fixedOwner, ENGINE, ENGINE_CODEHASH, DI0_CODEHASH, ZI0_CODEHASH, uint8(n)));
        for (uint256 i; i < n; ++i) {
            address d = fixedDecoders[i];
            if (d.codehash != DI0_CODEHASH) revert CoordinatorError(4);
            for (uint256 j; j < i; ++j) if (fixedDecoders[j] == d || keccak256(fixedRawNames[j]) == keccak256(fixedRawNames[i])) revert CoordinatorError(5);
            bytes memory name = fixedRawNames[i];
            if (!_validRawName(name)) revert CoordinatorError(6);
            if (_u8(d, bytes4(keccak256("phase()"))) != 4) revert CoordinatorError(7);
            if (_b32(d, bytes4(keccak256("nameHash()"))) != keccak256(name)) revert CoordinatorError(8);
            bytes32 ir = assertedIndexRoots[i];
            if (ir == bytes32(0) || _b32(d, bytes4(keccak256("indexRoot()"))) != ir) revert CoordinatorError(9);
            bytes32 fr = assertedResourceRoots[i];
            if (fr == bytes32(0) || _b32(d, bytes4(keccak256("finalRoot()"))) != fr) revert CoordinatorError(10);
            uint32 size = _u32(d, bytes4(keccak256("plainSize()")));
            if (size == 0 || size > 65536) revert CoordinatorError(11);
            if (uint256(total) + size > 65536) revert CoordinatorError(12);
            total += size;
            address idx = _address(d, bytes4(keccak256("index()")));
            if (i == 0) { commonIndex = idx; commonIndexRoot = ir; }
            else if (idx != commonIndex || ir != commonIndexRoot) revert CoordinatorError(13);
            if (_address(d, bytes4(keccak256("owner()"))) != fixedOwner) revert CoordinatorError(14);
            decoders[i] = d; rawNames[i] = name; resourceRoots[i] = fr; classSizes[i] = size;
            rolling = keccak256(abi.encode(RESOURCE_DOMAIN, rolling, uint8(i), d, keccak256(name), ir, fr, size));
        }
        if (commonIndex.codehash != ZI0_CODEHASH || _u8(commonIndex, bytes4(keccak256("phase()"))) != 2 || _b32(commonIndex, bytes4(keccak256("finalRoot()"))) != commonIndexRoot || _address(commonIndex, bytes4(keccak256("owner()"))) != fixedOwner) revert CoordinatorError(15);
        finalIndex = commonIndex; finalIndexRoot = commonIndexRoot; totalClassBytes = total;
        bytes32 p = keccak256(abi.encode(PACKAGE_DOMAIN, rolling, total, commonIndex, commonIndexRoot));
        if (p != assertedPackageRoot || p == bytes32(0)) revert CoordinatorError(16);
        packageRoot = p;
        instanceId = keccak256(abi.encode(VM_DOMAIN, address(this), p, fixedInstanceSalt));
    }

    modifier onlyOwner() { if (msg.sender != owner) revert CoordinatorError(17); _; }

    function classBinding(uint8 at) external view returns (address,bytes memory,bytes32,uint32) {
        if (at >= classCount) revert CoordinatorError(19);
        return (decoders[at], rawNames[at], resourceRoots[at], classSizes[at]);
    }

    function start(bytes32 assertedPackageRoot, uint8 entryAt, string calldata entry, int32[] calldata args, uint64 maxJvmSteps, uint32 maxInternalSteps)
        external onlyOwner returns (bytes memory engineReturn)
    {
        if (assertedPackageRoot != packageRoot) revert CoordinatorError(18);
        if (entryAt >= classCount) revert CoordinatorError(19);
        bytes[] memory classes = _loadAll();
        ISWTypes.SeedFile[] memory seeds = new ISWTypes.SeedFile[](0);
        bytes memory callData = abi.encodeWithSignature(
            "start(bytes32,bytes[],string,string,int32[],(bytes,bytes,bool)[],uint64,uint32)",
            instanceId, classes, _internalName(rawNames[entryAt]), entry, args, seeds, maxJvmSteps, maxInternalSteps
        );
        return _engineCall(callData);
    }

    function resume(bytes32 assertedPackageRoot, uint64 expectedEpoch, bytes32 expectedCheckpointRoot, bytes calldata checkpoint, uint64 maxJvmSteps, uint32 maxInternalSteps)
        external onlyOwner returns (bytes memory engineReturn)
    {
        if (assertedPackageRoot != packageRoot) revert CoordinatorError(18);
        bytes[] memory classes = _loadAll();
        bytes memory callData = abi.encodeWithSignature(
            "resume(bytes32,uint64,bytes32,bytes[],bytes,uint64,uint32)",
            instanceId, expectedEpoch, expectedCheckpointRoot, classes, checkpoint, maxJvmSteps, maxInternalSteps
        );
        return _engineCall(callData);
    }

    function _loadAll() internal view returns (bytes[] memory classes) {
        if (ENGINE.codehash != ENGINE_CODEHASH) revert CoordinatorError(3);
        if (finalIndex.codehash != ZI0_CODEHASH || _u8(finalIndex, bytes4(keccak256("phase()"))) != 2 || _b32(finalIndex, bytes4(keccak256("finalRoot()"))) != finalIndexRoot) revert CoordinatorError(15);
        uint256 n = classCount;
        classes = new bytes[](n);
        for (uint256 i; i < n; ++i) {
            address d = decoders[i];
            bytes memory name = rawNames[i];
            if (d.codehash != DI0_CODEHASH || _u8(d, bytes4(keccak256("phase()"))) != 4 || _b32(d, bytes4(keccak256("nameHash()"))) != keccak256(name) || _b32(d, bytes4(keccak256("indexRoot()"))) != finalIndexRoot || _b32(d, bytes4(keccak256("finalRoot()"))) != resourceRoots[i] || _address(d, bytes4(keccak256("index()"))) != finalIndex || _address(d, bytes4(keccak256("owner()"))) != owner || _u32(d, bytes4(keccak256("plainSize()"))) != classSizes[i]) revert CoordinatorError(20);
            uint32 size = classSizes[i];
            bytes memory klass = new bytes(size);
            for (uint32 offset; offset < size;) {
                uint32 count = size - offset;
                if (count > 4096) count = 4096;
                (bool ok, bytes memory out) = d.staticcall(abi.encodeWithSignature("read(uint32,uint32)", offset, count));
                if (!ok) _bubble(out);
                bytes memory part = abi.decode(out, (bytes));
                if (part.length != count) revert CoordinatorError(21);
                assembly ("memory-safe") { mcopy(add(add(klass,32),offset),add(part,32),count) }
                offset += count;
            }
            classes[i] = klass;
        }
    }

    function _engineCall(bytes memory data) private returns (bytes memory out) {
        (bool ok, bytes memory result) = ENGINE.call(data);
        if (!ok) _bubble(result);
        return result;
    }
    function _view(address a, bytes4 sel) private view returns (bytes memory out) {
        (bool ok, bytes memory result) = a.staticcall(abi.encodeWithSelector(sel));
        if (!ok) _bubble(result);
        return result;
    }
    function _u8(address a, bytes4 s) private view returns (uint8) { return abi.decode(_view(a,s),(uint8)); }
    function _u32(address a, bytes4 s) private view returns (uint32) { return abi.decode(_view(a,s),(uint32)); }
    function _b32(address a, bytes4 s) private view returns (bytes32) { return abi.decode(_view(a,s),(bytes32)); }
    function _address(address a, bytes4 s) private view returns (address) { return abi.decode(_view(a,s),(address)); }
    function _validRawName(bytes memory n) private pure returns (bool) {
        if (n.length <= 6 || n.length > 256) return false;
        bytes memory suffix = ".class";
        for (uint256 i; i < 6; ++i) if (n[n.length-6+i] != suffix[i]) return false;
        for (uint256 i; i < n.length-6; ++i) if (n[i] == 0 || n[i] == bytes1("\\") || n[i] == bytes1(".")) return false;
        return true;
    }
    function _internalName(bytes memory n) private pure returns (string memory) {
        bytes memory out = new bytes(n.length-6);
        for (uint256 i; i < out.length; ++i) out[i] = n[i];
        return string(out);
    }
    function _bubble(bytes memory data) private pure { assembly { revert(add(data,32),mload(data)) } }
}
