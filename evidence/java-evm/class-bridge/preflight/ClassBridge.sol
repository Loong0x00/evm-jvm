// SPDX-License-Identifier: GPL-3.0
pragma solidity 0.8.30;

interface IVFS0aTypes {
    struct SeedFile { bytes path; bytes data; bool readOnly; }
}

/// Disposable preflight adapter. It reads only a FINAL accepted DI0 controller,
/// validates the archive-name/binary-name binding, then calls the exact pinned
/// VFS0a entry. It has no class-byte input or decoded-byte installation method.
contract ClassBridge {
    error BridgeError(uint256 code);

    address constant ENGINE = 0x4a564D45564D564653304152554e54494D450001;
    bytes32 constant ENGINE_CODEHASH = hex"e7f4de699588a3d58624e8ab717a00809759d112952ca1fac8bbc74637118c84";
    bytes32 constant DI0_CODEHASH = hex"946686a0a4f09ec9a03e3eb63e9bbeac008212061d6f316586034cf800380c37";
    bytes32 constant INPUT_DOMAIN = keccak256("MC-CLASS-BRIDGE-PREFLIGHT/input/v1");
    address public owner;

    constructor() { owner = msg.sender; }
    modifier onlyOwner() { if (msg.sender != owner) revert BridgeError(10); _; }

    function start(
        address decoder, bytes calldata rawName, bytes32 assertedIndexRoot,
        bytes32 assertedResourceF, bytes32 instanceId, string calldata entryClass,
        string calldata entry, int32[] calldata args, uint64 maxJvmSteps,
        uint32 maxInternalSteps
    ) external onlyOwner returns (bytes32 inputBinding, bytes memory engineReturn) {
        (bytes memory klass, bytes32 binding) = _load(decoder, rawName, assertedIndexRoot, assertedResourceF, entryClass);
        bytes[] memory classes = new bytes[](1); classes[0] = klass;
        IVFS0aTypes.SeedFile[] memory seeds = new IVFS0aTypes.SeedFile[](0);
        bytes memory callData = abi.encodeWithSignature(
            "start(bytes32,bytes[],string,string,int32[],(bytes,bytes,bool)[],uint64,uint32)",
            instanceId, classes, entryClass, entry, args, seeds, maxJvmSteps, maxInternalSteps
        );
        return (binding, _engineCall(callData));
    }

    function resume(
        address decoder, bytes calldata rawName, bytes32 assertedIndexRoot,
        bytes32 assertedResourceF, bytes32 instanceId, string calldata entryClass,
        uint64 expectedEpoch, bytes32 expectedCheckpointRoot, bytes calldata checkpoint,
        uint64 maxJvmSteps, uint32 maxInternalSteps
    ) external onlyOwner returns (bytes32 inputBinding, bytes memory engineReturn) {
        (bytes memory klass, bytes32 binding) = _load(decoder, rawName, assertedIndexRoot, assertedResourceF, entryClass);
        bytes[] memory classes = new bytes[](1); classes[0] = klass;
        bytes memory callData = abi.encodeWithSignature(
            "resume(bytes32,uint64,bytes32,bytes[],bytes,uint64,uint32)",
            instanceId, expectedEpoch, expectedCheckpointRoot, classes, checkpoint, maxJvmSteps, maxInternalSteps
        );
        return (binding, _engineCall(callData));
    }

    function previewBinding(address decoder, bytes calldata rawName, bytes32 assertedIndexRoot,
        bytes32 assertedResourceF, string calldata entryClass) external view returns (bytes32) {
        (, bytes32 binding) = _load(decoder, rawName, assertedIndexRoot, assertedResourceF, entryClass);
        return binding;
    }

    function _load(address decoder, bytes calldata rawName, bytes32 assertedIndexRoot,
        bytes32 assertedResourceF, string calldata entryClass) internal view returns (bytes memory klass, bytes32 binding) {
        if (decoder.codehash != DI0_CODEHASH) revert BridgeError(1);
        if (ENGINE.codehash != ENGINE_CODEHASH) revert BridgeError(2);
        if (!_matchesEntryClass(rawName, bytes(entryClass))) revert BridgeError(3);
        if (_u8(decoder, bytes4(keccak256("phase()"))) != 4) revert BridgeError(4);
        if (_b32(decoder, bytes4(keccak256("nameHash()"))) != keccak256(rawName)) revert BridgeError(5);
        if (_b32(decoder, bytes4(keccak256("indexRoot()"))) != assertedIndexRoot || assertedIndexRoot == bytes32(0)) revert BridgeError(6);
        if (_b32(decoder, bytes4(keccak256("finalRoot()"))) != assertedResourceF || assertedResourceF == bytes32(0)) revert BridgeError(7);
        uint32 size = _u32(decoder, bytes4(keccak256("plainSize()")));
        if (size == 0 || size > 65536) revert BridgeError(8);
        (bool ok, bytes memory out) = decoder.staticcall(abi.encodeWithSignature("read(uint32,uint32)", uint32(0), size));
        if (!ok) _bubble(out);
        klass = abi.decode(out, (bytes));
        if (klass.length != size) revert BridgeError(9);
        binding = keccak256(abi.encode(INPUT_DOMAIN, decoder, DI0_CODEHASH, assertedIndexRoot,
            keccak256(rawName), assertedResourceF, size, keccak256(klass), ENGINE, ENGINE_CODEHASH, keccak256(bytes(entryClass))));
    }

    function _engineCall(bytes memory callData) internal returns (bytes memory out) {
        (bool ok, bytes memory result) = ENGINE.call(callData);
        if (!ok) _bubble(result);
        return result;
    }
    function _u8(address a, bytes4 sel) private view returns (uint8) { return abi.decode(_view(a,sel),(uint8)); }
    function _u32(address a, bytes4 sel) private view returns (uint32) { return abi.decode(_view(a,sel),(uint32)); }
    function _b32(address a, bytes4 sel) private view returns (bytes32) { return abi.decode(_view(a,sel),(bytes32)); }
    function _view(address a, bytes4 sel) private view returns (bytes memory out) {
        (bool ok, bytes memory result)=a.staticcall(abi.encodeWithSelector(sel)); if(!ok) _bubble(result); return result;
    }
    // VFS0a expects a JVM internal class name (slash-separated), not a dotted
    // source-language binary name. It must exactly equal the ZIP name sans .class.
    function _matchesEntryClass(bytes calldata rawName, bytes memory entryClass) private pure returns (bool) {
        if (rawName.length <= 6 || entryClass.length != rawName.length - 6) return false;
        bytes memory suffix = ".class";
        for (uint256 i; i < 6; ++i) if (rawName[rawName.length-6+i] != suffix[i]) return false;
        for (uint256 i; i < entryClass.length; ++i) {
            bytes1 c=rawName[i];
            if (c != entryClass[i] || c==bytes1(0) || c==bytes1('\\') || c==bytes1('.')) return false;
        }
        return true;
    }
    function _bubble(bytes memory data) private pure { assembly { revert(add(data,32),mload(data)) } }
}
