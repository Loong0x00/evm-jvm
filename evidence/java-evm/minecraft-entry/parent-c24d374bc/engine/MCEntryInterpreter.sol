// SPDX-License-Identifier: LGPL-3.0-or-later
pragma solidity 0.8.30;

/// @notice A deliberately small JVM classfile interpreter which runs entirely in EVM bytecode.
/// It accepts either one ordinary class or an unordered raw-class bundle, selects an
/// unambiguous static (int...)int root, and supports direct class-aware static I/V calls.
contract MCEntryInterpreter {
    error ClassError(uint256 code, uint256 offset);
    error MethodError(uint256 code);
    error BytecodeError(uint256 code, uint256 pc);
    error JavaException(uint256 kind);
    error CallError(uint256 code, uint256 pc);
    error LinkError(uint256 code, uint256 detail);
    // COPY-only diagnostic: site 0x1002 has owner-class-index context; PC sites have bytecode-PC context.
    error MCEntryMissingClass(uint256 site, uint256 context, bytes name);
    error FieldError(uint256 code, uint256 location);
    error InitError(uint256 code, uint256 classIndex);
    error HierarchyError(uint256 code, uint256 classIndex);
    error ArrayError(uint256 code, uint256 pc);
    error ReferenceError(uint256 code, uint256 pc);
    error ObjectError(uint256 code, uint256 pc);
    error TypeError(uint256 code, uint256 pc);
    error InterfaceError(uint256 code, uint256 location);
    error HandlerError(
        uint256 code, uint256 classIndex, uint256 methodIndex, uint256 entryIndex
    );
    error BootstrapProfileError(uint256 code, uint256 inputIndex);
    error StringProfileError(uint256 code, uint256 pc);
    error StringConstantError(
        uint256 code, uint256 classIndex, uint256 cpIndex, uint256 byteOffset
    );
    error ThrowableProfileError(uint256 code, uint256 classIndex, uint256 methodIndex);
    error ThrowableAPIProfileError(uint256 kind, uint256 invokePC);
    error VFS0aProfileError(uint256 code, uint256 pc);
    error VFS0aQuotaError(uint256 code, uint256 requested, uint256 limit);
    error VFS0aStateError(uint256 code, uint256 byteOffset);

    uint256 private constant MAX_CONSTANT_POOL = 4096;
    uint256 private constant MAX_CODE = 65535;
    uint256 private constant MAX_STACK = 1024;
    uint256 private constant MAX_LOCALS = 1024;
    uint256 private constant MAX_FRAMES = 128; // root plus Java frames and init continuations
    uint256 private constant MAX_ARRAYS = 1024;
    uint256 private constant MAX_ARRAY_LENGTH = 65536;
    uint256 private constant MAX_ARRAY_ELEMENTS = 262144;
    uint256 private constant MAX_OBJECTS = 1024;
    uint256 private constant MAX_OBJECT_FIELDS = 1024;
    uint256 private constant MAX_OBJECT_FIELD_SLOTS = 65536;
    uint256 private constant MAX_EXCEPTION_OBJECTS = 256;
    uint256 private constant MAX_EXCEPTION_FIELD_SLOTS = 262144;
    uint256 private constant MAX_EXCEPTION_HANDLERS = 256;
    uint256 private constant MAX_INTERNED_STRINGS = 1024;
    // MC-VFS0a local execution gates use explicit finite 100M ordinary and 1B
    // boundary gas caps in the harness; these labels do not alter EVM charging.
    uint256 private constant LOCAL_MC_VFS0A_ORDINARY_GAS_CAP = 100_000_000;
    uint256 private constant LOCAL_MC_VFS0A_BOUNDARY_GAS_CAP = 1_000_000_000;
    uint256 private constant MAX_HANDLES = MAX_ARRAYS + MAX_OBJECTS
        + MAX_EXCEPTION_OBJECTS + 1; // one reserved emergency OOM
    uint256 private constant ROOT_FAULT_SENTINEL = type(uint256).max;
    // A runtime value is a 64-bit payload plus an internal kind. Category-2 longs
    // remain one indivisible EVM value, while stack/local capacity is charged in
    // JVM words by the helpers below.
    uint256 private constant KIND_SHIFT = 64;
    uint256 private constant KIND_INT = 1;
    uint256 private constant KIND_REF = 2;
    uint256 private constant KIND_UNINIT = 3;
    uint256 private constant KIND_LONG = 4;
    uint256 private constant KIND_LONG_TAIL = 5;
    uint256 private constant KIND_FLOAT = 6;
    uint256 private constant KIND_DOUBLE = 7;
    uint256 private constant KIND_DOUBLE_TAIL = 8;
    uint8 private constant HEAP_ARRAY = 1;
    uint8 private constant HEAP_OBJECT = 2;
    uint256 private constant HEAP_OBJECT_MARKER = uint256(1) << 255;
    uint8 private constant PRIMITIVE_BYTE = 0x42; // B
    uint8 private constant PRIMITIVE_CHAR = 0x43; // C
    uint8 private constant PRIMITIVE_DOUBLE = 0x44; // D
    uint8 private constant PRIMITIVE_FLOAT = 0x46; // F
    uint8 private constant PRIMITIVE_INT = 0x49; // I
    uint8 private constant PRIMITIVE_LONG = 0x4a; // J
    uint8 private constant PRIMITIVE_SHORT = 0x53; // S
    uint8 private constant PRIMITIVE_BOOLEAN = 0x5a; // Z
    // Primitive array leaves use their descriptor byte. Reference leaves are kept
    // in a disjoint namespace so no zero/default class id can alias int[].
    uint256 private constant ARRAY_CLASS_BASE = 0x100;

    // Array types are represented without synthetic host classes: rank 1..255 and an
    // explicit ultimate primitive descriptor or ARRAY_CLASS_BASE + class index.
    struct ArrayType {
        uint8 rank;
        uint256 leafType;
    }

    struct MultiArrayPlan {
        uint256[] counts;
        uint256 arrays;
        uint256 elements;
    }

    struct Reader {
        bytes data;
        uint256 pos;
    }

    struct Selected {
        bool loaded;
        uint256 descriptorOffset;
        uint256 descriptorLength;
        uint256 codeOffset;
        uint256 codeLength;
        uint256 maxStack;
        uint256 maxLocals;
        uint256 argumentCount;
        uint256 argumentWords;
        uint8[] argumentKinds;
        uint256[] argumentTypeOffsets;
        uint256[] argumentTypeLengths;
        uint8 returnKind; // 1=int, 2=void, 3=reference, 4=long, 5=float, 6=double
        uint8 returnSubtype; // exact I/Z/B/C/S descriptor for computational-int returns
        uint256 returnTypeOffset;
        uint256 returnTypeLength;
        // Code exception_table entries retain classfile order. Resolution is lazy
        // and applies only after the protected range is reached during unwind.
        uint16[] handlerStarts;
        uint16[] handlerEnds;
        uint16[] handlerPCs;
        uint16[] handlerCatchTypes;
        uint256[] handlerClassesPlusOne;
        uint256 declaringClass;
        uint256 methodIndex;
    }

    struct FieldInfo {
        uint16 accessFlags;
        uint16 nameIndex;
        uint16 descriptorIndex;
        bool hasConstant;
        // Primitive bits or, for Ljava/lang/String;, the full CONSTANT_String CP index.
        uint256 constantValue;
    }

    struct ClassInfo {
        bytes data;
        // One packed word per CP slot. Low byte is the tag. Utf8 stores offset/length,
        // Integer stores its 32 bits, and reference entries store their u2 operands.
        uint256[] cp;
        FieldInfo[] fields;
        // One packed word per method: flags/name/descriptor and lazy Code attribute location.
        uint256[] methods;
        // Constant-pool Class indices for direct interfaces, in classfile order.
        uint16[] interfaces;
        uint256 thisNameOffset;
        uint256 thisNameLength;
        uint256 superNameOffset;
        uint256 superNameLength;
        uint256 initializerPlusOne;
        uint16 accessFlags;
        bool invalidInitializer;
        bool unsupportedSemantics;
        bool hasSuperclass;
    }

    struct Frame {
        uint256 classIndex;
        uint256 methodIndex;
        uint256 pc;
        uint256 sp;
        uint256 callPC;
        uint256[] stack; // low 64 bits payload, kind above it; long is one value/two words
        uint256[] locals;
        bool[] initialized;
        bool isInitializer;
        bool isInitContinuation;
        bool isConstructor;
        bool isConstructorLinked;
        bool entered; // false only for the dormant root during its initialization
        uint256 thisHandle;
    }

    struct PendingException {
        bool active;
        uint256 kind;
        uint256 ref;
        uint256 faultPC;
    }

    struct HeapRegistry {
        uint64[][] arrayHeap;
        uint256[][] objectHeap;
        uint256[] metadata;
        uint256[] classes;
        uint8[] ranks;
    }

    struct ExceptionArena {
        PendingException pending;
        // The single authoritative lazy registry and handle stream. Ordinary
        // objects/arrays, interned Strings, and exception objects all mutate it.
        HeapRegistry heap;
        uint256 nextHandle;
        uint256 ordinaryObjectCount;
        uint256 ordinaryArrayCount;
        uint256 ordinaryArrayElements;
        uint256 ordinaryFieldSlots;
        uint256 objectCount;
        uint256 fieldSlots;
        uint256 emergencyRef;
        uint256 throwableClass;
        uint256 errorClass;
        uint256[] classesByKind;
        // IOE0 stores VM-wrapper causes only in the canonical EIIE.exception
        // field. There is deliberately no second side-table authority.
        uint256[][] fieldDefaults;
        bool[] layoutsLoaded;
        uint256 stringClass;
        uint256 stringValueOffset;
        uint256 stringHashOffset;
        uint256[] stringDefaults;
        bool stringLayoutLoaded;
        uint256[] internHandles;
        uint32[] internHashes;
        uint256 internCount;
        uint256[][] stringRefs;
        // Class mirrors are ordinary guest objects.  There is deliberately no host
        // registry: canonicality is recovered by validated EVM heap scan.
        uint256 classClass;
        uint256 classNameOffset;
        uint256[] classDefaults;
        bool classLayoutLoaded;
    }

    // A finite IEEE value is significand * 2^scale. The significand is at most
    // 24/53 bits; classKind is zero/finite/infinity/NaN. Arithmetic never uses
    // an EVM- or host-floating operation.
    struct SeedFile { bytes path; bytes data; bool readOnly; }

    struct VFSInode {
        uint32 id;
        uint8 kind; // 1 directory, 2 regular file
        bool readOnly;
        uint32 parent;
        bytes name;
        bytes data;
    }

    struct VFSDescriptor {
        uint32 id;
        uint32 inode;
        uint32 ownerRef;
        uint8 flags; // READ=1, WRITE=2, APPEND=4
        uint64 cursor;
        uint8 phase; // PENDING_BIND=1, BOUND=2, CLOSED=3
        uint16 bindDepth;
        uint32 bindPC; // exact reserved constructor putfield PC while pending
    }

    struct VFSBindPlan {
        uint256 method;
        uint32 invokePC;
        uint32 afterInvokePC;
        uint32 afterStorePC;
        uint32 afterLoadPC;
        uint32 successPC;
        uint32 afterOwnerPC;
        uint32 putfieldPC;
        uint8 idLocal;
    }

    struct VFSState {
        bytes32 seedRoot;
        uint32 nextInode;
        uint32 nextDescriptor;
        uint64 logicalFileBytes;
        VFSInode[] inodes;
        VFSDescriptor[] descriptors;
    }

    struct RuntimeState {
        uint8 lifecycle;
        int32 result;
        uint64 totalJvmSteps;
        uint64 totalInternalSteps;
        Frame[] frames;
        uint256 depth;
        uint8[] initializationState;
        bool[] initializerStarted;
        uint256[][] staticValues;
        uint256[] parentLinks;
        uint8[] hierarchyState;
        ExceptionArena arena;
        uint256 nextHandle;
        bool rootInitializationScheduled;
        VFSState vfs;
    }

    struct Program {
        ClassInfo[] classes;
        Selected[][][] selected;
        uint256[][] referenceCaches;
        uint256[][] fieldCaches;
        uint256 rootClass;
        uint256 rootMethod;
        uint256 throwableBootstrapAt;
        // Appends after Runnable are conditional: retain the exact Class slot rather
        // than reconstructing it from a fixed historical offset on restore.
        uint256 classClass;
        bool mainRoot;
    }

    struct MR0MainSliceResult {
        uint32 schema;
        uint8 lifecycle;
        uint8 outcome; // 1=RUNNING,2=VOID_TERMINAL,3=JAVA_EXCEPTION
        uint64 epoch;
        bytes32 checkpointRoot;
        bytes32 machineStateRoot;
        uint64 totalJvmSteps;
        uint64 totalInternalSteps;
        uint64 executedJvmSteps;
        uint32 executedInternalSteps;
        int32 result;
        uint8 javaKind;
        uint32 javaRef;
        bytes javaClass;
        bytes32 vfsStateRoot;
        uint32 inodeCount;
        uint32 descriptorCount;
        uint64 logicalFileBytes;
    }

    struct Anchor {
        address owner;
        uint64 epoch;
        bytes32 checkpointRoot;
        bytes32 machineStateRoot;
        bytes32 vfsStateRoot;
        bytes32 seedRoot;
        bytes32 artifactRoot;
        bytes32 configRoot;
        bytes32 runtimeCodeHash;
        uint8 lifecycle;
    }

    struct Envelope {
        bytes32 instanceId;
        uint64 epoch;
        bytes32 parentCheckpointRoot;
        bytes32 runtimeCodeHash;
        bytes32 artifactRoot;
        bytes32 configRoot;
        bytes32 machineStateRoot;
        bytes32 seedRoot;
        bytes32 vfsStateRoot;
        bytes machineBytes;
    }

    struct Prelude {
        uint8 lifecycle;
        int32 result;
        uint8 javaKind;
        uint32 javaRef;
        uint64 totalJvmSteps;
        uint64 totalInternalSteps;
        uint8 rootKind;
        bytes32 argsCommitment;
        bytes entryClass;
        bytes entry;
        int32[] args;
    }

    error LC0ControlError(uint256 code);
    error LC0StateError(uint256 code, uint256 byteOffset);
    event CheckpointCommitted(
        bytes32 indexed instanceId, uint64 indexed epoch, bytes32 checkpointRoot,
        bytes32 machineStateRoot, bytes32 vfsStateRoot, uint8 lifecycle,
        uint64 totalJvmSteps, uint64 totalInternalSteps
    );

    uint32 private constant MR0_SCHEMA = 1;
    uint8 private constant ROOT_KIND_MAIN_EMPTY_STRING_ARRAY = 1;
    bytes32 private constant EMPTY_ARGS_COMMITMENT = keccak256("JVMEVM:MC-PROPERTIES-PARENT1:MAIN:EMPTY-STRING-ARRAY:1");
    bytes32 private constant DROOT = keccak256("JVMEVM:MC-PROPERTIES-PARENT1:ROOT:1");
    uint256 private constant MAX_RAW_CLASSES = 24;
    uint256 private constant MAX_RAW_BYTES = 262144;
    uint256 private constant MAX_CHECKPOINT_BYTES = 1048576;
    uint256 private constant CHECKPOINT_HEADER_BYTES = 280;
    uint256 private constant COMMIT_RESERVE = 25_000_000;
    uint32 private constant MAX_SEEDS = 16;
    uint32 private constant MAX_SEED_BYTES = 65536;
    uint32 private constant MAX_VFS_INODES = 64;
    uint32 private constant MAX_VFS_DESCRIPTORS = 32;
    uint32 private constant MAX_FILE_BYTES = 65536;
    uint64 private constant MAX_ALL_FILE_BYTES = 65536;
    uint32 private constant MAX_PATH_COMPONENT = 64;
    uint32 private constant MAX_PATH_DEPTH = 16;
    uint32 private constant MAX_PATH_BYTES = 256;
    uint32 private constant MAX_TRANSFER = 4096;
    bytes32 private constant DART = keccak256("JVMEVM:MC-PROPERTIES-PARENT1:ARTIFACT:1");
    bytes32 private constant DBOOT = keccak256("JVMEVM:MC-PROPERTIES-PARENT1:BOOTSTRAP:1");
    bytes32 private constant DCFG = keccak256("JVMEVM:MC-PROPERTIES-PARENT1:CONFIG:1");
    bytes32 private constant DMACH = keccak256("JVMEVM:MC-PROPERTIES-PARENT1:MACHINE:1");
    bytes32 private constant DSEED = keccak256("JVMEVM:MC-PROPERTIES-PARENT1:SEED:1");
    bytes32 private constant DVFS = keccak256("JVMEVM:MC-PROPERTIES-PARENT1:VFS:1");
    bytes32 private constant DFILE = keccak256("JVMEVM:MC-PROPERTIES-PARENT1:FILE:1");

    mapping(bytes32 => Anchor) private anchors;
    bool private enteredVFS0A;

    // A finite IEEE value is significand * 2^scale. The significand is at most
    struct IEEEValue {
        bool sign;
        uint8 classKind;
        uint256 significand;
        int256 scale;
    }

    struct VirtualResolution {
        uint256 owner;
        uint256 method;
        uint256 symbolic;
        uint256 referenceClass;
        uint256 nameOffset;
        uint256 nameLength;
        uint256 descriptorOffset;
        uint256 descriptorLength;
        uint256 javaFault;
    }

    /// @notice Direct generated `main(String[])` root. No host arguments are accepted.
    function startMain(
        bytes32 instanceId, bytes[] calldata rawClasses, string calldata entryClass,
        SeedFile[] calldata seeds, uint64 maxJvmSteps, uint32 maxInternalSteps
    ) external returns (MR0MainSliceResult memory result, bytes memory checkpoint) {
        if (enteredVFS0A) revert LC0ControlError(8);
        enteredVFS0A = true;
        if (instanceId == bytes32(0) || anchors[instanceId].epoch != 0) revert LC0ControlError(1);
        if (msg.sender == address(0)) revert LC0ControlError(2);
        _checkBudgets(maxJvmSteps, maxInternalSteps);
        bytes32 runtimeHash = address(this).codehash;
        bytes32 artifact = _artifactRoot(rawClasses);
        bytes memory ec = bytes(entryClass);
        bytes memory en = bytes("main");
        if (ec.length == 0 || ec.length > 256 || !_ascii(ec)) revert LC0ControlError(6);
        int32[] memory noArgs = new int32[](0);
        bytes32 seedRoot = keccak256(abi.encode(DSEED, seeds));
        bytes32 config = _configRoot(runtimeHash, artifact, ec, en, noArgs, seedRoot);
        Program memory p = _prepare(rawClasses, ec, en, noArgs);
        RuntimeState memory st = _freshState(p, noArgs, true);
        st.vfs = _initialVFS(seeds, seedRoot);
        (uint64 ej, uint32 ei) = _execute(p.classes, p.selected, p.referenceCaches, p.fieldCaches,
            p.rootClass, p.rootMethod, true, p.throwableBootstrapAt, st, maxJvmSteps, maxInternalSteps);
        (result, checkpoint) = _commit(instanceId, 1, bytes32(0), runtimeHash, artifact, config,
            ec, en, noArgs, p, st, ej, ei);
        enteredVFS0A = false;
    }

    /// @notice Resumes only the EVM-issued opaque direct-main checkpoint.
    function resumeMain(
        bytes32 instanceId, uint64 expectedEpoch, bytes32 expectedCheckpointRoot,
        bytes[] calldata rawClasses, bytes calldata checkpoint, uint64 maxJvmSteps,
        uint32 maxInternalSteps
    ) external returns (MR0MainSliceResult memory result, bytes memory childCheckpoint) {
        if (enteredVFS0A) revert LC0ControlError(8);
        enteredVFS0A = true;
        Anchor memory a = anchors[instanceId];
        if (a.epoch == 0 || a.lifecycle != 1) revert LC0ControlError(1);
        if (msg.sender == address(0) || msg.sender != a.owner) revert LC0ControlError(2);
        if (expectedEpoch != a.epoch) revert LC0ControlError(3);
        if (expectedCheckpointRoot != a.checkpointRoot || keccak256(checkpoint) != a.checkpointRoot) revert LC0ControlError(4);
        _checkBudgets(maxJvmSteps, maxInternalSteps);
        Envelope memory env = _decodeEnvelope(checkpoint);
        if (env.instanceId != instanceId || env.epoch != a.epoch) revert LC0ControlError(5);
        bytes32 runtimeHash = address(this).codehash;
        bytes32 artifact = _artifactRoot(rawClasses);
        if (runtimeHash != a.runtimeCodeHash || env.runtimeCodeHash != runtimeHash || artifact != a.artifactRoot
            || env.configRoot != a.configRoot || env.machineStateRoot != a.machineStateRoot
            || env.seedRoot != a.seedRoot || env.vfsStateRoot != a.vfsStateRoot) revert LC0ControlError(5);
        Prelude memory pre = _decodePrelude(env.machineBytes, CHECKPOINT_HEADER_BYTES);
        if (pre.lifecycle != 1 || pre.rootKind != ROOT_KIND_MAIN_EMPTY_STRING_ARRAY
            || pre.argsCommitment != EMPTY_ARGS_COMMITMENT || !_equalsLiteral(pre.entry, 0, pre.entry.length, bytes("main"))
            || pre.args.length != 0) revert LC0ControlError(5);
        if (_configRoot(runtimeHash, artifact, pre.entryClass, pre.entry, pre.args, env.seedRoot) != a.configRoot) revert LC0ControlError(5);
        Program memory p = _prepare(rawClasses, pre.entryClass, pre.entry, pre.args);
        RuntimeState memory st = _decodeMachine(env.machineBytes, p, pre, CHECKPOINT_HEADER_BYTES);
        st.vfs.seedRoot = env.seedRoot;
        if (_vfsRoot(st.vfs) != env.vfsStateRoot) revert VFS0aStateError(6, 244);
        (uint64 ej, uint32 ei) = _execute(p.classes, p.selected, p.referenceCaches, p.fieldCaches,
            p.rootClass, p.rootMethod, true, p.throwableBootstrapAt, st, maxJvmSteps, maxInternalSteps);
        if (a.epoch == type(uint64).max) revert LC0ControlError(6);
        (result, childCheckpoint) = _commit(instanceId, a.epoch + 1, a.checkpointRoot, runtimeHash,
            artifact, a.configRoot, pre.entryClass, pre.entry, pre.args, p, st, ej, ei);
        enteredVFS0A = false;
    }

    function head(bytes32 instanceId) external view returns (
        address owner, uint64 epoch, bytes32 checkpointRoot, bytes32 machineStateRoot,
        bytes32 vfsStateRoot, bytes32 seedRoot, bytes32 artifactRoot,
        bytes32 configRoot, bytes32 runtimeCodeHash, uint8 lifecycle
    ) {
        Anchor memory a = anchors[instanceId];
        return (a.owner, a.epoch, a.checkpointRoot, a.machineStateRoot, a.vfsStateRoot,
            a.seedRoot, a.artifactRoot, a.configRoot, a.runtimeCodeHash, a.lifecycle);
    }

    function validateCheckpoint(bytes[] calldata rawClasses, bytes calldata checkpoint)
        external view returns (bytes32 machineStateRoot, bytes32 vfsStateRoot)
    {
        Envelope memory env = _decodeEnvelope(checkpoint);
        bytes32 artifact = _artifactRoot(rawClasses);
        if (env.runtimeCodeHash != address(this).codehash || env.artifactRoot != artifact) {
            revert LC0StateError(3, 0);
        }
        Prelude memory pre = _decodePrelude(env.machineBytes, CHECKPOINT_HEADER_BYTES);
        if (_configRoot(env.runtimeCodeHash, artifact, pre.entryClass, pre.entry, pre.args,
            env.seedRoot) != env.configRoot) revert LC0StateError(3, 0);
        Program memory p = _prepare(rawClasses, pre.entryClass, pre.entry, pre.args);
        RuntimeState memory st = _decodeMachine(env.machineBytes, p, pre, CHECKPOINT_HEADER_BYTES);
        st.vfs.seedRoot = env.seedRoot;
        bytes memory canonical = _encodeMachine(p, st, pre.entryClass, pre.entry, pre.args);
        if (keccak256(canonical) != keccak256(env.machineBytes)) revert LC0StateError(3, 0);
        bytes32 actualVFS = _vfsRoot(st.vfs);
        if (actualVFS != env.vfsStateRoot || st.vfs.seedRoot != env.seedRoot) {
            revert VFS0aStateError(6, 244);
        }
        return (env.machineStateRoot, actualVFS);
    }

    function inspectFile(
        bytes[] calldata rawClasses, bytes calldata checkpoint, bytes calldata path,
        uint32 offset, uint32 maxBytes
    ) external view returns (
        uint8 kind, bool effectiveReadOnly, uint32 inode, bytes memory data, bytes32 fileRoot
    ) {
        if (maxBytes > MAX_TRANSFER) revert VFS0aProfileError(3, 0);
        Envelope memory env = _decodeEnvelope(checkpoint);
        bytes32 artifact = _artifactRoot(rawClasses);
        if (env.runtimeCodeHash != address(this).codehash || env.artifactRoot != artifact) {
            revert LC0StateError(3, 0);
        }
        Prelude memory pre = _decodePrelude(env.machineBytes, CHECKPOINT_HEADER_BYTES);
        if (_configRoot(env.runtimeCodeHash, artifact, pre.entryClass, pre.entry, pre.args,
            env.seedRoot) != env.configRoot) revert LC0StateError(3, 0);
        Program memory p = _prepare(rawClasses, pre.entryClass, pre.entry, pre.args);
        RuntimeState memory st = _decodeMachine(env.machineBytes, p, pre, CHECKPOINT_HEADER_BYTES);
        st.vfs.seedRoot = env.seedRoot;
        if (_vfsRoot(st.vfs) != env.vfsStateRoot || st.vfs.seedRoot != env.seedRoot) {
            revert VFS0aStateError(6, 244);
        }
        bytes memory canonical = _canonicalPath(_lexicalPath(path, 0), 0);
        inode = _lookupPath(st.vfs, canonical);
        if (inode == 0) return (0, false, 0, bytes(""), bytes32(0));
        VFSInode memory n = st.vfs.inodes[inode - 1];
        kind = n.kind;
        effectiveReadOnly = _effectiveReadOnly(st.vfs, inode);
        uint256 take;
        if (kind == 2 && offset < n.data.length) {
            take = n.data.length - offset;
            if (take > maxBytes) take = maxBytes;
        }
        data = new bytes(take);
        for (uint256 i; i < take; ++i) data[i] = n.data[uint256(offset) + i];
        bytes memory fullPath = _inodePath(st.vfs, inode);
        fileRoot = keccak256(abi.encode(
            DFILE, uint32(1), inode, kind, effectiveReadOnly, fullPath, keccak256(n.data)
        ));
    }

    function _checkBudgets(uint64 jvm, uint32 internalSteps) private view {
        if (jvm == 0 || jvm > 4096 || internalSteps == 0 || internalSteps > 4096) {
            revert LC0ControlError(6);
        }
        if (gasleft() <= COMMIT_RESERVE) revert LC0ControlError(7);
    }

    function _artifactRoot(bytes[] calldata rawClasses) private pure returns (bytes32) {
        uint256 total;
        if (rawClasses.length == 0 || rawClasses.length > MAX_RAW_CLASSES) {
            revert LinkError(1, rawClasses.length);
        }
        for (uint256 i; i < rawClasses.length; ++i) total += rawClasses[i].length;
        if (total > MAX_RAW_BYTES) revert LinkError(1, total);
        return keccak256(abi.encode(DART, rawClasses));
    }

    function _configRoot(
        bytes32 runtimeHash, bytes32 artifact, bytes memory entryClass,
        bytes memory entry, int32[] memory args, bytes32 seedRoot
    ) private pure returns (bytes32) {
        uint32[11] memory limits = [
            uint32(24), uint32(262144), uint32(64), uint32(32), uint32(65536),
            uint32(65536), uint32(16), uint32(64), uint32(256), uint32(4096),
            uint32(1048576)
        ];
        bytes32 limitsHash = keccak256(abi.encode(limits));
        return keccak256(abi.encode(
            DCFG, MR0_SCHEMA, runtimeHash, _bootstrapRoot(), artifact,
            DROOT, ROOT_KIND_MAIN_EMPTY_STRING_ARRAY, string(entryClass), string(entry),
            EMPTY_ARGS_COMMITMENT, args, seedRoot, limitsHash
        ));
    }

    function _bootstrapRoot() private pure returns (bytes32) {
        bytes32[] memory h = new bytes32[](48);
        h[0] = keccak256(_bootstrapObject());
        h[1] = keccak256(_bootstrapCloneable());
        h[2] = keccak256(_bootstrapSerializable());
        h[3] = keccak256(_bootstrapFloat());
        h[4] = keccak256(_bootstrapDouble());
        h[5] = keccak256(_bootstrapThrowable());
        h[6] = keccak256(_bootstrapError());
        h[7] = keccak256(_bootstrapVirtualMachineError());
        h[8] = keccak256(_bootstrapStackOverflowError());
        h[9] = keccak256(_bootstrapOutOfMemoryError());
        h[10] = keccak256(_bootstrapLinkageError());
        h[11] = keccak256(_bootstrapExceptionInInitializerError());
        h[12] = keccak256(_bootstrapIncompatibleClassChangeError());
        h[13] = keccak256(_bootstrapNoClassDefFoundError());
        h[14] = keccak256(_bootstrapAbstractMethodError());
        h[15] = keccak256(_bootstrapException());
        h[16] = keccak256(_bootstrapRuntimeException());
        h[17] = keccak256(_bootstrapArithmeticException());
        h[18] = keccak256(_bootstrapNullPointerException());
        h[19] = keccak256(_bootstrapNegativeArraySizeException());
        h[20] = keccak256(_bootstrapClassCastException());
        h[21] = keccak256(_bootstrapArrayStoreException());
        h[22] = keccak256(_bootstrapIndexOutOfBoundsException());
        h[23] = keccak256(_bootstrapArrayIndexOutOfBoundsException());
        h[24] = keccak256(_bootstrapComparable());
        h[25] = keccak256(_bootstrapCharSequence());
        h[26] = keccak256(_bootstrapString());
        h[27] = keccak256(_bootstrapIOException());
        h[28] = keccak256(_bootstrapFileNotFoundException());
        h[29] = keccak256(_bootstrapEOFException());
        h[30] = keccak256(_bootstrapAutoCloseable());
        h[31] = keccak256(_bootstrapCloseable());
        h[32] = keccak256(_bootstrapFlushable());
        h[33] = keccak256(_bootstrapFile());
        h[34] = keccak256(_bootstrapInputStream());
        h[35] = keccak256(_bootstrapOutputStream());
        h[36] = keccak256(_bootstrapFileInputStream());
        h[37] = keccak256(_bootstrapFileOutputStream());
        h[38] = keccak256(_bootstrapRunnable());
        h[39] = keccak256(_bootstrapClass());
        h[40] = keccak256(_bootstrapMap());
        h[41] = keccak256(_bootstrapConcurrentMap());
        h[42] = keccak256(_bootstrapAbstractMap());
        h[43] = keccak256(_bootstrapConcurrentHashMap());
        h[44] = keccak256(_bootstrapSystem());
        // Properties storage is a distinct appended bootstrap family.  The prior
        // forty-five image bytes and their root positions remain unchanged.
        h[45] = keccak256(_bootstrapDictionary());
        h[46] = keccak256(_bootstrapHashtable());
        h[47] = keccak256(_bootstrapProperties());
        return keccak256(abi.encode(DBOOT, h));
    }

    function _prepare(
        bytes[] calldata rawClasses, bytes memory wantedClass, bytes memory wantedMethod,
        int32[] memory args
    ) private pure returns (Program memory p) {
        uint256 inputCount = rawClasses.length;
        if (inputCount == 0 || inputCount > MAX_RAW_CLASSES) revert LinkError(1, inputCount);
        ClassInfo[] memory users = new ClassInfo[](inputCount);
        uint256 entryPlusOne;
        bool suppliedObject;
        bool suppliedCloneable;
        bool suppliedSerializable;
        bool suppliedFloat;
        bool suppliedDouble;
        bool suppliedRunnable;
        for (uint256 i; i < inputCount; ++i) {
            users[i] = _parseBundleClass(rawClasses[i]);
            if (_isReservedThrowableClass(users[i]) || _isReservedVFSClass(users[i])) {
                revert LinkError(6, i);
            }
            if (_isReservedStringProfileClass(users[i]) || _isReservedClassLiteralProfileClass(users[i])
                || _isReservedPlatformMapClass(users[i]) || _isReservedSystemClass(users[i])
                || _isReservedPropertiesClass(users[i])) {
                revert BootstrapProfileError(1, i);
            }
            for (uint256 j; j < i; ++j) if (_sameClassName(users[i], users[j])) {
                revert LinkError(2, i);
            }
            if (_isObjectClass(users[i])) suppliedObject = true;
            if (_isNamedClass(users[i], bytes("java/lang/Cloneable"))) suppliedCloneable = true;
            if (_isNamedClass(users[i], bytes("java/io/Serializable"))) suppliedSerializable = true;
            if (_isNamedClass(users[i], bytes("java/lang/Float"))) suppliedFloat = true;
            if (_isNamedClass(users[i], bytes("java/lang/Double"))) suppliedDouble = true;
            if (_isNamedClass(users[i], bytes("java/lang/Runnable"))) suppliedRunnable = true;
            if (_equals(users[i].data, users[i].thisNameOffset, users[i].thisNameLength,
                wantedClass)) entryPlusOne = i + 1;
        }
        if (entryPlusOne == 0) revert LinkError(3, 0);
        // Historical Runnable remains conditional. Class/map/System positions remain
        // fixed, then the three Properties-family images append after all forty-five.
        uint256 count = inputCount + 42 + (suppliedObject ? 0 : 1)
            + (suppliedCloneable ? 0 : 1) + (suppliedSerializable ? 0 : 1)
            + (suppliedFloat ? 0 : 1) + (suppliedDouble ? 0 : 1) + (suppliedRunnable ? 0 : 1);
        p.classes = new ClassInfo[](count);
        for (uint256 i; i < inputCount; ++i) p.classes[i] = users[i];
        uint256 at = inputCount;
        if (!suppliedObject) p.classes[at++] = _parseBundleClass(_bootstrapObject());
        if (!suppliedCloneable) p.classes[at++] = _parseBundleClass(_bootstrapCloneable());
        if (!suppliedSerializable) p.classes[at++] = _parseBundleClass(_bootstrapSerializable());
        if (!suppliedFloat) p.classes[at++] = _parseBundleClass(_bootstrapFloat());
        if (!suppliedDouble) p.classes[at++] = _parseBundleClass(_bootstrapDouble());
        p.throwableBootstrapAt = at;
        _appendThrowableBootstraps(p.classes, at);
        _appendStringBootstraps(p.classes, at + 19);
        _appendIOBootstraps(p.classes, at + 22);
        _appendVFSBootstraps(p.classes, at + 25);
        // Keep all historical bootstrap indexes fixed.  Runnable is conditional,
        // so derive Class's actual appended slot instead of assuming +34.
        uint256 classSlot = at + (suppliedRunnable ? 33 : 34);
        if (!suppliedRunnable) p.classes[at + 33].data = _bootstrapRunnable();
        p.classes[classSlot].data = _bootstrapClass();
        p.classes[classSlot + 1].data = _bootstrapMap();
        p.classes[classSlot + 2].data = _bootstrapConcurrentMap();
        p.classes[classSlot + 3].data = _bootstrapAbstractMap();
        p.classes[classSlot + 4].data = _bootstrapConcurrentHashMap();
        p.classes[classSlot + 5].data = _bootstrapSystem();
        // Do not interleave this new family with the pinned historical tail.
        p.classes[classSlot + 6].data = _bootstrapDictionary();
        p.classes[classSlot + 7].data = _bootstrapHashtable();
        p.classes[classSlot + 8].data = _bootstrapProperties();
        p.classClass = classSlot;
        p.rootClass = entryPlusOne - 1;
        _requireSupportedClass(p.classes[p.rootClass], p.rootClass);
        // MR0 has exactly one permitted root signature.  Select it before
        // applying root access/Code checks so valid overloads neither mask nor
        // duplicate the exact main(String[]) target.
        bytes memory wantedDescriptor = bytes("([Ljava/lang/String;)V");
        uint256 rootPlusOne;
        for (uint256 m; m < p.classes[p.rootClass].methods.length; ++m) {
            uint256 meta = p.classes[p.rootClass].methods[m];
            (uint256 no, uint256 nn) = _utf(p.classes[p.rootClass].cp[(meta >> 16) & 0xffff]);
            (uint256 doff, uint256 dn) = _utf(p.classes[p.rootClass].cp[(meta >> 32) & 0xffff]);
            if (_equals(p.classes[p.rootClass].data, no, nn, wantedMethod)
                && _equals(p.classes[p.rootClass].data, doff, dn, wantedDescriptor)) {
                if (rootPlusOne != 0) revert MethodError(2);
                rootPlusOne = m + 1;
            }
        }
        if (rootPlusOne == 0) revert MethodError(1);
        p.rootMethod = rootPlusOne - 1;
        uint256 rootMeta = p.classes[p.rootClass].methods[p.rootMethod];
        uint16 access = uint16(rootMeta);
        if ((access & (0x0001 | 0x0008)) != (0x0001 | 0x0008)) revert MethodError(6);
        if ((access & (0x0020 | 0x0100 | 0x0400)) != 0) revert MethodError(7);
        if (_methodCodeCount(rootMeta) != 1) revert MethodError(_methodCodeCount(rootMeta) == 0 ? 4 : 3);
        p.selected = new Selected[][][](count);
        p.referenceCaches = new uint256[][](count);
        p.fieldCaches = new uint256[][](count);
        p.selected[p.rootClass] = new Selected[][](p.classes[p.rootClass].methods.length);
        p.referenceCaches[p.rootClass] = new uint256[](p.classes[p.rootClass].cp.length);
        p.fieldCaches[p.rootClass] = new uint256[](p.classes[p.rootClass].cp.length);
        Selected memory rootSelection = _loadRoot(
            p.classes[p.rootClass], rootMeta, p.rootClass, p.rootMethod
        );
        // Preserve MR0's exact String[] root checks before predecode: malformed Code
        // must not outrank a wrong canonical root argument shape.
        if (args.length != 0 || !_isMainEmptyStringArrayRoot(p.classes[p.rootClass], rootSelection)) revert MethodError(9);
        if (rootSelection.maxLocals < 1) revert MethodError(10);
        p.mainRoot = true;
        _predecode(p.classes[p.rootClass], rootSelection);
        _putSelection(p.selected, p.rootClass, p.rootMethod, rootSelection);
    }

    function _freshState(Program memory p, int32[] memory args, bool installMainRoot)
        private pure returns (RuntimeState memory s)
    {
        uint256 n = p.classes.length;
        s.lifecycle = 1;
        s.frames = new Frame[](MAX_FRAMES);
        s.frames[0] = _newFrame(
            p.rootClass, p.rootMethod, p.selected[p.rootClass][p.rootMethod][0], 0
        );
        s.frames[0].callPC = ROOT_FAULT_SENTINEL;
        for (uint256 i; i < args.length; ++i) {
            s.frames[0].locals[i] = _packInt(uint32(args[i]));
            s.frames[0].initialized[i] = true;
        }
        s.depth = 1;
        s.initializationState = new uint8[](n);
        s.initializerStarted = new bool[](n);
        s.staticValues = new uint256[][](n);
        s.parentLinks = new uint256[](n);
        s.hierarchyState = new uint8[](n);
        for (uint256 i; i < n; ++i) {
            if (p.classes[i].cp.length == 0) p.classes[i] = _parseBundleClass(p.classes[i].data);
            s.staticValues[i] = new uint256[](p.classes[i].fields.length);
            for (uint256 j; j < p.classes[i].fields.length; ++j) {
                uint8 k = _fieldKind(p.classes[i], p.classes[i].fields[j]);
                s.staticValues[i][j] = k == KIND_INT ? _packInt(0)
                    : (k == KIND_REF ? _packRef(0) : (k == KIND_LONG ? _packLong(0)
                    : (k == KIND_FLOAT ? _packFloat(0) : _packDouble(0))));
            }
        }
        _validateHierarchy(p.classes, p.rootClass, s.parentLinks, s.hierarchyState);
        s.arena.classesByKind = new uint256[](13);
        s.arena.stringRefs = new uint256[][](n);
        _configureExceptionClasses(s.arena, p.throwableBootstrapAt);
        s.arena.stringClass = p.throwableBootstrapAt + 21;
        s.arena.classClass = p.classClass;
        if (installMainRoot) {
            _installEmptyMainStringArray(p, s);
            // The non-null, rank-one, empty String[] is an initial-input
            // invariant. Validate the canonical allocation before guest code can
            // execute, not on later checkpoints where local0 is ordinary mutable
            // Java storage.
            _validateInitialMainRoot(p, s);
        }
    }

    function _installEmptyMainStringArray(Program memory p, RuntimeState memory s) private pure {
        _ensureExceptionRegistry(s.arena, p.classes, s.parentLinks, s.hierarchyState);
        if (s.arena.ordinaryArrayCount >= MAX_ARRAYS || s.nextHandle >= MAX_HANDLES) revert ObjectError(2, ROOT_FAULT_SENTINEL);
        if (s.arena.heap.arrayHeap.length == 0) {
            s.arena.heap.arrayHeap = new uint64[][](MAX_HANDLES + 1);
            s.arena.heap.ranks = new uint8[](MAX_HANDLES + 1);
        }
        uint256 h = s.arena.nextHandle + 1;
        s.arena.nextHandle = h; s.nextHandle = h;
        ++s.arena.ordinaryArrayCount;
        s.arena.heap.ranks[h] = 1;
        s.arena.heap.metadata[h] = ARRAY_CLASS_BASE + s.arena.stringClass;
        s.arena.heap.arrayHeap[h] = new uint64[](0);
        s.frames[0].locals[0] = _packRef(uint32(h));
        s.frames[0].initialized[0] = true;
    }

    function _commit(
        bytes32 instanceId, uint64 epoch, bytes32 parentRoot, bytes32 runtimeHash,
        bytes32 artifact, bytes32 config, bytes memory entryClass, bytes memory entry,
        int32[] memory args, Program memory p, RuntimeState memory s,
        uint64 executedJvm, uint32 executedInternal
    ) private returns (MR0MainSliceResult memory out, bytes memory checkpoint) {
        if (gasleft() <= COMMIT_RESERVE) revert LC0ControlError(7);
        _validateRestoredReferences(p, s);
        _validateClassMirrors(p, s);
        _validateInitAndFrames(p, s, false);
        _validateVFSHeap(p, s);
        bytes memory machine = _encodeMachine(p, s, entryClass, entry, args);
        bytes32 vfsRoot = _vfsRoot(s.vfs);
        bytes32 machineRoot = keccak256(abi.encode(
            DMACH, MR0_SCHEMA, artifact, config, keccak256(machine), vfsRoot
        ));
        checkpoint = _encodeEnvelope(
            instanceId, epoch, parentRoot, runtimeHash, artifact, config, machineRoot,
            s.vfs.seedRoot, vfsRoot, machine
        );
        if (checkpoint.length > MAX_CHECKPOINT_BYTES) revert LC0StateError(1, 0);
        bytes32 checkpointRoot = keccak256(checkpoint);
        uint8 javaKind = s.lifecycle == 3 ? uint8(s.arena.pending.kind) : 0;
        uint32 javaRef = s.lifecycle == 3 ? uint32(s.arena.pending.ref) : 0;
        bytes memory javaClass;
        if (s.lifecycle == 3 && javaKind == 0) {
            javaClass = _classNameBytes(p.classes[s.arena.heap.classes[javaRef]]);
        }
        uint8 outcome = s.lifecycle == 1 ? 1 : (s.lifecycle == 2 ? 2 : 3);
        out = MR0MainSliceResult(
            MR0_SCHEMA, s.lifecycle, outcome, epoch, checkpointRoot, machineRoot,
            s.totalJvmSteps, s.totalInternalSteps, executedJvm, executedInternal,
            s.lifecycle == 2 ? s.result : int32(0), javaKind, javaRef, javaClass,
            vfsRoot, uint32(s.vfs.inodes.length), uint32(s.vfs.descriptors.length),
            s.vfs.logicalFileBytes
        );
        anchors[instanceId] = Anchor(
            msg.sender, epoch, checkpointRoot, machineRoot, vfsRoot, s.vfs.seedRoot,
            artifact, config, runtimeHash, s.lifecycle
        );
        emit CheckpointCommitted(
            instanceId, epoch, checkpointRoot, machineRoot, vfsRoot, s.lifecycle,
            s.totalJvmSteps, s.totalInternalSteps
        );
    }

    function _encodeEnvelope(
        bytes32 instanceId, uint64 epoch, bytes32 parentRoot, bytes32 runtimeHash,
        bytes32 artifact, bytes32 config, bytes32 machineRoot, bytes32 seedRoot,
        bytes32 vfsRoot, bytes memory machine
    ) private pure returns (bytes memory out) {
        out = new bytes(CHECKPOINT_HEADER_BYTES + machine.length);
        uint256 at;
        at = _put(out, at, uint64(bytes8("JVMVF0A1")), 8);
        at = _put(out, at, MR0_SCHEMA, 4);
        at = _put(out, at, uint256(instanceId), 32);
        at = _put(out, at, epoch, 8);
        at = _put(out, at, uint256(parentRoot), 32);
        at = _put(out, at, uint256(runtimeHash), 32);
        at = _put(out, at, uint256(artifact), 32);
        at = _put(out, at, uint256(config), 32);
        at = _put(out, at, uint256(machineRoot), 32);
        at = _put(out, at, uint256(seedRoot), 32);
        at = _put(out, at, uint256(vfsRoot), 32);
        at = _put(out, at, machine.length, 4);
        assembly ("memory-safe") {
            mcopy(add(add(out, 32), at), add(machine, 32), mload(machine))
        }
    }

    function _decodeEnvelope(bytes calldata checkpoint)
        private pure returns (Envelope memory e)
    {
        if (checkpoint.length < CHECKPOINT_HEADER_BYTES || checkpoint.length > MAX_CHECKPOINT_BYTES) {
            revert LC0StateError(1, 0);
        }
        bytes memory b = checkpoint;
        uint256 at;
        (uint256 v, uint256 n) = _get(b, at, 8, 0); at = n;
        if (v != uint64(bytes8("JVMVF0A1"))) revert LC0StateError(3, 0);
        (v, at) = _get(b, at, 4, 0);
        if (v != MR0_SCHEMA) revert LC0StateError(3, 8);
        (v, at) = _get(b, at, 32, 0); e.instanceId = bytes32(v);
        (v, at) = _get(b, at, 8, 0); e.epoch = uint64(v);
        (v, at) = _get(b, at, 32, 0); e.parentCheckpointRoot = bytes32(v);
        (v, at) = _get(b, at, 32, 0); e.runtimeCodeHash = bytes32(v);
        (v, at) = _get(b, at, 32, 0); e.artifactRoot = bytes32(v);
        (v, at) = _get(b, at, 32, 0); e.configRoot = bytes32(v);
        (v, at) = _get(b, at, 32, 0); e.machineStateRoot = bytes32(v);
        (v, at) = _get(b, at, 32, 0); e.seedRoot = bytes32(v);
        (v, at) = _get(b, at, 32, 0); e.vfsStateRoot = bytes32(v);
        (v, at) = _get(b, at, 4, 0);
        if (v != b.length - CHECKPOINT_HEADER_BYTES) revert LC0StateError(2, at - 4);
        e.machineBytes = new bytes(v);
        bytes memory machine = e.machineBytes;
        assembly ("memory-safe") { mcopy(add(machine, 32), add(add(b, 32), at), v) }
        bytes32 computed = keccak256(abi.encode(
            DMACH, MR0_SCHEMA, e.artifactRoot, e.configRoot,
            keccak256(e.machineBytes), e.vfsStateRoot
        ));
        if (computed != e.machineStateRoot) revert LC0StateError(3, 180);
    }

    function _machineSize(
        Program memory p, RuntimeState memory s, bytes memory ec, bytes memory en,
        int32[] memory args
    ) private pure returns (uint256 z) {
        z = 63 + 2 + ec.length + 2 + en.length + 1 + 4 * args.length + 2;
        for (uint256 i; i < p.classes.length; ++i) {
            uint256 statics;
            for (uint256 j; j < p.classes[i].fields.length; ++j) {
                if ((p.classes[i].fields[j].accessFlags & 0x0008) != 0) ++statics;
            }
            z += 4 + 34 * statics;
        }
        z += 2;
        for (uint256 i; i < s.depth; ++i) {
            Frame memory f = s.frames[i];
            z += 49 + 32 * f.sp + (f.locals.length + 7) / 8 + 32 * f.locals.length;
        }
        z += 26;
        for (uint256 h = 1; h <= s.nextHandle; ++h) {
            uint8 k = _heapKindAt(s.arena.heap.metadata[h]);
            uint256 count = k == HEAP_ARRAY ? s.arena.heap.arrayHeap[h].length
                : s.arena.heap.objectHeap[h].length;
            z += 43 + count * (k == HEAP_ARRAY ? 8 : 32);
        }
        z += 38 + 2 + 8 * s.arena.internCount;
        z += _vfsEncodedSize(s.vfs);
    }

    function _encodeMachine(
        Program memory p, RuntimeState memory s, bytes memory ec, bytes memory en,
        int32[] memory args
    ) private pure returns (bytes memory out) {
        if (ec.length == 0 || ec.length > 256 || en.length == 0 || en.length > 256
            || args.length > 8) revert LC0StateError(4, 0);
        uint256 size = _machineSize(p, s, ec, en, args);
        if (size + CHECKPOINT_HEADER_BYTES > MAX_CHECKPOINT_BYTES) revert LC0StateError(1, 0);
        out = new bytes(size);
        uint256 at;
        at = _put(out, at, uint32(bytes4("MR01")), 4);
        at = _put(out, at, s.lifecycle, 1);
        at = _put(out, at, uint32(s.lifecycle == 2 ? s.result : int32(0)), 4);
        at = _put(out, at, s.lifecycle == 3 ? s.arena.pending.kind : 0, 1);
        at = _put(out, at, s.lifecycle == 3 ? s.arena.pending.ref : 0, 4);
        at = _put(out, at, s.totalJvmSteps, 8);
        at = _put(out, at, s.totalInternalSteps, 8);
        at = _put(out, at, ROOT_KIND_MAIN_EMPTY_STRING_ARRAY, 1);
        at = _put(out, at, uint256(EMPTY_ARGS_COMMITMENT), 32);
        at = _putBytes16(out, at, ec);
        at = _putBytes16(out, at, en);
        at = _put(out, at, args.length, 1);
        for (uint256 i; i < args.length; ++i) at = _put(out, at, uint32(args[i]), 4);
        at = _put(out, at, p.classes.length, 2);
        for (uint256 i; i < p.classes.length; ++i) {
            at = _put(out, at, s.initializationState[i], 1);
            at = _put(out, at, s.initializerStarted[i] ? 1 : 0, 1);
            uint256 countAt = at; at += 2;
            uint256 count;
            for (uint256 j; j < p.classes[i].fields.length; ++j) {
                if ((p.classes[i].fields[j].accessFlags & 0x0008) == 0) continue;
                at = _put(out, at, j, 2);
                at = _put(out, at, s.staticValues[i][j], 32);
                ++count;
            }
            _put(out, countAt, count, 2);
        }
        at = _put(out, at, s.depth, 2);
        for (uint256 i; i < s.depth; ++i) {
            Frame memory f = s.frames[i];
            at = _put(out, at, f.classIndex, 2);
            at = _put(out, at, f.methodIndex, 2);
            at = _put(out, at, f.pc, 4);
            at = _put(out, at, f.callPC, 32);
            uint8 flags = (f.isInitializer ? 1 : 0) | (f.isInitContinuation ? 2 : 0)
                | (f.isConstructor ? 4 : 0) | (f.isConstructorLinked ? 8 : 0)
                | (f.entered ? 16 : 0);
            at = _put(out, at, flags, 1);
            at = _put(out, at, f.thisHandle, 4);
            at = _put(out, at, f.sp, 2);
            for (uint256 j; j < f.sp; ++j) at = _put(out, at, f.stack[j], 32);
            at = _put(out, at, f.locals.length, 2);
            uint256 bitmapAt = at;
            at += (f.locals.length + 7) / 8;
            for (uint256 j; j < f.locals.length; ++j) {
                if (f.initialized[j]) out[bitmapAt + j / 8] |= bytes1(uint8(1 << (j & 7)));
                at = _put(out, at, f.initialized[j] ? f.locals[j] : 0, 32);
            }
        }
        ExceptionArena memory a = s.arena;
        at = _put(out, at, s.nextHandle, 4);
        at = _put(out, at, a.ordinaryObjectCount, 2);
        at = _put(out, at, a.ordinaryArrayCount, 2);
        at = _put(out, at, a.ordinaryArrayElements, 4);
        at = _put(out, at, a.ordinaryFieldSlots, 4);
        at = _put(out, at, a.emergencyRef, 4);
        at = _put(out, at, a.objectCount, 2);
        at = _put(out, at, a.fieldSlots, 4);
        for (uint256 h = 1; h <= s.nextHandle; ++h) {
            uint256 meta = a.heap.metadata[h];
            uint8 k = _heapKindAt(meta);
            if (k == 0) revert LC0StateError(6, 0);
            at = _put(out, at, h, 4);
            at = _put(out, at, meta, 32);
            at = _put(out, at, a.heap.classes[h], 2);
            at = _put(out, at, a.heap.ranks.length == 0 ? 0 : a.heap.ranks[h], 1);
            uint256 count = k == HEAP_ARRAY ? a.heap.arrayHeap[h].length : a.heap.objectHeap[h].length;
            at = _put(out, at, count, 4);
            if (k == HEAP_ARRAY) for (uint256 j; j < count; ++j) {
                at = _put(out, at, a.heap.arrayHeap[h][j], 8);
            } else for (uint256 j; j < count; ++j) at = _put(out, at, a.heap.objectHeap[h][j], 32);
        }
        at = _put(out, at, a.pending.active ? 1 : 0, 1);
        at = _put(out, at, a.pending.active ? a.pending.kind : 0, 1);
        at = _put(out, at, a.pending.active ? a.pending.ref : 0, 4);
        at = _put(out, at, a.pending.active ? a.pending.faultPC : 0, 32);
        at = _put(out, at, a.internCount, 2);
        for (uint256 i; i < a.internCount; ++i) {
            at = _put(out, at, a.internHandles[i], 4);
            at = _put(out, at, a.internHashes[i], 4);
        }
        bytes memory vfsSection = _encodeVFS(s.vfs);
        assembly ("memory-safe") {
            mcopy(add(add(out, 32), at), add(vfsSection, 32), mload(vfsSection))
        }
        at += vfsSection.length;
        assert(at == out.length);
    }

    function _vfsEncodedSize(VFSState memory fs) private pure returns (uint256 z) {
        z = 24 + fs.descriptors.length * 28;
        for (uint256 i; i < fs.inodes.length; ++i) {
            z += 15 + fs.inodes[i].name.length + fs.inodes[i].data.length;
        }
    }

    function _vfsRoot(VFSState memory fs) private pure returns (bytes32) {
        if (fs.nextInode == type(uint32).max) return _vfsRoot(fs);
        bytes memory section = _encodeVFS(fs);
        return keccak256(abi.encode(DVFS, uint32(1), fs.seedRoot, keccak256(section)));
    }

    function _initialVFS(SeedFile[] calldata seeds, bytes32 seedRoot)
        private pure returns (VFSState memory fs)
    {
        if (seeds.length > MAX_SEEDS) revert VFS0aQuotaError(1, seeds.length, MAX_SEEDS);
        fs.seedRoot = seedRoot;
        fs.nextInode = 4;
        fs.nextDescriptor = 1;
        fs.inodes = new VFSInode[](3);
        fs.descriptors = new VFSDescriptor[](0);
        fs.inodes[0] = VFSInode(1, 1, false, 0, bytes(""), bytes(""));
        fs.inodes[1] = VFSInode(2, 1, false, 1, bytes("work"), bytes(""));
        fs.inodes[2] = VFSInode(3, 1, true, 1, bytes("ro"), bytes(""));
        uint256 seedBytes;
        for (uint256 i; i < seeds.length; ++i) {
            seedBytes += seeds[i].data.length;
            if (seedBytes > MAX_SEED_BYTES) {
                revert VFS0aQuotaError(1, seedBytes, MAX_SEED_BYTES);
            }
            if (seeds[i].path.length > 256) revert VFS0aProfileError(1, 0);
            bytes memory canonical = _canonicalPath(_lexicalPath(seeds[i].path, 0), 0);
            _seedFile(fs, canonical, seeds[i].data, seeds[i].readOnly);
        }
        _validateVFS(fs, 0);
    }

    function _seedFile(VFSState memory fs, bytes memory canonical, bytes calldata data, bool ro)
        private pure
    {
        if (data.length > 65536) revert VFS0aQuotaError(4, data.length, 65536);
        (bytes[] memory comps, uint256 count) = _pathComponents(canonical);
        if (count == 0) revert VFS0aProfileError(1, 0);
        uint32 parent = 1;
        for (uint256 i; i + 1 < count; ++i) {
            uint32 child = _findChild(fs, parent, comps[i]);
            if (child == 0) child = _addInode(fs, 1, false, parent, comps[i], bytes(""));
            if (fs.inodes[child - 1].kind != 1) revert VFS0aProfileError(1, 0);
            parent = child;
        }
        if (_findChild(fs, parent, comps[count - 1]) != 0) revert VFS0aProfileError(1, 0);
        bytes memory copied = data;
        _addInode(fs, 2, ro, parent, comps[count - 1], copied);
        fs.logicalFileBytes += uint64(data.length);
        if (fs.logicalFileBytes > 65536) {
            revert VFS0aQuotaError(5, fs.logicalFileBytes, 65536);
        }
    }

    function _lexicalPath(bytes memory raw, uint256 pc) private pure returns (bytes memory out) {
        if (pc == type(uint256).max) return _lexicalPath(raw, pc);
        if (raw.length == 0 || raw.length > 256) revert VFS0aProfileError(1, pc);
        out = new bytes(raw.length);
        uint256 n;
        bool slash;
        for (uint256 i; i < raw.length; ++i) {
            uint8 c = uint8(raw[i]);
            if (c < 0x20 || c > 0x7e) revert VFS0aProfileError(1, pc);
            if (c == 0x2f) {
                if (slash) continue;
                slash = true;
            } else slash = false;
            out[n++] = raw[i];
        }
        if (n > 1 && out[n - 1] == 0x2f) --n;
        assembly ("memory-safe") { mstore(out, n) }
    }

    function _canonicalPath(bytes memory lexical, uint256 pc)
        private pure returns (bytes memory out)
    {
        if (pc == type(uint256).max) return _canonicalPath(lexical, pc);
        bytes[] memory stack = new bytes[](16);
        uint256 depth;
        bool absolute = lexical.length != 0 && lexical[0] == 0x2f;
        if (!absolute) stack[depth++] = bytes("work");
        uint256 i = absolute ? 1 : 0;
        while (i <= lexical.length) {
            uint256 j = i;
            while (j < lexical.length && lexical[j] != 0x2f) ++j;
            uint256 len = j - i;
            if (len > 64) revert VFS0aProfileError(1, pc);
            if (len == 1 && lexical[i] == 0x2e) {
            } else if (len == 2 && lexical[i] == 0x2e && lexical[i + 1] == 0x2e) {
                if (depth == 0) revert VFS0aProfileError(1, pc);
                --depth;
            } else if (len != 0) {
                if (depth == 16) revert VFS0aProfileError(1, pc);
                bytes memory component = new bytes(len == 0 ? 1 : len);
                for (uint256 k; k < len; ++k) component[k] = lexical[i + k];
                stack[depth++] = component;
            }
            if (j == lexical.length) break;
            i = j + 1;
        }
        uint256 size = 1;
        for (uint256 k; k < depth; ++k) size += stack[k].length + (k == 0 ? 0 : 1);
        if (size > 256) revert VFS0aProfileError(1, pc);
        out = new bytes(size);
        out[0] = 0x2f;
        uint256 at = 1;
        for (uint256 k; k < depth; ++k) {
            if (k != 0) out[at++] = 0x2f;
            for (uint256 q; q < stack[k].length; ++q) out[at++] = stack[k][q];
        }
    }

    function _pathComponents(bytes memory canonical)
        private pure returns (bytes[] memory comps, uint256 count)
    {
        if (canonical.length > 256) return _pathComponents(canonical);
        comps = new bytes[](16);
        uint256 i = 1;
        while (i < canonical.length) {
            uint256 j = i;
            while (j < canonical.length && canonical[j] != 0x2f) ++j;
            bytes memory c = new bytes(j - i);
            for (uint256 k; k < c.length; ++k) c[k] = canonical[i + k];
            comps[count++] = c;
            i = j + 1;
        }
    }

    function _bytesEqual(bytes memory a, bytes memory b) private pure returns (bool) {
        if (a.length != b.length) return false;
        for (uint256 i; i < a.length; ++i) if (a[i] != b[i]) return false;
        return true;
    }

    function _findChild(VFSState memory fs, uint32 parent, bytes memory name)
        private pure returns (uint32)
    {
        if (parent == type(uint32).max) return _findChild(fs, parent, name);
        for (uint256 i; i < fs.inodes.length; ++i) {
            if (fs.inodes[i].parent == parent && _bytesEqual(fs.inodes[i].name, name)) {
                return fs.inodes[i].id;
            }
        }
        return 0;
    }

    function _lookupPath(VFSState memory fs, bytes memory canonical) private pure returns (uint32 id) {
        if (canonical.length > 256) return _lookupPath(fs, canonical);
        (bytes[] memory comps, uint256 count) = _pathComponents(canonical);
        id = 1;
        for (uint256 i; i < count; ++i) {
            id = _findChild(fs, id, comps[i]);
            if (id == 0) return 0;
        }
    }

    // Walk the normalized lexical spelling in operation order, before dot-dot can
    // erase a failed intermediate lookup. failure=1 is ENOENT and failure=2 is
    // ENOTDIR. A missing final ordinary component also reports the parent/name so
    // mkdir or output-open can create it without repeating a canonicalized walk.
    function _walkVFSPath(VFSState memory fs, bytes memory lexical)
        private pure returns (uint32 id, uint32 createParent, bytes memory leaf, uint8 failure)
    {
        bool absolute = lexical[0] == 0x2f;
        id = absolute ? 1 : 2;
        uint256 i = absolute ? 1 : 0;
        while (i <= lexical.length) {
            uint256 j = i;
            while (j < lexical.length && lexical[j] != 0x2f) ++j;
            uint256 len = j - i;
            if (len != 0) {
                if (fs.inodes[id - 1].kind != 1) return (0, 0, bytes(""), 2);
                if (len == 1 && lexical[i] == 0x2e) {
                    // The current component must still be a directory; checked above.
                } else if (len == 2 && lexical[i] == 0x2e && lexical[i + 1] == 0x2e) {
                    id = fs.inodes[id - 1].parent;
                    // _canonicalPath has already rejected lexical root escape.
                    if (id == 0) return (0, 0, bytes(""), 1);
                } else {
                    bytes memory component = new bytes(len);
                    for (uint256 k; k < len; ++k) component[k] = lexical[i + k];
                    uint32 child = _findChild(fs, id, component);
                    if (child == 0) {
                        if (j == lexical.length) return (0, id, component, 1);
                        return (0, 0, bytes(""), 1);
                    }
                    id = child;
                }
            }
            if (j == lexical.length) break;
            i = j + 1;
        }
    }

    function _effectiveReadOnly(VFSState memory fs, uint32 id) private pure returns (bool) {
        if (id == type(uint32).max) return _effectiveReadOnly(fs, id);
        while (id != 0) {
            VFSInode memory n = fs.inodes[id - 1];
            if (n.readOnly) return true;
            id = n.parent;
        }
        return false;
    }

    function _addInode(
        VFSState memory fs, uint8 kind, bool ro, uint32 parent, bytes memory name, bytes memory data
    ) private pure returns (uint32 id) {
        if (parent == type(uint32).max) return _addInode(fs, kind, ro, parent, name, data);
        if (fs.inodes.length >= MAX_VFS_INODES) {
            revert VFS0aQuotaError(2, fs.inodes.length + 1, MAX_VFS_INODES);
        }
        if (name.length == 0 || name.length > 64 || parent == 0
            || _findChild(fs, parent, name) != 0) revert VFS0aProfileError(1, 0);
        id = fs.nextInode++;
        VFSInode[] memory next = new VFSInode[](fs.inodes.length + 1);
        for (uint256 i; i < fs.inodes.length; ++i) next[i] = fs.inodes[i];
        next[fs.inodes.length] = VFSInode(id, kind, ro, parent, name, data);
        fs.inodes = next;
    }

    function _mkdirVFS(VFSState memory fs, bytes memory lexical, bool recursive)
        private pure returns (bool)
    {
        if (!recursive) {
            (uint32 existing, uint32 createParent, bytes memory leaf, uint8 failure) =
                _walkVFSPath(fs, lexical);
            if (existing != 0 || failure != 1 || createParent == 0
                || _effectiveReadOnly(fs, createParent)) return false;
            _addInode(fs, 1, false, createParent, leaf, bytes(""));
            return true;
        }

        // File.mkdirs has a measured Java8/21 canonical fallback unlike mkdir,
        // stat and open. Preserve that operation-specific behavior.
        bytes memory canonical = _canonicalPath(lexical, 0);
        (bytes[] memory comps, uint256 count) = _pathComponents(canonical);
        if (count == 0) return false;
        uint32 parent = 1;
        for (uint256 i; i < count; ++i) {
            uint32 child = _findChild(fs, parent, comps[i]);
            if (child != 0) {
                if (fs.inodes[child - 1].kind != 1) return false;
                parent = child;
                if (i + 1 == count) return false;
                continue;
            }
            if (_effectiveReadOnly(fs, parent)) return false;
            parent = _addInode(fs, 1, false, parent, comps[i], bytes(""));
        }
        return true;
    }

    function _pendingDescriptorCount(VFSState memory fs) private pure returns (uint256 count) {
        for (uint256 i; i < fs.descriptors.length; ++i) {
            if (fs.descriptors[i].phase == 1) ++count;
        }
    }

    function _openVFS(
        VFSState memory fs, bytes memory lexical, uint32 owner, uint16 depth,
        uint32 bindPC, uint256 pc, bool reading, bool append
    ) private pure returns (int32) {
        if (owner == 0 || depth == 0 || _pendingDescriptorCount(fs) != 0) {
            revert VFS0aProfileError(4, pc);
        }
        (uint32 inode, uint32 parent, bytes memory leaf, uint8 failure) =
            _walkVFSPath(fs, lexical);
        if (reading) {
            if (failure == 2) return -4;
            if (inode == 0) return -1;
            if (fs.inodes[inode - 1].kind != 2) return -2;
        } else if (inode != 0) {
            if (fs.inodes[inode - 1].kind != 2) return -2;
            if (_effectiveReadOnly(fs, inode)) return -3;
        } else {
            if (failure == 2) return -4;
            if (parent == 0) return -1;
            if (_effectiveReadOnly(fs, parent)) return -3;
            inode = _addInode(fs, 2, false, parent, leaf, bytes(""));
        }
        if (fs.descriptors.length >= MAX_VFS_DESCRIPTORS) {
            revert VFS0aQuotaError(3, fs.descriptors.length + 1, MAX_VFS_DESCRIPTORS);
        }
        if (!reading && !append) {
            fs.logicalFileBytes -= uint64(fs.inodes[inode - 1].data.length);
            fs.inodes[inode - 1].data = bytes("");
        }
        uint8 flags = reading ? 1 : uint8(2 | (append ? 4 : 0));
        uint64 cursor = append ? uint64(fs.inodes[inode - 1].data.length) : 0;
        uint32 id = fs.nextDescriptor++;
        VFSDescriptor[] memory next = new VFSDescriptor[](fs.descriptors.length + 1);
        for (uint256 i; i < fs.descriptors.length; ++i) next[i] = fs.descriptors[i];
        next[fs.descriptors.length] = VFSDescriptor(
            id, inode, owner, flags, cursor, 1, depth, bindPC
        );
        fs.descriptors = next;
        return int32(id);
    }

    function _descriptor(VFSState memory fs, uint32 id, uint256 pc)
        private pure returns (VFSDescriptor memory)
    {
        if (pc == type(uint256).max) return _descriptor(fs, id, pc);
        if (id == 0 || id > fs.descriptors.length) revert VFS0aProfileError(4, pc);
        return fs.descriptors[id - 1];
    }

    function _descriptorForOwner(VFSState memory fs, uint32 owner, uint256 pc)
        private pure returns (uint32 id)
    {
        for (uint256 i; i < fs.descriptors.length; ++i) {
            if (fs.descriptors[i].ownerRef == owner) {
                if (id != 0) revert VFS0aStateError(4, 0);
                id = uint32(i + 1);
            }
        }
        if (id == 0) revert VFS0aProfileError(4, pc);
    }

    function _bindDescriptor(
        VFSState memory fs, uint32 id, uint32 owner, uint16 depth, uint32 bindPC,
        uint256 putfieldPC
    ) private pure {
        VFSDescriptor memory d = _descriptor(fs, id, putfieldPC);
        if (d.phase != 1 || d.ownerRef != owner || d.bindDepth != depth
            || d.bindPC != bindPC || bindPC != putfieldPC) {
            revert VFS0aProfileError(4, putfieldPC);
        }
        fs.descriptors[id - 1].phase = 2;
        fs.descriptors[id - 1].bindDepth = 0;
        fs.descriptors[id - 1].bindPC = 0;
    }

    function _readVFS(VFSState memory fs, uint32 id, uint32 len, uint256 pc)
        private pure returns (int32 status, bytes memory data)
    {
        if (len > 4096) revert VFS0aProfileError(3, pc);
        VFSDescriptor memory d = _descriptor(fs, id, pc);
        if (d.phase == 3) return (-2, bytes(""));
        if (d.phase != 2 || d.flags != 1) revert VFS0aProfileError(2, pc);
        bytes memory source = fs.inodes[d.inode - 1].data;
        if (d.cursor >= source.length) return (-1, bytes(""));
        uint256 count = source.length - uint256(d.cursor);
        if (count > len) count = len;
        data = new bytes(count);
        for (uint256 i; i < count; ++i) data[i] = source[uint256(d.cursor) + i];
        fs.descriptors[id - 1].cursor += uint64(count);
        return (int32(uint32(count)), data);
    }

    function _writeVFS(VFSState memory fs, uint32 id, bytes memory data, uint256 pc)
        private pure returns (int32)
    {
        if (data.length > 4096) revert VFS0aProfileError(3, pc);
        VFSDescriptor memory d = _descriptor(fs, id, pc);
        if (d.phase == 3) return -2;
        if (d.phase != 2 || (d.flags & 2) == 0) revert VFS0aProfileError(2, pc);
        VFSInode memory n = fs.inodes[d.inode - 1];
        uint256 at = (d.flags & 4) != 0 ? n.data.length : uint256(d.cursor);
        uint256 end = at + data.length;
        if (end > 65536) revert VFS0aQuotaError(4, end, 65536);
        uint256 newLength = end > n.data.length ? end : n.data.length;
        uint256 total = uint256(fs.logicalFileBytes) - n.data.length + newLength;
        if (total > 65536) revert VFS0aQuotaError(5, total, 65536);
        bytes memory next = new bytes(newLength);
        for (uint256 i; i < n.data.length; ++i) next[i] = n.data[i];
        for (uint256 i; i < data.length; ++i) next[at + i] = data[i];
        fs.inodes[d.inode - 1].data = next;
        fs.logicalFileBytes = uint64(total);
        fs.descriptors[id - 1].cursor = uint64(end);
        return 0;
    }

    function _closeVFS(VFSState memory fs, uint32 id, uint256 pc) private pure returns (int32) {
        VFSDescriptor memory d = _descriptor(fs, id, pc);
        if (d.phase == 1) revert VFS0aProfileError(4, pc);
        fs.descriptors[id - 1].phase = 3;
        return 0;
    }

    function _inodePath(VFSState memory fs, uint32 id) private pure returns (bytes memory out) {
        if (id == type(uint32).max) return _inodePath(fs, id);
        if (id == 1) return bytes("/");
        bytes[] memory reverse = new bytes[](16);
        uint256 count;
        uint256 size = 1;
        while (id != 1) {
            if (id == 0 || id > fs.inodes.length || count == 16) revert VFS0aStateError(2, 0);
            reverse[count++] = fs.inodes[id - 1].name;
            size += fs.inodes[id - 1].name.length + (count == 1 ? 0 : 1);
            id = fs.inodes[id - 1].parent;
        }
        out = new bytes(size);
        out[0] = 0x2f;
        uint256 at = 1;
        while (count != 0) {
            bytes memory c = reverse[--count];
            for (uint256 i; i < c.length; ++i) out[at++] = c[i];
            if (count != 0) out[at++] = 0x2f;
        }
    }

    function _validateVFS(VFSState memory fs, uint256 base) private pure {
        if (base == type(uint256).max) _validateVFS(fs, base);
        if (fs.inodes.length < 3 || fs.inodes.length > MAX_VFS_INODES
            || fs.descriptors.length > MAX_VFS_DESCRIPTORS
            || fs.nextInode != fs.inodes.length + 1
            || fs.nextDescriptor != fs.descriptors.length + 1) {
            revert VFS0aStateError(1, base);
        }
        uint256 total;
        uint256 pending;
        uint256 recordOffset = base + 24;
        for (uint256 i; i < fs.inodes.length; ++i) {
            VFSInode memory n = fs.inodes[i];
            bool framing = n.id != i + 1 || (n.kind != 1 && n.kind != 2)
                || (n.kind == 1 && n.readOnly != (i == 2))
                || (i == 0 ? (n.parent != 0 || n.name.length != 0)
                    : (n.parent == 0 || n.parent >= n.id || n.name.length == 0
                        || n.name.length > 64));
            if (framing) revert VFS0aStateError(2, recordOffset);
            if (i != 0) {
                if (fs.inodes[n.parent - 1].kind != 1
                    || _bytesEqual(n.name, bytes(".")) || _bytesEqual(n.name, bytes(".."))) {
                    revert VFS0aStateError(2, recordOffset);
                }
                for (uint256 k; k < n.name.length; ++k) {
                    uint8 ch = uint8(n.name[k]);
                    if (ch < 0x20 || ch > 0x7e || ch == 0x2f) {
                        revert VFS0aStateError(2, recordOffset);
                    }
                }
            }
            if (n.kind == 1) {
                if (n.data.length != 0) revert VFS0aStateError(3, recordOffset);
            } else {
                if (n.data.length > 65536) revert VFS0aStateError(3, recordOffset);
                total += n.data.length;
            }
            for (uint256 j; j < i; ++j) {
                if (n.parent == fs.inodes[j].parent
                    && _bytesEqual(n.name, fs.inodes[j].name)) {
                    revert VFS0aStateError(2, recordOffset);
                }
            }
            bytes memory canonical = _inodePath(fs, uint32(i + 1));
            if (canonical.length > 256) revert VFS0aStateError(2, recordOffset);
            recordOffset += 15 + n.name.length + n.data.length;
        }
        if (fs.inodes[0].kind != 1 || fs.inodes[0].readOnly
            || fs.inodes[1].kind != 1 || fs.inodes[1].parent != 1
            || fs.inodes[1].readOnly || !_bytesEqual(fs.inodes[1].name, bytes("work"))
            || fs.inodes[2].kind != 1 || fs.inodes[2].parent != 1
            || !fs.inodes[2].readOnly || !_bytesEqual(fs.inodes[2].name, bytes("ro"))) {
            revert VFS0aStateError(2, base);
        }
        if (total != fs.logicalFileBytes || total > 65536) revert VFS0aStateError(3, base);
        for (uint256 i; i < fs.descriptors.length; ++i) {
            VFSDescriptor memory d = fs.descriptors[i];
            if (d.id != i + 1 || d.inode == 0 || d.inode > fs.inodes.length
                || fs.inodes[d.inode - 1].kind != 2 || d.ownerRef == 0
                || (d.flags != 1 && d.flags != 2 && d.flags != 6)
                || d.cursor > 65536 || d.phase < 1 || d.phase > 3) {
                revert VFS0aStateError(4, recordOffset);
            }
            // Read-only bits cannot change after seeding in this profile. An
            // output descriptor (even closed) therefore cannot own a read-only
            // target or a target beneath a read-only ancestor.
            if ((d.flags & 2) != 0 && _effectiveReadOnly(fs, d.inode)) {
                revert VFS0aStateError(4, recordOffset);
            }
            for (uint256 j; j < i; ++j) {
                if (fs.descriptors[j].ownerRef == d.ownerRef) revert VFS0aStateError(4, recordOffset);
            }
            if (d.phase == 1) {
                if (d.bindDepth == 0) revert VFS0aStateError(5, recordOffset);
                ++pending;
            } else if (d.bindDepth != 0 || d.bindPC != 0) {
                revert VFS0aStateError(5, recordOffset);
            }
            recordOffset += 28;
        }
        if (pending > 1) revert VFS0aStateError(5, base);
    }

    function _encodeVFS(VFSState memory fs) private pure returns (bytes memory out) {
        if (fs.nextDescriptor == type(uint32).max) return _encodeVFS(fs);
        _validateVFS(fs, 0);
        out = new bytes(_vfsEncodedSize(fs));
        uint256 at;
        at = _put(out, at, fs.nextInode, 4);
        at = _put(out, at, fs.nextDescriptor, 4);
        at = _put(out, at, fs.inodes.length, 4);
        at = _put(out, at, fs.descriptors.length, 4);
        at = _put(out, at, fs.logicalFileBytes, 8);
        for (uint256 i; i < fs.inodes.length; ++i) {
            VFSInode memory n = fs.inodes[i];
            at = _put(out, at, n.id, 4);
            at = _put(out, at, n.kind, 1);
            at = _put(out, at, n.readOnly ? 1 : 0, 1);
            at = _put(out, at, n.parent, 4);
            at = _put(out, at, n.name.length, 1);
            at = _put(out, at, n.data.length, 4);
            for (uint256 j; j < n.name.length; ++j) out[at++] = n.name[j];
            for (uint256 j; j < n.data.length; ++j) out[at++] = n.data[j];
        }
        for (uint256 i; i < fs.descriptors.length; ++i) {
            VFSDescriptor memory d = fs.descriptors[i];
            at = _put(out, at, d.id, 4);
            at = _put(out, at, d.inode, 4);
            at = _put(out, at, d.ownerRef, 4);
            at = _put(out, at, d.flags, 1);
            at = _put(out, at, d.cursor, 8);
            at = _put(out, at, d.phase, 1);
            at = _put(out, at, d.bindDepth, 2);
            at = _put(out, at, d.bindPC, 4);
        }
        assert(at == out.length);
    }

    function _decodeVFS(bytes memory data, uint256 at, uint256 base)
        private pure returns (VFSState memory fs, uint256 next)
    {
        uint256 sectionAt = at;
        uint256 v;
        (v, at) = _get(data, at, 4, base); fs.nextInode = uint32(v);
        (v, at) = _get(data, at, 4, base); fs.nextDescriptor = uint32(v);
        (uint256 inodeCount, uint256 n) = _get(data, at, 4, base); at = n;
        (uint256 descriptorCount, uint256 q) = _get(data, at, 4, base); at = q;
        (v, at) = _get(data, at, 8, base); fs.logicalFileBytes = uint64(v);
        if (inodeCount > MAX_VFS_INODES || descriptorCount > MAX_VFS_DESCRIPTORS) {
            revert VFS0aStateError(1, base + sectionAt);
        }
        fs.inodes = new VFSInode[](inodeCount);
        fs.descriptors = new VFSDescriptor[](descriptorCount);
        for (uint256 i; i < inodeCount; ++i) {
            uint256 id; uint256 kind; uint256 ro; uint256 parent; uint256 nl; uint256 dl;
            (id, at) = _get(data, at, 4, base);
            (kind, at) = _get(data, at, 1, base);
            (ro, at) = _get(data, at, 1, base);
            (parent, at) = _get(data, at, 4, base);
            (nl, at) = _get(data, at, 1, base);
            (dl, at) = _get(data, at, 4, base);
            if (nl > 64 || dl > 65536 || at > data.length || data.length - at < nl + dl) {
                revert VFS0aStateError(1, base + at);
            }
            bytes memory name = new bytes(nl);
            bytes memory fileData = new bytes(dl);
            for (uint256 j; j < nl; ++j) name[j] = data[at++];
            for (uint256 j; j < dl; ++j) fileData[j] = data[at++];
            fs.inodes[i] = VFSInode(uint32(id), uint8(kind), ro != 0,
                uint32(parent), name, fileData);
        }
        for (uint256 i; i < descriptorCount; ++i) {
            uint256 id; uint256 inode; uint256 owner; uint256 flags;
            uint256 cursor; uint256 phase; uint256 depth; uint256 pc;
            (id, at) = _get(data, at, 4, base);
            (inode, at) = _get(data, at, 4, base);
            (owner, at) = _get(data, at, 4, base);
            (flags, at) = _get(data, at, 1, base);
            (cursor, at) = _get(data, at, 8, base);
            (phase, at) = _get(data, at, 1, base);
            (depth, at) = _get(data, at, 2, base);
            (pc, at) = _get(data, at, 4, base);
            fs.descriptors[i] = VFSDescriptor(uint32(id), uint32(inode), uint32(owner),
                uint8(flags), uint64(cursor), uint8(phase), uint16(depth), uint32(pc));
        }
        _validateVFS(fs, base + sectionAt);
        next = at;
    }

    function _putBytes16(bytes memory out, uint256 at, bytes memory value)
        private pure returns (uint256)
    {
        at = _put(out, at, value.length, 2);
        assembly ("memory-safe") {
            mcopy(add(add(out, 32), at), add(value, 32), mload(value))
        }
        return at + value.length;
    }

    function _put(bytes memory out, uint256 at, uint256 value, uint256 width)
        private pure returns (uint256)
    {
        if (width == 0 || width > 32 || at > out.length || out.length - at < width) {
            revert LC0StateError(2, at);
        }
        // Copy exactly the field width, including unaligned/end-of-buffer writes.
        // Scratch is confined to 0..31; no writes past the allocated byte array.
        assembly ("memory-safe") {
            mstore(0, shl(mul(sub(32, width), 8), value))
            mcopy(add(add(out, 32), at), 0, width)
        }
        return at + width;
    }

    function _get(bytes memory data, uint256 at, uint256 width, uint256 base)
        private pure returns (uint256 value, uint256 next)
    {
        if (width == 0 || width > 32 || at > data.length || data.length - at < width) {
            revert LC0StateError(2, base + at);
        }
        assembly ("memory-safe") {
            mstore(0, 0)
            mcopy(0, add(add(data, 32), at), width)
            value := shr(mul(sub(32, width), 8), mload(0))
        }
        next = at + width;
    }

    function _decodePrelude(bytes memory data, uint256 base)
        private pure returns (Prelude memory p)
    {
        uint256 at;
        (uint256 v, uint256 n) = _get(data, at, 4, base); at = n;
        if (v != uint32(bytes4("MR01"))) revert LC0StateError(3, base);
        (v, at) = _get(data, at, 1, base); p.lifecycle = uint8(v);
        if (p.lifecycle < 1 || p.lifecycle > 3) revert LC0StateError(4, base + 4);
        (v, at) = _get(data, at, 4, base); p.result = int32(uint32(v));
        (v, at) = _get(data, at, 1, base); p.javaKind = uint8(v);
        (v, at) = _get(data, at, 4, base); p.javaRef = uint32(v);
        (v, at) = _get(data, at, 8, base); p.totalJvmSteps = uint64(v);
        (v, at) = _get(data, at, 8, base); p.totalInternalSteps = uint64(v);
        (v, at) = _get(data, at, 1, base); p.rootKind = uint8(v);
        (v, at) = _get(data, at, 32, base); p.argsCommitment = bytes32(v);
        if (p.rootKind != ROOT_KIND_MAIN_EMPTY_STRING_ARRAY || p.argsCommitment != EMPTY_ARGS_COMMITMENT) revert LC0StateError(7, base + 30);
        (p.entryClass, at) = _getBytes16(data, at, base);
        (p.entry, at) = _getBytes16(data, at, base);
        if (p.entryClass.length == 0 || p.entryClass.length > 256 || p.entry.length == 0
            || p.entry.length > 256 || !_ascii(p.entryClass) || !_ascii(p.entry)) {
            revert LC0StateError(4, base + 30);
        }
        (v, at) = _get(data, at, 1, base);
        if (v > 8) revert LC0StateError(4, base + at - 1);
        p.args = new int32[](v);
        for (uint256 i; i < v; ++i) {
            (uint256 q, uint256 next) = _get(data, at, 4, base); at = next;
            p.args[i] = int32(uint32(q));
        }
        if ((p.lifecycle == 1 && (p.result != 0 || p.javaKind != 0 || p.javaRef != 0))
            || (p.lifecycle == 2 && (p.javaKind != 0 || p.javaRef != 0))
            || (p.lifecycle == 3 && (p.result != 0
                || p.javaKind > 12 || p.javaRef == 0))) revert LC0StateError(7, base + 4);
    }

    function _decodeMachine(
        bytes memory data, Program memory p, Prelude memory pre, uint256 base
    ) private pure returns (RuntimeState memory s) {
        s = _freshState(p, pre.args, false);
        s.lifecycle = pre.lifecycle;
        s.result = pre.result;
        s.totalJvmSteps = pre.totalJvmSteps;
        s.totalInternalSteps = pre.totalInternalSteps;
        s.rootInitializationScheduled = true;
        uint256 at = _preludeEnd(data, base);
        (uint256 v, uint256 next) = _get(data, at, 2, base); at = next;
        if (v != p.classes.length) revert LC0StateError(4, base + at - 2);
        for (uint256 i; i < p.classes.length; ++i) {
            (v, at) = _get(data, at, 1, base);
            if (v > 3) revert LC0StateError(4, base + at - 1);
            s.initializationState[i] = uint8(v);
            (v, at) = _get(data, at, 1, base);
            if (v > 1) revert LC0StateError(4, base + at - 1);
            s.initializerStarted[i] = v != 0;
            (v, at) = _get(data, at, 2, base);
            uint256 expected;
            for (uint256 j; j < p.classes[i].fields.length; ++j) {
                if ((p.classes[i].fields[j].accessFlags & 0x0008) != 0) ++expected;
            }
            if (v != expected) revert LC0StateError(4, base + at - 2);
            uint256 prior;
            for (uint256 j; j < v; ++j) {
                (uint256 fi, uint256 nn) = _get(data, at, 2, base); at = nn;
                if (fi >= p.classes[i].fields.length || (j != 0 && fi <= prior)
                    || (p.classes[i].fields[fi].accessFlags & 0x0008) == 0) {
                    revert LC0StateError(4, base + at - 2);
                }
                prior = fi;
                (uint256 value, uint256 vn) = _get(data, at, 32, base); at = vn;
                _checkValueShape(value, true, base + at - 32);
                uint8 wanted = _fieldKind(p.classes[i], p.classes[i].fields[fi]);
                if (_valueKind(value) != wanted) revert LC0StateError(5, base + at - 32);
                s.staticValues[i][fi] = value;
            }
        }
        (v, at) = _get(data, at, 2, base);
        if (v > MAX_FRAMES || (pre.lifecycle == 1 && v == 0)
            || (pre.lifecycle != 1 && v != 0)) revert LC0StateError(4, base + at - 2);
        s.frames = new Frame[](MAX_FRAMES);
        s.depth = v;
        for (uint256 i; i < v; ++i) {
            uint256 frameAt = at;
            (uint256 ci, uint256 nn) = _get(data, at, 2, base); at = nn;
            (uint256 mi, uint256 mn) = _get(data, at, 2, base); at = mn;
            (uint256 pc, uint256 pn) = _get(data, at, 4, base); at = pn;
            (uint256 callPC, uint256 cn) = _get(data, at, 32, base); at = cn;
            (uint256 flags, uint256 fn) = _get(data, at, 1, base); at = fn;
            (uint256 thisHandle, uint256 thn) = _get(data, at, 4, base); at = thn;
            if (ci >= p.classes.length || flags > 31) revert LC0StateError(5, base + frameAt);
            _validateHierarchy(p.classes, ci, s.parentLinks, s.hierarchyState);
            bool continuation = (flags & 2) != 0;
            if (continuation) {
                if (mi != 0 || pc != 0 || thisHandle != 0 || flags != 2) {
                    revert LC0StateError(5, base + frameAt);
                }
                Frame memory synthetic;
                synthetic.classIndex = ci;
                synthetic.callPC = callPC;
                synthetic.isInitContinuation = true;
                s.frames[i] = synthetic;
            } else {
                if (mi >= p.classes[ci].methods.length) revert LC0StateError(5, base + frameAt);
                Selected memory sel = _restoreSelection(
                    p, ci, mi, callPC, (flags & 1) != 0, (flags & 4) != 0
                );
                if (pc > sel.codeLength) revert LC0StateError(5, base + frameAt + 4);
                Frame memory f = _newFrame(ci, mi, sel, callPC);
                f.pc = pc;
                f.isInitializer = (flags & 1) != 0;
                f.isConstructor = (flags & 4) != 0;
                f.isConstructorLinked = (flags & 8) != 0;
                f.entered = (flags & 16) != 0;
                f.thisHandle = thisHandle;
                s.frames[i] = f;
            }
            (uint256 sp, uint256 sn) = _get(data, at, 2, base); at = sn;
            if (continuation && sp != 0) revert LC0StateError(5, base + at - 2);
            if (!continuation && sp > s.frames[i].stack.length) revert LC0StateError(5, base + at - 2);
            s.frames[i].sp = sp;
            for (uint256 j; j < sp; ++j) {
                (uint256 cell, uint256 qn) = _get(data, at, 32, base); at = qn;
                _checkValueShape(cell, false, base + at - 32);
                s.frames[i].stack[j] = cell;
            }
            (uint256 lc, uint256 ln) = _get(data, at, 2, base); at = ln;
            if ((continuation && lc != 0) || (!continuation && lc != s.frames[i].locals.length)) {
                revert LC0StateError(5, base + at - 2);
            }
            uint256 bitmapBytes = (lc + 7) / 8;
            if (at > data.length || data.length - at < bitmapBytes) {
                revert LC0StateError(2, base + at);
            }
            uint256 bitmapAt = at; at += bitmapBytes;
            if (lc != 0 && (lc & 7) != 0) {
                uint8 last = uint8(data[bitmapAt + bitmapBytes - 1]);
                if ((last >> (lc & 7)) != 0) revert LC0StateError(5, base + bitmapAt + bitmapBytes - 1);
            }
            for (uint256 j; j < lc; ++j) {
                bool initialized = (uint8(data[bitmapAt + j / 8]) & uint8(1 << (j & 7))) != 0;
                (uint256 cell, uint256 qn) = _get(data, at, 32, base); at = qn;
                if (!initialized && cell != 0) revert LC0StateError(5, base + at - 32);
                if (initialized) _checkValueShape(cell, true, base + at - 32);
                s.frames[i].initialized[j] = initialized;
                s.frames[i].locals[j] = cell;
            }
            _checkLocalCategories(s.frames[i], base + frameAt);
        }
        (uint256 nextHandle, uint256 hn) = _get(data, at, 4, base); at = hn;
        if (nextHandle > MAX_HANDLES) revert LC0StateError(4, base + at - 4);
        s.nextHandle = nextHandle;
        (uint256 oo, uint256 oon) = _get(data, at, 2, base); at = oon;
        (uint256 oa, uint256 oan) = _get(data, at, 2, base); at = oan;
        (uint256 ae, uint256 aen) = _get(data, at, 4, base); at = aen;
        (uint256 ofs, uint256 ofsn) = _get(data, at, 4, base); at = ofsn;
        (uint256 emergency, uint256 ern) = _get(data, at, 4, base); at = ern;
        (uint256 eo, uint256 eon) = _get(data, at, 2, base); at = eon;
        (uint256 efs, uint256 efsn) = _get(data, at, 4, base); at = efsn;
        if (oo > MAX_OBJECTS || oa > MAX_ARRAYS || ae > MAX_ARRAY_ELEMENTS
            || ofs > MAX_OBJECT_FIELD_SLOTS || eo > MAX_EXCEPTION_OBJECTS
            || efs > MAX_EXCEPTION_FIELD_SLOTS) revert LC0StateError(6, base + at - 26);
        ExceptionArena memory a = s.arena;
        a.ordinaryObjectCount = oo; a.ordinaryArrayCount = oa;
        a.ordinaryArrayElements = ae; a.ordinaryFieldSlots = ofs;
        a.emergencyRef = emergency; a.objectCount = eo; a.fieldSlots = efs;
        a.nextHandle = nextHandle;
        if (nextHandle != 0) {
            a.heap.arrayHeap = new uint64[][](MAX_HANDLES + 1);
            a.heap.objectHeap = new uint256[][](MAX_HANDLES + 1);
            a.heap.metadata = new uint256[](MAX_HANDLES + 1);
            a.heap.classes = new uint256[](MAX_HANDLES + 1);
            a.heap.ranks = new uint8[](MAX_HANDLES + 1);
            a.fieldDefaults = new uint256[][](p.classes.length);
            a.layoutsLoaded = new bool[](p.classes.length);
        }
        uint256 actualOO; uint256 actualOA; uint256 actualAE; uint256 actualOFS;
        uint256 actualEO; uint256 actualEFS;
        for (uint256 h = 1; h <= nextHandle; ++h) {
            uint256 recordAt = at;
            (uint256 ordinal, uint256 on) = _get(data, at, 4, base); at = on;
            (uint256 meta, uint256 metan) = _get(data, at, 32, base); at = metan;
            (uint256 ci, uint256 cin) = _get(data, at, 2, base); at = cin;
            (uint256 rank, uint256 rn) = _get(data, at, 1, base); at = rn;
            (uint256 count, uint256 con) = _get(data, at, 4, base); at = con;
            uint8 k = _heapKindAt(meta);
            if (ordinal != h || k == 0 || ci >= p.classes.length) {
                revert LC0StateError(6, base + recordAt);
            }
            if (k == HEAP_OBJECT) {
                if ((p.classes[ci].accessFlags & (0x0200 | 0x0400)) != 0) {
                    revert LC0StateError(6, base + recordAt);
                }
                _validateHierarchy(p.classes, ci, s.parentLinks, s.hierarchyState);
            }
            a.heap.metadata[h] = meta; a.heap.classes[h] = ci; a.heap.ranks[h] = uint8(rank);
            if (k == HEAP_ARRAY) {
                if (rank == 0 || count > MAX_ARRAY_LENGTH || ci != 0
                    || !_validArrayLeaf(uint8(rank), meta, p.classes.length)) {
                    revert LC0StateError(6, base + recordAt);
                }
                _requireCellBytes(data, at, count, 8, base);
                a.heap.arrayHeap[h] = new uint64[](count);
                for (uint256 j; j < count; ++j) {
                    (uint256 cell, uint256 qn) = _get(data, at, 8, base); at = qn;
                    a.heap.arrayHeap[h][j] = uint64(cell);
                }
                ++actualOA; actualAE += count;
            } else {
                uint256 exceptionKind = meta & 0xff;
                if (rank != 0 || (meta & ~(HEAP_OBJECT_MARKER | uint256(0xff))) != 0
                    || exceptionKind > 12
                    || (exceptionKind != 0 && a.classesByKind[exceptionKind] != ci)) {
                    revert LC0StateError(6, base + recordAt);
                }
                uint256 expectedFields = _instanceFieldCount(
                    p.classes, ci, s.parentLinks, ROOT_FAULT_SENTINEL
                );
                if (count != expectedFields) revert LC0StateError(6, base + recordAt);
                _requireCellBytes(data, at, count, 32, base);
                a.heap.objectHeap[h] = new uint256[](count);
                for (uint256 j; j < count; ++j) {
                    (uint256 cell, uint256 qn) = _get(data, at, 32, base); at = qn;
                    _checkValueShape(cell, true, base + at - 32);
                    a.heap.objectHeap[h][j] = cell;
                }
                if (exceptionKind != 0) {
                    if (h != emergency) ++actualEO; // the reserved OOM is outside objectCount
                    actualEFS += count;
                } else { ++actualOO; actualOFS += count; }
            }
        }
        if (actualOO != oo || actualOA != oa || actualAE != ae || actualOFS != ofs
            || actualEO != eo || actualEFS != efs
            || ((nextHandle == 0) != (emergency == 0))
            || (nextHandle != 0 && (emergency != 1 || (a.heap.metadata[1] & 0xff) != 7))) {
            revert LC0StateError(6, 0);
        }
        (v, at) = _get(data, at, 1, base);
        if (v > 1) revert LC0StateError(4, base + at - 1);
        bool pendingActive = v != 0;
        (uint256 pk, uint256 pkn) = _get(data, at, 1, base); at = pkn;
        (uint256 pr, uint256 prn) = _get(data, at, 4, base); at = prn;
        (uint256 ppc, uint256 ppcn) = _get(data, at, 32, base); at = ppcn;
        if ((!pendingActive && (pk != 0 || pr != 0 || ppc != 0))
            || (pendingActive && (pk > 12 || pr == 0 || pr > nextHandle
                || _heapKindAt(a.heap.metadata[pr]) != HEAP_OBJECT
                || !_typeAssignable(p.classes, a.heap.classes[pr], a.throwableClass,
                    s.parentLinks)
                || _exactKnownKind(a, a.heap.classes[pr]) != pk))) {
            revert LC0StateError(7, base + at - 38);
        }
        a.pending = PendingException(pendingActive, pk, pr, ppc);
        (uint256 internCount, uint256 icn) = _get(data, at, 2, base); at = icn;
        if (internCount > MAX_INTERNED_STRINGS) revert LC0StateError(4, base + at - 2);
        a.internHandles = new uint256[](MAX_INTERNED_STRINGS);
        a.internHashes = new uint32[](MAX_INTERNED_STRINGS);
        a.internCount = internCount;
        uint256 priorHandle;
        for (uint256 i; i < internCount; ++i) {
            (uint256 handle, uint256 ihn) = _get(data, at, 4, base); at = ihn;
            (uint256 hash, uint256 ihashn) = _get(data, at, 4, base); at = ihashn;
            if (handle == 0 || handle > nextHandle || (i != 0 && handle <= priorHandle)
                || a.heap.classes[handle] != a.stringClass) revert LC0StateError(7, base + at - 8);
            priorHandle = handle; a.internHandles[i] = handle; a.internHashes[i] = uint32(hash);
        }
        (s.vfs, at) = _decodeVFS(data, at, base);
        if (at != data.length) revert LC0StateError(2, base + at);
        if (internCount != 0) {
            // Rebuild immutable String layout state without resolving a constant
            // or writing any guest String.hash field.
            if (!_ensureStringLayout(a, p.classes, a.stringClass,
                s.parentLinks, s.hierarchyState)) revert LC0StateError(7, 0);
            for (uint256 i; i < internCount; ++i) {
                uint256 handle = a.internHandles[i];
                uint256[] memory fields = a.heap.objectHeap[handle];
                if (fields.length != a.stringDefaults.length
                    || _valueKind(fields[a.stringValueOffset]) != KIND_REF) revert LC0StateError(7, 0);
                uint256 backing = _payload(fields[a.stringValueOffset]);
                if (backing == 0 || backing > nextHandle
                    || a.heap.metadata[backing] != PRIMITIVE_CHAR
                    || a.heap.ranks[backing] != 1) revert LC0StateError(7, 0);
                for (uint256 j; j < a.heap.arrayHeap[backing].length; ++j) {
                    if (a.heap.arrayHeap[backing][j] > 0xffff) revert LC0StateError(7, 0);
                }
                uint64[] memory units = _stringUnits(a, handle, ROOT_FAULT_SENTINEL);
                uint32 actualHash = _stringHash(units);
                uint256 cached = a.heap.objectHeap[handle][a.stringHashOffset];
                if (a.internHashes[i] != actualHash || _valueKind(cached) != KIND_INT
                    || (uint32(_payload(cached)) != 0
                        && uint32(_payload(cached)) != actualHash)) {
                    revert LC0StateError(7, 0);
                }
            }
        }
        s.arena = a;
        _validateRestoredReferences(p, s);
        _validateClassMirrors(p, s);
        _validateInitAndFrames(p, s, true);
        _validateVFSHeap(p, s);
        if ((pre.lifecycle == 3 && (!a.pending.active || pre.javaKind != a.pending.kind
                || pre.javaRef != a.pending.ref))
            || (pre.lifecycle == 2 && a.pending.active)) revert LC0StateError(7, 0);
    }

    function _restoreSelection(
        Program memory p, uint256 ci, uint256 mi, uint256 callPC,
        bool initializer, bool isCtor
    ) private pure returns (Selected memory sel) {
        if (p.selected[ci].length == 0) {
            p.selected[ci] = new Selected[][](p.classes[ci].methods.length);
            p.referenceCaches[ci] = new uint256[](p.classes[ci].cp.length);
            p.fieldCaches[ci] = new uint256[](p.classes[ci].cp.length);
        }
        if (_selectionLoaded(p.selected, ci, mi)) return p.selected[ci][mi][0];
        if (ci == p.rootClass && mi == p.rootMethod) {
            sel = _loadRoot(p.classes[ci], p.classes[ci].methods[mi], ci, mi);
        } else if (initializer) {
            sel = _loadInitializer(p.classes[ci], mi, ci);
        } else if ((uint16(p.classes[ci].methods[mi]) & 0x0008) != 0) {
            sel = _loadCallee(p.classes[ci], mi, callPC, ci);
        } else {
            // The selected owner/method and the retained constructor/private flags are
            // authoritative; no invoking-type cache is serialized or invented here.
            sel = _loadSpecialCallee(p.classes[ci], mi, callPC, isCtor, ci);
        }
        _predecode(p.classes[ci], sel);
        _putSelection(p.selected, ci, mi, sel);
    }

    // A class table is only method-sized pointers.  A slot owns exactly one
    // Selected object only after that method is resolved; no unselected method
    // can alias the mutable handler cache of another slot.
    function _selectionLoaded(Selected[][][] memory selected, uint256 ci, uint256 mi)
        private pure returns (bool)
    {
        return selected[ci].length != 0 && selected[ci][mi].length == 1
            && selected[ci][mi][0].loaded;
    }

    function _putSelection(
        Selected[][][] memory selected, uint256 ci, uint256 mi, Selected memory value
    ) private pure {
        Selected[] memory slot = new Selected[](1);
        slot[0] = value;
        selected[ci][mi] = slot;
    }

    function _validateRestoredReferences(Program memory p, RuntimeState memory s) private pure {
        uint256[] memory meta = s.arena.heap.metadata;
        for (uint256 i; i < s.depth; ++i) {
            Frame memory f = s.frames[i];
            if (f.thisHandle > s.nextHandle || _stackWords(f.stack, f.sp) > f.stack.length) {
                revert LC0StateError(5, 0);
            }
            for (uint256 j; j < f.sp; ++j) _checkRefCell(f.stack[j], meta, s.nextHandle);
            for (uint256 j; j < f.locals.length; ++j) if (f.initialized[j]) {
                _checkRefCell(f.locals[j], meta, s.nextHandle);
            }
        }
        for (uint256 ci; ci < p.classes.length; ++ci) {
            for (uint256 j; j < p.classes[ci].fields.length; ++j) {
                if ((p.classes[ci].fields[j].accessFlags & 0x0008) != 0) {
                    _checkCheckpointField(p, s, ci, j, s.staticValues[ci][j], 7);
                }
            }
        }
        uint256[][] memory layouts = new uint256[][](p.classes.length);
        for (uint256 h = 1; h <= s.nextHandle; ++h) {
            uint8 heapKind = _heapKindAt(meta[h]);
            if (heapKind == HEAP_ARRAY) {
                bool refs = _arrayHasReferenceComponents(
                    s.arena.heap.ranks[h], s.arena.heap.metadata[h]
                );
                for (uint256 j; j < s.arena.heap.arrayHeap[h].length; ++j) {
                    uint64 cell = s.arena.heap.arrayHeap[h][j];
                    if (refs) {
                        if (cell > type(uint32).max) revert LC0StateError(6, 0);
                        uint256 ref = uint32(cell);
                        if (ref != 0 && (ref > s.nextHandle || _heapKindAt(meta[ref]) == 0)) {
                            revert LC0StateError(6, 0);
                        }
                        if (ref != 0 && s.arena.heap.metadata[h] >= ARRAY_CLASS_BASE) {
                            _validateHierarchy(p.classes, s.arena.heap.metadata[h] - ARRAY_CLASS_BASE,
                                s.parentLinks, s.hierarchyState);
                        }
                        if (!_valueFitsArrayComponent(p.classes, _packRef(uint32(ref)),
                            s.arena.heap.ranks[h], s.arena.heap.metadata[h], meta,
                            s.arena.heap.classes, s.arena.heap.ranks, meta, s.parentLinks)) {
                            revert LC0StateError(6, 0);
                        }
                    } else {
                        uint256 leaf = s.arena.heap.metadata[h];
                        if (leaf != PRIMITIVE_LONG && leaf != PRIMITIVE_DOUBLE) {
                            if (cell > type(uint32).max
                                || _normalizeInt(uint32(cell), uint8(leaf)) != uint32(cell)) {
                                revert LC0StateError(6, 0);
                            }
                        }
                    }
                }
                continue;
            }
            uint256 ci = s.arena.heap.classes[h];
            if ((p.classes[ci].accessFlags & (0x0200 | 0x0400)) != 0) {
                revert LC0StateError(6, 0);
            }
            if (layouts[ci].length == 0 && s.arena.heap.objectHeap[h].length != 0) {
                layouts[ci] = _checkpointFieldLayout(p, s, ci, s.arena.heap.objectHeap[h].length);
            }
            for (uint256 j; j < s.arena.heap.objectHeap[h].length; ++j) {
                uint256 cell = s.arena.heap.objectHeap[h][j];
                _checkRefCell(cell, meta, s.nextHandle);
                _checkCheckpointField(p, s, layouts[ci][j] >> 128,
                    uint128(layouts[ci][j]), cell, 6);
            }
        }
        _validateThrowableGraph(p, s);
        _validateStringGraph(p, s);
    }

    function _validateThrowableGraph(Program memory p, RuntimeState memory s) private pure {
        ExceptionArena memory a = s.arena;
        if (a.heap.metadata.length == 0) return;
        if (p.classes[a.throwableClass].cp.length == 0) {
            p.classes[a.throwableClass] = _parseBundleClass(p.classes[a.throwableClass].data);
        }
        uint256 eiieClass = a.classesByKind[3];
        if (p.classes[eiieClass].cp.length == 0) {
            p.classes[eiieClass] = _parseBundleClass(p.classes[eiieClass].data);
        }
        _validateHierarchy(p.classes, a.throwableClass, s.parentLinks, s.hierarchyState);
        _validateHierarchy(p.classes, eiieClass, s.parentLinks, s.hierarchyState);
        uint256 messageOffset = _canonicalFieldOffset(
            p.classes, a.throwableClass, bytes("detailMessage"), bytes("Ljava/lang/String;"),
            s.parentLinks, ROOT_FAULT_SENTINEL
        );
        uint256 causeOffset = _canonicalFieldOffset(
            p.classes, a.throwableClass, bytes("cause"), bytes("Ljava/lang/Throwable;"),
            s.parentLinks, ROOT_FAULT_SENTINEL
        );
        uint256 exceptionOffset = _canonicalFieldOffset(
            p.classes, eiieClass, bytes("exception"), bytes("Ljava/lang/Throwable;"),
            s.parentLinks, ROOT_FAULT_SENTINEL
        );
        _validateActiveIOEConstructors(
            p, s, messageOffset, causeOffset, exceptionOffset, eiieClass
        );
        for (uint256 h = 1; h <= s.nextHandle; ++h) {
            if (_heapKindAt(a.heap.metadata[h]) != HEAP_OBJECT
                || !_typeAssignable(p.classes, a.heap.classes[h], a.throwableClass,
                    s.parentLinks)) continue;
            uint256[] memory fields = a.heap.objectHeap[h];
            if (messageOffset >= fields.length || causeOffset >= fields.length
                || _valueKind(fields[messageOffset]) != KIND_REF
                || _valueKind(fields[causeOffset]) != KIND_REF) revert LC0StateError(7, 0);
            uint256 message = _payload(fields[messageOffset]);
            uint256 cause = _payload(fields[causeOffset]);
            if (message != 0 && (message > s.nextHandle
                || _heapKindAt(a.heap.metadata[message]) != HEAP_OBJECT
                || a.heap.classes[message] != a.stringClass)) revert LC0StateError(7, 0);
            uint256 origin = a.heap.metadata[h] & 0xff;
            if (origin == 0) {
                // The only exposed Throwable constructors either leave the default
                // null during a real partial construction or store this exact ref.
                if (cause != 0 && cause != h) revert LC0StateError(7, 0);
            } else if (message != 0 || cause != h) {
                revert LC0StateError(7, 0);
            }
            if (!_typeAssignable(p.classes, a.heap.classes[h], eiieClass, s.parentLinks)) continue;
            if (exceptionOffset >= fields.length
                || _valueKind(fields[exceptionOffset]) != KIND_REF) revert LC0StateError(7, 0);
            uint256 exception = _payload(fields[exceptionOffset]);
            if (exception != 0 && (exception > s.nextHandle
                || _heapKindAt(a.heap.metadata[exception]) != HEAP_OBJECT
                || !_typeAssignable(p.classes, a.heap.classes[exception], a.throwableClass,
                    s.parentLinks))) revert LC0StateError(7, 0);
            if (origin == 3 && (exception == 0 || exception >= h
                || _typeAssignable(p.classes, a.heap.classes[exception], a.errorClass,
                    s.parentLinks))) revert LC0StateError(7, 0);
        }
    }

    function _validateActiveIOEConstructors(
        Program memory p, RuntimeState memory s, uint256 messageOffset,
        uint256 causeOffset, uint256 exceptionOffset, uint256 eiieClass
    ) private pure {
        for (uint256 i; i < s.depth; ++i) {
            Frame memory f = s.frames[i];
            uint8 kind = _activeIOEConstructorKind(p, s.arena, f, eiieClass);
            if (kind == 0) continue;
            if (f.thisHandle == 0 || f.thisHandle > s.nextHandle
                || f.locals.length == 0 || !f.initialized[0]
                || _payload(f.locals[0]) != f.thisHandle
                || (_valueKind(f.locals[0]) != KIND_REF
                    && _valueKind(f.locals[0]) != KIND_UNINIT)
                || (s.arena.heap.metadata[f.thisHandle] & 0xff) != 0) {
                revert LC0StateError(7, 0);
            }
            bool deeper;
            for (uint256 j = i + 1; j < s.depth; ++j) {
                if (s.frames[j].isConstructor
                    && s.frames[j].thisHandle == f.thisHandle) { deeper = true; break; }
            }
            // A genuine deeper super-constructor owns the current partial phase.
            // In particular Object Code may have published REF while Throwable's
            // own cause store has not run; that state remains admissible.
            if (deeper) continue;
            uint256[] memory fields = s.arena.heap.objectHeap[f.thisHandle];
            uint256 cause = _payload(fields[causeOffset]);
            uint256 message = _payload(fields[messageOffset]);
            uint256 argument;
            if (kind == 2 || kind == 4 || kind == 6) {
                if (f.locals.length < 2 || !f.initialized[1]
                    || _valueKind(f.locals[1]) != KIND_REF) revert LC0StateError(7, 0);
                argument = _payload(f.locals[1]);
            }
            if (kind == 1 || kind == 2) {
                uint256 expectedCause = f.pc >= 9 ? f.thisHandle : 0;
                uint256 expectedMessage = kind == 2 && f.pc >= 14 ? argument : 0;
                if (cause != expectedCause || message != expectedMessage) {
                    revert LC0StateError(7, 0);
                }
                if (f.pc == 6 && (f.sp != 2
                    || f.stack[0] != _packRef(uint32(f.thisHandle))
                    || f.stack[1] != _packRef(uint32(f.thisHandle)))) {
                    revert LC0StateError(7, 0);
                }
                if (kind == 2 && f.pc == 11 && (f.sp != 2
                    || f.stack[0] != _packRef(uint32(f.thisHandle))
                    || f.stack[1] != _packRef(uint32(argument)))) {
                    revert LC0StateError(7, 0);
                }
            } else if (kind == 3 || kind == 4) {
                if (cause != (f.pc >= 4 ? f.thisHandle : 0) || message != 0) {
                    revert LC0StateError(7, 0);
                }
                uint256 expectedException = kind == 4 && f.pc >= 9 ? argument : 0;
                if (_payload(fields[exceptionOffset]) != expectedException) {
                    revert LC0StateError(7, 0);
                }
                if (kind == 4 && f.pc == 6 && (f.sp != 2
                    || f.stack[0] != _packRef(uint32(f.thisHandle))
                    || f.stack[1] != _packRef(uint32(argument)))) {
                    revert LC0StateError(7, 0);
                }
            } else {
                uint256 completePC = kind == 6 ? 5 : 4;
                uint256 expectedCause = f.pc >= completePC ? f.thisHandle : 0;
                uint256 expectedMessage = kind == 6 && f.pc >= completePC ? argument : 0;
                if (cause != expectedCause || message != expectedMessage) {
                    revert LC0StateError(7, 0);
                }
            }
        }
    }

    function _activeIOEConstructorKind(
        Program memory p, ExceptionArena memory arena, Frame memory f, uint256 eiieClass
    ) private pure returns (uint8) {
        if (!f.isConstructor || f.classIndex >= p.classes.length
            || f.methodIndex >= p.classes[f.classIndex].methods.length) return 0;
        bool throwable = f.classIndex == arena.throwableClass;
        bool eiie = f.classIndex == eiieClass;
        bool forwarding = f.classIndex == arena.throwableClass + 10
            || f.classIndex == arena.throwableClass + 22
            || f.classIndex == arena.throwableClass + 23
            || f.classIndex == arena.throwableClass + 24;
        if (!throwable && !eiie && !forwarding) return 0;
        ClassInfo memory c = p.classes[f.classIndex];
        uint256 meta = c.methods[f.methodIndex];
        (uint256 no, uint256 nn) = _utf(c.cp[(meta >> 16) & 0xffff]);
        (uint256 doff, uint256 dn) = _utf(c.cp[(meta >> 32) & 0xffff]);
        if (!_equalsLiteral(c.data, no, nn, bytes("<init>"))) return 0;
        bool noarg = _equalsLiteral(c.data, doff, dn, bytes("()V"));
        bool stringArg = _equalsLiteral(
            c.data, doff, dn, bytes("(Ljava/lang/String;)V")
        );
        bool throwableArg = _equalsLiteral(
            c.data, doff, dn, bytes("(Ljava/lang/Throwable;)V")
        );
        if (throwable && (noarg || stringArg)) return noarg ? 1 : 2;
        if (eiie && (noarg || throwableArg)) return noarg ? 3 : 4;
        if (forwarding && (noarg || stringArg)) return noarg ? 5 : 6;
        return 0;
    }

    function _validateStringGraph(Program memory p, RuntimeState memory s) private pure {
        bool needsLayout = s.arena.internCount != 0;
        for (uint256 h = 1; h <= s.nextHandle; ++h) {
            if (_heapKindAt(s.arena.heap.metadata[h]) == HEAP_OBJECT
                && s.arena.heap.classes[h] == s.arena.stringClass) needsLayout = true;
        }
        for (uint256 i; i < s.depth; ++i) {
            if (s.frames[i].classIndex == s.arena.stringClass) needsLayout = true;
        }
        if (!needsLayout) return; // preserve literal-free/custom-Object compatibility
        if (!_ensureStringLayout(
            s.arena, p.classes, s.arena.stringClass,
            s.parentLinks, s.hierarchyState
        )) revert LC0StateError(7, 0);

        bool[] memory isString = new bool[](s.nextHandle + 1);
        bool[] memory isDefault = new bool[](s.nextHandle + 1);
        bool[] memory isBacking = new bool[](s.nextHandle + 1);
        bool[] memory activeString = new bool[](s.nextHandle + 1);
        bool[] memory internedHandle = new bool[](s.nextHandle + 1);
        for (uint256 i; i < s.arena.internCount; ++i) {
            uint256 h = s.arena.internHandles[i];
            if (h == 0 || h > s.nextHandle || internedHandle[h]) revert LC0StateError(7, 0);
            internedHandle[h] = true;
        }
        bool reliesOnObjectProfile;

        for (uint256 i; i < s.depth; ++i) {
            Frame memory f = s.frames[i];
            if (!f.isConstructor || f.classIndex != s.arena.stringClass) continue;
            if (f.thisHandle == 0 || f.thisHandle > s.nextHandle
                || s.arena.heap.classes[f.thisHandle] != s.arena.stringClass
                || _activeStringConstructorKind(p, f) == 0) revert LC0StateError(7, 0);
            activeString[f.thisHandle] = true;
            reliesOnObjectProfile = true;
            _validateActiveStringConstructor(p, s, f, isBacking);
        }

        for (uint256 h = 1; h <= s.nextHandle; ++h) {
            if (_heapKindAt(s.arena.heap.metadata[h]) != HEAP_OBJECT
                || s.arena.heap.classes[h] != s.arena.stringClass) continue;
            isString[h] = true;
            uint256[] memory fields = s.arena.heap.objectHeap[h];
            if (fields.length != s.arena.stringDefaults.length
                || _valueKind(fields[s.arena.stringValueOffset]) != KIND_REF
                || _valueKind(fields[s.arena.stringHashOffset]) != KIND_INT) {
                revert LC0StateError(7, 0);
            }
            uint256 backing = _payload(fields[s.arena.stringValueOffset]);
            if (backing == 0) {
                isDefault[h] = true;
                if (uint32(_payload(fields[s.arena.stringHashOffset])) != 0) {
                    revert LC0StateError(7, 0);
                }
                reliesOnObjectProfile = true;
            } else {
                _requireStringBacking(s, backing);
                isBacking[backing] = true;
                uint32 actualHash = _stringHash(s.arena.heap.arrayHeap[backing]);
                uint32 cached = uint32(_payload(fields[s.arena.stringHashOffset]));
                if (cached != 0 && cached != actualHash) revert LC0StateError(7, 0);
            }
            if (!internedHandle[h]) reliesOnObjectProfile = true;
        }

        bytes32[] memory contentFilters = new bytes32[](s.arena.internCount);
        uint256 prior;
        for (uint256 i; i < s.arena.internCount; ++i) {
            uint256 h = s.arena.internHandles[i];
            if (h == 0 || h > s.nextHandle || !isString[h] || isDefault[h]
                || (i != 0 && h <= prior)) revert LC0StateError(7, 0);
            prior = h;
            uint64[] memory units = _stringUnits(s.arena, h, ROOT_FAULT_SENTINEL);
            if (s.arena.internHashes[i] != _stringHash(units)) revert LC0StateError(7, 0);
            // EVM-local filter over validated memory cells. Equal content always
            // has the same filter; filter hits still receive full comparison, so
            // neither Java-hash nor Keccak collisions define String identity.
            bytes32 filter;
            assembly ("memory-safe") {
                filter := keccak256(add(units, 32), mul(mload(units), 32))
            }
            contentFilters[i] = filter;
        }
        for (uint256 i; i < s.arena.internCount; ++i) {
            uint64[] memory left = _stringUnits(
                s.arena, s.arena.internHandles[i], ROOT_FAULT_SENTINEL
            );
            for (uint256 j = i + 1; j < s.arena.internCount; ++j) {
                if (s.arena.internHashes[i] != s.arena.internHashes[j]
                    || contentFilters[i] != contentFilters[j]) continue;
                uint64[] memory right = _stringUnits(
                    s.arena, s.arena.internHandles[j], ROOT_FAULT_SENTINEL
                );
                if (_sameStringUnits(left, right)) revert LC0StateError(7, 0);
            }
        }

        if (reliesOnObjectProfile) _requireStringObjectProfile(
            p.classes, s.arena.stringClass, ROOT_FAULT_SENTINEL,
            s.parentLinks, s.hierarchyState, true
        );
        _validateStringReachability(p, s, isDefault, activeString);
        _validateStringBackingAliases(p, s, isBacking);
    }

    function _activeStringConstructorKind(Program memory p, Frame memory f)
        private pure returns (uint8)
    {
        if (!f.isConstructor || f.classIndex >= p.classes.length
            || f.methodIndex >= p.classes[f.classIndex].methods.length) return 0;
        ClassInfo memory c = p.classes[f.classIndex];
        // These temporary-alias privileges belong only to the pinned String
        // constructors, not arbitrary user constructors with the same descriptor.
        if (!_isNamedClass(c, bytes("java/lang/String"))) return 0;
        uint256 meta = c.methods[f.methodIndex];
        (uint256 no, uint256 nn) = _utf(c.cp[(meta >> 16) & 0xffff]);
        (uint256 doff, uint256 dn) = _utf(c.cp[(meta >> 32) & 0xffff]);
        if (!_equalsLiteral(c.data, no, nn, bytes("<init>"))) return 0;
        if (_equalsLiteral(c.data, doff, dn, bytes("([C)V"))) return 1;
        if (_equalsLiteral(c.data, doff, dn, bytes("(Ljava/lang/String;)V"))) return 2;
        return 0;
    }

    function _requireStringBacking(RuntimeState memory s, uint256 backing) private pure {
        if (backing > s.nextHandle
            || _heapKindAt(s.arena.heap.metadata[backing]) != HEAP_ARRAY
            || s.arena.heap.ranks[backing] != 1
            || s.arena.heap.metadata[backing] != PRIMITIVE_CHAR) {
            revert LC0StateError(7, 0);
        }
        uint64[] memory cells = s.arena.heap.arrayHeap[backing];
        for (uint256 i; i < cells.length; ++i) {
            if (cells[i] > 0xffff) revert LC0StateError(7, 0);
        }
    }

    function _validateActiveStringConstructor(
        Program memory p, RuntimeState memory s, Frame memory f, bool[] memory temporaryBacking
    ) private pure {
        if (f.locals.length < 2 || !f.initialized[0] || !f.initialized[1]
            || _payload(f.locals[0]) != f.thisHandle
            || (_valueKind(f.locals[0]) != KIND_REF
                && _valueKind(f.locals[0]) != KIND_UNINIT)
            || _valueKind(f.locals[1]) != KIND_REF) revert LC0StateError(7, 0);
        uint8 kind = _activeStringConstructorKind(p, f);
        uint256 source = _payload(f.locals[1]);
        if (source == 0) {
            // Pinned Code cannot execute beyond its first null dereference. At
            // that advanced PC, the NPE (or arena-exhaustion OOM) is still pending;
            // the next internal unwind removes this handler-free constructor.
            uint256 faultPC = kind == 1 ? 5 : 6;
            uint256 afterFaultPC = kind == 1 ? 6 : 9;
            if (f.pc > afterFaultPC || (f.pc == afterFaultPC
                && (!s.arena.pending.active || s.arena.pending.faultPC != faultPC
                    || (s.arena.pending.kind != 6 && s.arena.pending.kind != 7)))) {
                revert LC0StateError(7, 0);
            }
        }
        uint256[] memory own = s.arena.heap.objectHeap[f.thisHandle];
        uint256 backing = _payload(own[s.arena.stringValueOffset]);
        uint32 cached = uint32(_payload(own[s.arena.stringHashOffset]));
        if (kind == 1) {
            if (source != 0) _requireStringBacking(s, source);
            if (cached != 0) revert LC0StateError(7, 0);
            uint256 destination;
            if (f.locals.length > 2 && f.initialized[2]) {
                if (_valueKind(f.locals[2]) != KIND_REF) revert LC0StateError(7, 0);
                destination = _payload(f.locals[2]);
                if (destination == 0 || destination == source) revert LC0StateError(7, 0);
                _requireStringBacking(s, destination);
                temporaryBacking[destination] = true;
            }
            // Immediately after newarray the destination is still on the stack.
            if (f.pc == 8 && f.sp != 0 && _valueKind(f.stack[f.sp - 1]) == KIND_REF) {
                destination = _payload(f.stack[f.sp - 1]);
                if (destination == 0 || destination == source) revert LC0StateError(7, 0);
                _requireStringBacking(s, destination);
                temporaryBacking[destination] = true;
            }
            if (backing != 0 && (f.pc < 34 || destination == 0 || backing != destination)) {
                revert LC0StateError(7, 0);
            }
            if (f.pc == 31) {
                _requireStringWriteStack(f, _packRef(uint32(destination)));
            }
            if (destination != 0 && source != 0) {
                uint64[] memory src = s.arena.heap.arrayHeap[source];
                uint64[] memory dst = s.arena.heap.arrayHeap[destination];
                if (src.length != dst.length) revert LC0StateError(7, 0);
                uint256 copied;
                if (f.locals.length > 3 && f.initialized[3]) {
                    if (_valueKind(f.locals[3]) != KIND_INT) revert LC0StateError(7, 0);
                    copied = uint32(_payload(f.locals[3]));
                    if (f.pc == 23) ++copied;
                }
                if (copied > src.length) revert LC0StateError(7, 0);
                for (uint256 i; i < dst.length; ++i) {
                    if (dst[i] != (i < copied ? src[i] : 0)) revert LC0StateError(7, 0);
                }
            }
        } else {
            if (source != 0 && (_heapKindAt(s.arena.heap.metadata[source]) != HEAP_OBJECT
                || s.arena.heap.classes[source] != s.arena.stringClass)) {
                revert LC0StateError(7, 0);
            }
            if (f.pc == 9) {
                uint256 sourceBacking = source == 0 ? 0
                    : _payload(s.arena.heap.objectHeap[source][s.arena.stringValueOffset]);
                _requireStringWriteStack(f, _packRef(uint32(sourceBacking)));
            }
            if (f.pc == 17 && source != 0) {
                _requireStringWriteStack(f, s.arena.heap.objectHeap[source][s.arena.stringHashOffset]);
            }
            if (f.pc < 12) {
                if (backing != 0 || cached != 0) revert LC0StateError(7, 0);
            } else {
                if (source == 0) revert LC0StateError(7, 0);
                uint256[] memory srcFields = s.arena.heap.objectHeap[source];
                if (backing == 0
                    || backing != _payload(srcFields[s.arena.stringValueOffset])) {
                    revert LC0StateError(7, 0);
                }
                if (f.pc < 20) {
                    if (cached != 0) revert LC0StateError(7, 0);
                } else if (cached != uint32(_payload(srcFields[s.arena.stringHashOffset]))) {
                    revert LC0StateError(7, 0);
                }
            }
        }
    }

    // The three field-write safepoints are part of the pinned bootstrap Code,
    // not guest-fixture PCs. Their receiver and value must be the actual
    // constructor target/source, not another otherwise well-formed String/array.
    function _requireStringWriteStack(Frame memory f, uint256 value) private pure {
        if (f.sp != 2 || f.stack[0] != _packRef(uint32(f.thisHandle))
            || f.stack[1] != value) revert LC0StateError(7, 0);
    }

    function _validateStringReachability(
        Program memory p, RuntimeState memory s, bool[] memory isDefault,
        bool[] memory activeString
    ) private pure {
        bool[] memory seen = new bool[](s.nextHandle + 1);
        bool[] memory exposed = new bool[](s.nextHandle + 1);
        uint256[] memory queue = new uint256[](s.nextHandle + 1);
        uint256 tail;
        for (uint256 i; i < s.depth; ++i) {
            Frame memory f = s.frames[i];
            for (uint256 j; j < f.sp; ++j) {
                uint256 cell = f.stack[j];
                uint256 k = _valueKind(cell);
                if (k != KIND_REF && k != KIND_UNINIT) continue;
                uint256 h = _payload(cell); if (h == 0) continue;
                bool internalRef = activeString[h]
                    && ((f.isConstructor && f.thisHandle == h
                            && (f.classIndex == s.arena.stringClass
                                || _isObjectClass(p.classes[f.classIndex]))));
                if (k == KIND_REF && !internalRef) exposed[h] = true;
                if (!seen[h]) { seen[h] = true; queue[tail++] = h; }
            }
            for (uint256 j; j < f.locals.length; ++j) if (f.initialized[j]) {
                uint256 cell = f.locals[j];
                uint256 k = _valueKind(cell);
                if (k != KIND_REF && k != KIND_UNINIT) continue;
                uint256 h = _payload(cell); if (h == 0) continue;
                bool internalRef = activeString[h]
                    && f.isConstructor && f.thisHandle == h
                    && (f.classIndex == s.arena.stringClass
                        || _isObjectClass(p.classes[f.classIndex]));
                if (k == KIND_REF && !internalRef) exposed[h] = true;
                if (!seen[h]) { seen[h] = true; queue[tail++] = h; }
            }
        }
        for (uint256 ci; ci < p.classes.length; ++ci) for (uint256 j; j < p.classes[ci].fields.length; ++j) {
            if ((p.classes[ci].fields[j].accessFlags & 0x0008) == 0
                || _valueKind(s.staticValues[ci][j]) != KIND_REF) continue;
            uint256 h = _payload(s.staticValues[ci][j]); if (h == 0) continue;
            exposed[h] = true; if (!seen[h]) { seen[h] = true; queue[tail++] = h; }
        }
        if (s.arena.pending.active) {
            uint256 h = s.arena.pending.ref; exposed[h] = true;
            if (!seen[h]) { seen[h] = true; queue[tail++] = h; }
        }
        for (uint256 i; i < s.arena.internCount; ++i) {
            uint256 h = s.arena.internHandles[i]; exposed[h] = true;
            if (!seen[h]) { seen[h] = true; queue[tail++] = h; }
        }
        for (uint256 head; head < tail; ++head) {
            uint256 h = queue[head];
            if (_heapKindAt(s.arena.heap.metadata[h]) == HEAP_ARRAY) {
                if (!_arrayHasReferenceComponents(
                    s.arena.heap.ranks[h], s.arena.heap.metadata[h]
                )) continue;
                for (uint256 j; j < s.arena.heap.arrayHeap[h].length; ++j) {
                    uint256 child = uint32(s.arena.heap.arrayHeap[h][j]);
                    if (child == 0) continue; exposed[child] = true;
                    if (!seen[child]) { seen[child] = true; queue[tail++] = child; }
                }
            } else {
                for (uint256 j; j < s.arena.heap.objectHeap[h].length; ++j) {
                    uint256 cell = s.arena.heap.objectHeap[h][j];
                    if (_valueKind(cell) != KIND_REF) continue;
                    uint256 child = _payload(cell); if (child == 0) continue;
                    // String.value is immutable backing, not publication of a Java String.
                    if (!(s.arena.heap.classes[h] == s.arena.stringClass
                        && j == s.arena.stringValueOffset)) exposed[child] = true;
                    if (!seen[child]) { seen[child] = true; queue[tail++] = child; }
                }
            }
        }
        for (uint256 h = 1; h <= s.nextHandle; ++h) {
            if (isDefault[h] && exposed[h]) revert LC0StateError(7, 0);
        }
    }

    function _validateStringBackingAliases(
        Program memory p, RuntimeState memory s, bool[] memory isBacking
    ) private pure {
        for (uint256 ci; ci < p.classes.length; ++ci) for (uint256 j; j < p.classes[ci].fields.length; ++j) {
            uint256 cell = s.staticValues[ci][j];
            if ((p.classes[ci].fields[j].accessFlags & 0x0008) != 0
                && _valueKind(cell) == KIND_REF && _payload(cell) <= s.nextHandle
                && isBacking[_payload(cell)]) revert LC0StateError(7, 0);
        }
        for (uint256 h = 1; h <= s.nextHandle; ++h) {
            if (_heapKindAt(s.arena.heap.metadata[h]) == HEAP_ARRAY) {
                if (_arrayHasReferenceComponents(s.arena.heap.ranks[h], s.arena.heap.metadata[h])) {
                    for (uint256 j; j < s.arena.heap.arrayHeap[h].length; ++j) {
                        uint256 ref = uint32(s.arena.heap.arrayHeap[h][j]);
                        if (ref <= s.nextHandle && isBacking[ref]) revert LC0StateError(7, 0);
                    }
                }
            } else for (uint256 j; j < s.arena.heap.objectHeap[h].length; ++j) {
                if (s.arena.heap.classes[h] == s.arena.stringClass
                    && j == s.arena.stringValueOffset) continue;
                uint256 cell = s.arena.heap.objectHeap[h][j];
                if (_valueKind(cell) == KIND_REF && _payload(cell) <= s.nextHandle
                    && isBacking[_payload(cell)]) revert LC0StateError(7, 0);
            }
        }
        for (uint256 i; i < s.depth; ++i) {
            Frame memory f = s.frames[i];
            uint8 ctorKind = _activeStringConstructorKind(p, f);
            uint256 allowed;
            if (ctorKind == 1 && f.locals.length > 2 && f.initialized[2]
                && _valueKind(f.locals[2]) == KIND_REF) allowed = _payload(f.locals[2]);
            if (ctorKind == 2 && f.locals.length > 1 && f.initialized[1]
                && _valueKind(f.locals[1]) == KIND_REF && _payload(f.locals[1]) != 0) {
                allowed = _payload(s.arena.heap.objectHeap[_payload(f.locals[1])][s.arena.stringValueOffset]);
            }
            for (uint256 j; j < f.locals.length; ++j) if (f.initialized[j]) {
                uint256 cell = f.locals[j];
                if (_valueKind(cell) == KIND_REF && _payload(cell) <= s.nextHandle
                    && isBacking[_payload(cell)]
                    && !(ctorKind == 1 && j == 2 && _payload(cell) == allowed)) {
                    revert LC0StateError(7, 0);
                }
            }
            for (uint256 j; j < f.sp; ++j) {
                uint256 cell = f.stack[j];
                if (_valueKind(cell) != KIND_REF || _payload(cell) > s.nextHandle
                    || !isBacking[_payload(cell)]) continue;
                bool permitted = (ctorKind == 1 && _payload(cell) == allowed)
                    || (ctorKind == 2 && f.pc == 9 && j + 1 == f.sp
                        && _payload(cell) == allowed);
                // At char-constructor pc8 the just-allocated destination has not
                // reached local2 yet, but is the sole top-stack temporary.
                if (ctorKind == 1 && f.pc == 8 && j + 1 == f.sp) permitted = true;
                if (!permitted) revert LC0StateError(7, 0);
            }
        }
    }

    function _requireCellBytes(bytes memory data, uint256 at, uint256 count,
        uint256 width, uint256 base) private pure {
        uint256 available = (data.length - at) / width;
        if (count > available) revert LC0StateError(2, base + at + available * width);
    }

    // EVM-derived declaration identities in physical base-first field order.
    // Cache once per dynamic class; do not rebuild a default object for every record.
    function _checkpointFieldLayout(Program memory p, RuntimeState memory s,
        uint256 ci, uint256 count) private pure returns (uint256[] memory layout) {
        layout = new uint256[](count);
        uint256[] memory chain = new uint256[](p.classes.length);
        uint256 depth;
        uint256 current = ci;
        while (true) {
            chain[depth++] = current;
            uint256 link = s.parentLinks[current];
            if (link == 0 || link == type(uint256).max) break;
            current = link - 1;
        }
        uint256 slot;
        while (depth != 0) {
            current = chain[--depth];
            for (uint256 j; j < p.classes[current].fields.length; ++j) {
                if ((p.classes[current].fields[j].accessFlags & 0x0008) == 0) {
                    layout[slot++] = (current << 128) | j;
                }
            }
        }
        if (slot != count) revert LC0StateError(6, 0);
    }

    function _checkCheckpointField(Program memory p, RuntimeState memory s,
        uint256 owner, uint256 field, uint256 value, uint256 errorCode) private pure {
        ClassInfo memory c = p.classes[owner];
        FieldInfo memory f = c.fields[field];
        uint8 kind = _fieldKind(c, f);
        if (_valueKind(value) != kind) revert LC0StateError(errorCode, 0);
        if (kind == KIND_INT) {
            uint32 bits = uint32(_payload(value));
            if (_normalizeInt(bits, _fieldSubtype(c, f)) != bits) revert LC0StateError(errorCode, 0);
        } else if (kind == KIND_REF) {
            (uint256 off, uint256 n) = _utf(c.cp[f.descriptorIndex]);
            if (!_checkpointReferenceFits(p, s, value, c.data, off, n)) revert LC0StateError(errorCode, 0);
        }
    }

    function _checkpointReferenceFits(Program memory p, RuntimeState memory s,
        uint256 value, bytes memory data, uint256 off, uint256 n) private pure returns (bool) {
        uint256 h = _payload(value);
        // As in the base interpreter, a null/default field does not resolve a
        // dormant target class merely for checkpoint validation.
        if (h == 0) return true;
        if (h > s.nextHandle || _heapKindAt(s.arena.heap.metadata[h]) == 0) return false;
        if (n != 0 && uint8(data[off]) == 0x5b) {
            (bool structural, bool supported, uint8 rank, uint8 primitive,
                uint256 nameOff, uint256 nameLen) = _arrayClassShape(data, off, n);
            if (!structural || !supported || _heapKindAt(s.arena.heap.metadata[h]) != HEAP_ARRAY) return false;
            uint256 leaf = primitive;
            if (primitive == 0) {
                (bool found, uint256 target) = _findClass(p.classes, data, nameOff, nameLen);
                if (!found) return false;
                _validateHierarchy(p.classes, target, s.parentLinks, s.hierarchyState);
                leaf = ARRAY_CLASS_BASE + target;
            }
            return _arrayTypeAssignable(p.classes, s.arena.heap.ranks[h], s.arena.heap.metadata[h],
                rank, leaf, s.parentLinks);
        }
        if (n < 3 || uint8(data[off]) != 0x4c || uint8(data[off + n - 1]) != 0x3b) return false;
        (bool found, uint256 target) = _findClass(p.classes, data, off + 1, n - 2);
        if (!found) return false;
        _validateHierarchy(p.classes, target, s.parentLinks, s.hierarchyState);
        if (_heapKindAt(s.arena.heap.metadata[h]) == HEAP_ARRAY) return _arrayImplementsClass(p.classes, target);
        return _typeAssignable(p.classes, s.arena.heap.classes[h], target, s.parentLinks);
    }

    function _validateInitAndFrames(
        Program memory p, RuntimeState memory s, bool restoredCheckpoint
    ) private pure {
        bool[] memory hasContinuation = new bool[](p.classes.length);
        bool[] memory hasInitializer = new bool[](p.classes.length);
        for (uint256 i; i < s.depth; ++i) {
            Frame memory f = s.frames[i];
            if (f.isInitContinuation) {
                if (s.initializationState[f.classIndex] != 1) revert LC0StateError(7, 0);
                hasContinuation[f.classIndex] = true;
                continue;
            }
            if (i == 0 && (f.classIndex != p.rootClass || f.methodIndex != p.rootMethod)) {
                revert LC0StateError(5, 0);
            }
            if (i != 0 && !f.entered) revert LC0StateError(5, 0);
            if (f.isInitializer) {
                if (p.classes[f.classIndex].initializerPlusOne == 0
                    || f.methodIndex + 1 != p.classes[f.classIndex].initializerPlusOne
                    || s.initializationState[f.classIndex] != 1
                    || !s.initializerStarted[f.classIndex]) revert LC0StateError(7, 0);
                hasInitializer[f.classIndex] = true;
            }
            if (f.isConstructorLinked && !f.isConstructor) revert LC0StateError(5, 0);
            if (f.isConstructor) {
                if (f.thisHandle == 0 || f.thisHandle > s.nextHandle
                    || _heapKindAt(s.arena.heap.metadata[f.thisHandle]) != HEAP_OBJECT
                    || (s.arena.heap.metadata[f.thisHandle] & 0xff) != 0) {
                    revert LC0StateError(5, 0);
                }
            } else if (f.thisHandle != 0) {
                // The base dispatcher retains thisHandle on ordinary private/
                // superclass invokespecial frames as well as constructors.
                // Validate that retained receiver instead of rejecting the state
                // produced by a legitimate special call. Local slot zero is mutable
                // bytecode storage, not an immutable receiver identity: istore_0 or
                // astore_0 may overwrite it after entry while thisHandle is retained.
                if (f.isInitializer || (uint16(p.classes[f.classIndex].methods[f.methodIndex]) & 0x0008) != 0
                    || _heapKindAt(s.arena.heap.metadata[f.thisHandle]) != HEAP_OBJECT
                    || !_typeAssignable(p.classes, s.arena.heap.classes[f.thisHandle],
                        f.classIndex, s.parentLinks)) revert LC0StateError(5, 0);
            }
            // Only the top frame is at an executable opcode boundary. A suspended
            // caller may already point at athrow while its constructor callee still
            // legitimately owns UNINIT duplicates of the eventual receiver.
            if (i + 1 == s.depth && !s.arena.pending.active) {
                _validateAthrowBoundary(p, s, f, restoredCheckpoint);
            }
        }
        for (uint256 i; i < p.classes.length; ++i) {
            uint8 init = s.initializationState[i];
            if (s.initializerStarted[i] && p.classes[i].initializerPlusOne == 0) {
                revert LC0StateError(7, 0);
            }
            if (init == 0) {
                if (s.initializerStarted[i] || hasContinuation[i] || hasInitializer[i]) {
                    revert LC0StateError(7, 0);
                }
                // State zero precedes preparation; all static cells remain their
                // descriptor defaults (ConstantValue/String work starts in init).
                for (uint256 j; j < p.classes[i].fields.length; ++j) {
                    uint8 k = _fieldKind(p.classes[i], p.classes[i].fields[j]);
                    uint256 expected = k == KIND_INT ? _packInt(0)
                        : (k == KIND_REF ? _packRef(0) : (k == KIND_LONG ? _packLong(0)
                        : (k == KIND_FLOAT ? _packFloat(0) : _packDouble(0))));
                    if (s.staticValues[i][j] != expected) revert LC0StateError(7, 0);
                }
            } else if (init == 1) {
                if (!hasContinuation[i] && !hasInitializer[i]) revert LC0StateError(7, 0);
            } else if (hasContinuation[i] || hasInitializer[i]) {
                revert LC0StateError(7, 0);
            }
        }
        if (s.depth != 0 && !s.frames[0].entered) {
            bool initializingRoot;
            for (uint256 i; i < p.classes.length; ++i) {
                if (s.initializationState[i] == 1) initializingRoot = true;
            }
            if (!initializingRoot) revert LC0StateError(7, 0);
        }
    }

    function _validateInitialMainRoot(Program memory p, RuntimeState memory s) private pure {
        Frame memory root = s.frames[0];
        if (root.locals.length == 0 || !root.initialized[0] || _valueKind(root.locals[0]) != KIND_REF) revert LC0StateError(7, 0);
        uint256 h = _payload(root.locals[0]);
        if (h == 0 || h > s.nextHandle || _heapKindAt(s.arena.heap.metadata[h]) != HEAP_ARRAY
            || s.arena.heap.ranks[h] != 1 || s.arena.heap.metadata[h] != ARRAY_CLASS_BASE + s.arena.stringClass
            || s.arena.heap.arrayHeap[h].length != 0) revert LC0StateError(7, 0);
    }

    function _validateAthrowBoundary(
        Program memory p, RuntimeState memory s, Frame memory f, bool restoredCheckpoint
    ) private pure {
        Selected memory sel = p.selected[f.classIndex][f.methodIndex][0];
        if (!sel.loaded || f.pc >= sel.codeLength
            || uint8(p.classes[f.classIndex].data[sel.codeOffset + f.pc]) != 0xbf) return;
        if (f.sp == 0 || _valueKind(f.stack[f.sp - 1]) != KIND_REF) {
            if (restoredCheckpoint) revert LC0StateError(5, 0);
            // A checkpoint boundary must not relabel the guest's hard bytecode
            // error just because a different quantum reaches this PC first.
            revert BytecodeError(f.sp == 0 ? 3 : 14, f.pc);
        }
        uint256 ref = _payload(f.stack[f.sp - 1]);
        if (ref == 0) return; // executing athrow null deterministically raises NPE.
        if (ref > s.nextHandle
            || _heapKindAt(s.arena.heap.metadata[ref]) != HEAP_OBJECT
            || !_typeAssignable(p.classes, s.arena.heap.classes[ref],
                s.arena.throwableClass, s.parentLinks)) {
            if (restoredCheckpoint) revert LC0StateError(7, 0);
            revert BytecodeError(14, f.pc);
        }
    }

    function _validArrayLeaf(uint8 rank, uint256 leaf, uint256 classCount)
        private pure returns (bool)
    {
        if (rank == 0 || (leaf & HEAP_OBJECT_MARKER) != 0) return false;
        if (leaf >= ARRAY_CLASS_BASE) return leaf - ARRAY_CLASS_BASE < classCount;
        return leaf == PRIMITIVE_BOOLEAN || leaf == PRIMITIVE_BYTE || leaf == PRIMITIVE_CHAR
            || leaf == PRIMITIVE_SHORT || leaf == PRIMITIVE_INT || leaf == PRIMITIVE_LONG
            || leaf == PRIMITIVE_FLOAT || leaf == PRIMITIVE_DOUBLE;
    }

    function _checkRefCell(uint256 cell, uint256[] memory meta, uint256 nextHandle) private pure {
        uint256 k = _valueKind(cell);
        if (k != KIND_REF && k != KIND_UNINIT) return;
        uint256 h = uint32(cell);
        if (h != 0 && (h > nextHandle || meta.length == 0 || _heapKindAt(meta[h]) == 0)) {
            revert LC0StateError(6, 0);
        }
    }

    function _checkValueShape(uint256 value, bool locals, uint256 off) private pure {
        uint256 k = _valueKind(value);
        if (k == 0 || k > KIND_DOUBLE_TAIL || (!locals && (k == KIND_LONG_TAIL || k == KIND_DOUBLE_TAIL))) {
            revert LC0StateError(5, off);
        }
        uint256 payload = uint64(value);
        if ((k == KIND_INT || k == KIND_REF || k == KIND_UNINIT || k == KIND_FLOAT)
            && payload > type(uint32).max) revert LC0StateError(5, off);
        if ((k == KIND_LONG_TAIL || k == KIND_DOUBLE_TAIL) && payload != 0) {
            revert LC0StateError(5, off);
        }
    }

    function _checkLocalCategories(Frame memory f, uint256 off) private pure {
        for (uint256 i; i < f.locals.length; ++i) {
            if (!f.initialized[i]) continue;
            uint256 k = _valueKind(f.locals[i]);
            if (k == KIND_LONG || k == KIND_DOUBLE) {
                uint256 tail = k == KIND_LONG ? KIND_LONG_TAIL : KIND_DOUBLE_TAIL;
                if (i + 1 >= f.locals.length || !f.initialized[i + 1]
                    || _valueKind(f.locals[i + 1]) != tail) revert LC0StateError(5, off);
            } else if (k == KIND_LONG_TAIL || k == KIND_DOUBLE_TAIL) {
                uint256 head = k == KIND_LONG_TAIL ? KIND_LONG : KIND_DOUBLE;
                if (i == 0 || !f.initialized[i - 1] || _valueKind(f.locals[i - 1]) != head) {
                    revert LC0StateError(5, off);
                }
            }
        }
    }

    function _preludeEnd(bytes memory data, uint256 base) private pure returns (uint256 at) {
        at = 63;
        (, at) = _getBytes16(data, at, base);
        (, at) = _getBytes16(data, at, base);
        (uint256 argc, uint256 n) = _get(data, at, 1, base); at = n;
        if (argc > 8) revert LC0StateError(4, base + at - 1);
        if (at > data.length || data.length - at < argc * 4) revert LC0StateError(2, base + at);
        at += argc * 4;
    }

    function _getBytes16(bytes memory data, uint256 at, uint256 base)
        private pure returns (bytes memory value, uint256 next)
    {
        (uint256 length, uint256 n) = _get(data, at, 2, base);
        if (n > data.length || data.length - n < length) revert LC0StateError(2, base + n);
        value = new bytes(length);
        for (uint256 i; i < length; ++i) value[i] = data[n + i];
        next = n + length;
    }

    function _ascii(bytes memory value) private pure returns (bool) {
        for (uint256 i; i < value.length; ++i) {
            uint8 c = uint8(value[i]);
            if (c == 0 || c > 0x7f) return false;
        }
        return true;
    }

    function _parseBundleClass(bytes memory rawClass) private pure returns (ClassInfo memory c) {
        c.data = rawClass;
        Reader memory r = Reader(c.data, 0);
        if (_u4(r) != 0xcafebabe) revert ClassError(1, 0);
        _u2(r);
        _u2(r);
        c.cp = _readConstantPool(r);

        c.accessFlags = _u2(r);
        uint256 thisClass = _u2(r);
        uint256 superClass = _u2(r);
        (c.thisNameOffset, c.thisNameLength) = _className(c, thisClass, r.pos);
        if (superClass != 0) {
            (c.superNameOffset, c.superNameLength) = _className(c, superClass, r.pos);
            c.hasSuperclass = true;
        }
        if ((c.accessFlags & 0x0200) == 0 && (c.accessFlags & 0xe000) != 0) {
            c.unsupportedSemantics = true;
        }

        uint256 interfacesCount = _u2(r);
        c.interfaces = new uint16[](interfacesCount);
        for (uint256 i = 0; i < interfacesCount; ++i) c.interfaces[i] = _u2(r);
        c.fields = _readFields(r, c);

        uint256 methodsCount = _u2(r);
        c.methods = new uint256[](methodsCount);
        for (uint256 m = 0; m < methodsCount; ++m) {
            uint16 access = _u2(r);
            uint256 nameIndex = _u2(r);
            uint256 descriptorIndex = _u2(r);
            uint256 attributesCount = _u2(r);
            _validUtf8(nameIndex, c.cp, r.pos);
            _validUtf8(descriptorIndex, c.cp, r.pos);
            (uint256 nameOffset, uint256 nameLength) = _utf(c.cp[nameIndex]);
            if (_equalsLiteral(c.data, nameOffset, nameLength, bytes("<clinit>"))) {
                if (c.initializerPlusOne != 0) c.invalidInitializer = true;
                else c.initializerPlusOne = m + 1;
            }
            uint256 packed = uint256(access) | (nameIndex << 16) | (descriptorIndex << 32);
            uint256 codeCount;
            for (uint256 a = 0; a < attributesCount; ++a) {
                uint256 attributeNameIndex = _u2(r);
                uint256 attributeLength = _u4(r);
                _validUtf8(attributeNameIndex, c.cp, r.pos);
                uint256 attributeStart = r.pos;
                _skip(r, attributeLength);
                (uint256 attributeNameOffset, uint256 attributeNameLength) =
                    _utf(c.cp[attributeNameIndex]);
                if (_equalsLiteral(c.data, attributeNameOffset, attributeNameLength, bytes("Code"))) {
                    ++codeCount;
                    if (codeCount == 1) {
                        packed |= attributeStart << 48;
                        packed |= attributeLength << 112;
                    }
                }
            }
            packed |= codeCount << 144;
            c.methods[m] = packed;
        }
        _skipAttributes(r);
        if (r.pos != c.data.length) revert ClassError(5, r.pos);
    }

    function _requireSupportedClass(ClassInfo memory c, uint256 classIndex) private pure {
        if (c.unsupportedSemantics) revert LinkError(5, classIndex);
    }

    function _sameClassName(ClassInfo memory a, ClassInfo memory b) private pure returns (bool) {
        if (a.thisNameLength != b.thisNameLength) return false;
        for (uint256 i = 0; i < a.thisNameLength; ++i) {
            if (a.data[a.thisNameOffset + i] != b.data[b.thisNameOffset + i]) return false;
        }
        return true;
    }

    function _isObjectClass(ClassInfo memory c) private pure returns (bool) {
        return _equalsLiteral(c.data, c.thisNameOffset, c.thisNameLength, bytes("java/lang/Object"));
    }

    function _isNamedClass(ClassInfo memory c, bytes memory name) private pure returns (bool) {
        return _equalsLiteral(c.data, c.thisNameOffset, c.thisNameLength, name);
    }

    function _isInterface(ClassInfo memory c) private pure returns (bool) {
        return (c.accessFlags & 0x0200) != 0;
    }

    function _isReservedStringProfileClass(ClassInfo memory c) private pure returns (bool) {
        return _isNamedClass(c, bytes("java/lang/String"))
            || _isNamedClass(c, bytes("java/lang/Comparable"))
            || _isNamedClass(c, bytes("java/lang/CharSequence"));
    }

    function _isReservedClassLiteralProfileClass(ClassInfo memory c) private pure returns (bool) {
        return _isNamedClass(c, bytes("java/lang/Class"));
    }

    function _isReservedPlatformMapClass(ClassInfo memory c) private pure returns (bool) {
        return _isNamedClass(c, bytes("java/util/Map"))
            || _isNamedClass(c, bytes("java/util/concurrent/ConcurrentMap"))
            || _isNamedClass(c, bytes("java/util/AbstractMap"))
            || _isNamedClass(c, bytes("java/util/concurrent/ConcurrentHashMap"));
    }

    function _isReservedSystemClass(ClassInfo memory c) private pure returns (bool) {
        return _isNamedClass(c, bytes("java/lang/System"));
    }

    // These classes are interpreter-owned images, not user-supplied platform
    // definitions. This prevents an input bundle from silently replacing the
    // construction/storage hierarchy used by original Properties allocation.
    function _isReservedPropertiesClass(ClassInfo memory c) private pure returns (bool) {
        return _isNamedClass(c, bytes("java/util/Dictionary"))
            || _isNamedClass(c, bytes("java/util/Hashtable"))
            || _isNamedClass(c, bytes("java/util/Properties"));
    }

    function _isReservedVFSClass(ClassInfo memory c) private pure returns (bool) {
        return _isNamedClass(c, bytes("java/lang/AutoCloseable"))
            || _isNamedClass(c, bytes("java/io/Closeable"))
            || _isNamedClass(c, bytes("java/io/Flushable"))
            || _isNamedClass(c, bytes("java/io/File"))
            || _isNamedClass(c, bytes("java/io/InputStream"))
            || _isNamedClass(c, bytes("java/io/OutputStream"))
            || _isNamedClass(c, bytes("java/io/FileInputStream"))
            || _isNamedClass(c, bytes("java/io/FileOutputStream"));
    }

    function _isStringProfileSymbolic(ClassInfo memory c) private pure returns (bool) {
        return _isNamedClass(c, bytes("java/lang/String"))
            || _isNamedClass(c, bytes("java/lang/Comparable"))
            || _isNamedClass(c, bytes("java/lang/CharSequence"));
    }

    function _isReservedThrowableClass(ClassInfo memory c) private pure returns (bool) {
        bytes memory d = c.data;
        uint256 o = c.thisNameOffset;
        uint256 n = c.thisNameLength;
        return _equalsLiteral(d, o, n, bytes("java/lang/Throwable"))
            || _equalsLiteral(d, o, n, bytes("java/lang/Error"))
            || _equalsLiteral(d, o, n, bytes("java/lang/VirtualMachineError"))
            || _equalsLiteral(d, o, n, bytes("java/lang/StackOverflowError"))
            || _equalsLiteral(d, o, n, bytes("java/lang/OutOfMemoryError"))
            || _equalsLiteral(d, o, n, bytes("java/lang/LinkageError"))
            || _equalsLiteral(d, o, n, bytes("java/lang/ExceptionInInitializerError"))
            || _equalsLiteral(d, o, n, bytes("java/lang/IncompatibleClassChangeError"))
            || _equalsLiteral(d, o, n, bytes("java/lang/NoClassDefFoundError"))
            || _equalsLiteral(d, o, n, bytes("java/lang/AbstractMethodError"))
            || _equalsLiteral(d, o, n, bytes("java/lang/Exception"))
            || _equalsLiteral(d, o, n, bytes("java/lang/RuntimeException"))
            || _equalsLiteral(d, o, n, bytes("java/lang/ArithmeticException"))
            || _equalsLiteral(d, o, n, bytes("java/lang/NullPointerException"))
            || _equalsLiteral(d, o, n, bytes("java/lang/NegativeArraySizeException"))
            || _equalsLiteral(d, o, n, bytes("java/lang/ClassCastException"))
            || _equalsLiteral(d, o, n, bytes("java/lang/ArrayStoreException"))
            || _equalsLiteral(d, o, n, bytes("java/lang/IndexOutOfBoundsException"))
            || _equalsLiteral(d, o, n, bytes("java/lang/ArrayIndexOutOfBoundsException"))
            || _equalsLiteral(d, o, n, bytes("java/io/IOException"))
            || _equalsLiteral(d, o, n, bytes("java/io/FileNotFoundException"))
            || _equalsLiteral(d, o, n, bytes("java/io/EOFException"));
    }

    function _missingClass(uint256 site, uint256 context, bytes memory data, uint256 off, uint256 n)
        private pure
    {
        bytes memory name = new bytes(n);
        for (uint256 i; i < n; ++i) name[i] = data[off + i];
        revert MCEntryMissingClass(site, context, name);
    }

    function _findClass(
        ClassInfo[] memory classes, bytes memory nameData, uint256 nameOffset, uint256 nameLength
    ) private pure returns (bool found, uint256 classIndex) {
        for (uint256 i = 0; i < classes.length; ++i) {
            // Canonical Throwable images occupy raw-only slots until resolution
            // reaches them. They still go through the ordinary in-EVM parser.
            if (classes[i].cp.length == 0 && classes[i].data.length != 0) {
                classes[i] = _parseBundleClass(classes[i].data);
            }
            if (_equalsCross(nameData, nameOffset, nameLength, classes[i].data,
                classes[i].thisNameOffset, classes[i].thisNameLength)) return (true, i);
        }
    }

    function _readConstantPool(Reader memory r) private pure returns (uint256[] memory cp) {
        uint256 cpCount = _u2(r);
        if (cpCount == 0 || cpCount > MAX_CONSTANT_POOL || cpCount > r.data.length) {
            revert ClassError(2, r.pos);
        }
        cp = new uint256[](cpCount);
        for (uint256 i = 1; i < cpCount; ++i) {
            uint8 tag = _u1(r);
            if (tag == 1) { // CONSTANT_Utf8
                uint256 n = _u2(r);
                cp[i] = uint256(tag) | (r.pos << 8) | (n << 72);
                _skip(r, n);
            } else if (tag == 3 || tag == 4) {
                cp[i] = uint256(tag) | (uint256(_u4(r)) << 8);
            } else if (tag == 5 || tag == 6) {
                uint256 high = _u4(r);
                uint256 low = _u4(r);
                cp[i] = uint256(tag) | (high << 40) | (low << 8);
                if (i + 1 >= cpCount) revert ClassError(3, r.pos);
                ++i;
            } else if (tag == 7 || tag == 8 || tag == 16 || tag == 19 || tag == 20) {
                cp[i] = uint256(tag) | (uint256(_u2(r)) << 8);
            } else if (
                tag == 9 || tag == 10 || tag == 11 || tag == 12 || tag == 17 || tag == 18
            ) {
                uint256 first = _u2(r);
                uint256 second = _u2(r);
                cp[i] = uint256(tag) | (first << 8) | (second << 24);
            } else if (tag == 15) {
                uint256 kind = _u1(r);
                uint256 index = _u2(r);
                cp[i] = uint256(tag) | (kind << 8) | (index << 16);
            } else {
                revert ClassError(4, r.pos - 1);
            }
        }
    }

    function _loadRoot(
        ClassInfo memory c, uint256 meta, uint256 classIndex, uint256 methodIndex
    ) private pure returns (Selected memory s) {
        s.declaringClass = classIndex;
        s.methodIndex = methodIndex;
        uint256 descriptorIndex = (meta >> 32) & 0xffff;
        (s.descriptorOffset, s.descriptorLength) = _utf(c.cp[descriptorIndex]);
        if (!_descriptor(c.data, s.descriptorOffset, s.descriptorLength, s)
            || !_isMainEmptyStringArrayRoot(c, s)) revert MethodError(11);
        s.argumentCount = s.argumentKinds.length;
        uint256 start = (meta >> 48) & 0xffffffffffffffff;
        uint256 length = (meta >> 112) & 0xffffffff;
        _readCode(c, start, length, s);
        if (s.maxStack > MAX_STACK) revert BytecodeError(1, 0);
        if (s.maxLocals > MAX_LOCALS) revert BytecodeError(10, 0);
        s.loaded = true;
    }

    function _loadCallee(
        ClassInfo memory c, uint256 method, uint256 callPC, uint256 classIndex
    ) private pure returns (Selected memory s) {
        s.declaringClass = classIndex;
        s.methodIndex = method;
        uint256 meta = c.methods[method];
        uint16 access = uint16(meta);
        if (
            (access & 0x0008) == 0 || (access & (0x0020 | 0x0100 | 0x0400)) != 0
                || _methodCodeCount(meta) != 1
        ) revert CallError(4, callPC);
        uint256 descriptorIndex = (meta >> 32) & 0xffff;
        (s.descriptorOffset, s.descriptorLength) = _utf(c.cp[descriptorIndex]);
        if (!_descriptor(c.data, s.descriptorOffset, s.descriptorLength, s)) {
            revert CallError(4, callPC);
        }
        s.argumentCount = s.argumentKinds.length;
        uint256 start = (meta >> 48) & 0xffffffffffffffff;
        uint256 length = (meta >> 112) & 0xffffffff;
        if (!_readCallCode(c, start, length, s)) revert CallError(4, callPC);
        if (s.maxStack > MAX_STACK || s.maxLocals > MAX_LOCALS || s.maxLocals < s.argumentWords) {
            revert CallError(4, callPC);
        }
        s.loaded = true;
    }

    function _guardCanonicalThrowableGetter(
        ClassInfo[] memory classes, uint256 calleeClass, uint256 callee,
        uint256 receiverRef, ExceptionArena memory arena, uint256 invokePC
    ) private pure {
        if (calleeClass != arena.throwableClass) return;
        ClassInfo memory c = classes[calleeClass];
        uint256 meta = c.methods[callee];
        (uint256 no, uint256 nn) = _utf(c.cp[(meta >> 16) & 0xffff]);
        (uint256 doff, uint256 dn) = _utf(c.cp[(meta >> 32) & 0xffff]);
        bool getMessage = _equalsLiteral(c.data, no, nn, bytes("getMessage"))
            && _equalsLiteral(c.data, doff, dn, bytes("()Ljava/lang/String;"));
        bool getCause = _equalsLiteral(c.data, no, nn, bytes("getCause"))
            && _equalsLiteral(c.data, doff, dn, bytes("()Ljava/lang/Throwable;"));
        if (!getMessage && !getCause) return;
        uint256 kind = arena.heap.metadata[receiverRef] & 0xff;
        if (kind == 0 || kind == 6 || kind == 3 || (kind == 1 && getCause)) return;
        revert ThrowableAPIProfileError(kind, invokePC);
    }

    function _vfsMemberRefMatches(
        ClassInfo memory c, uint256 refIndex, uint8 tag, bytes memory name,
        bytes memory descriptor
    ) private pure returns (bool) {
        if (refIndex == 0 || refIndex >= c.cp.length || uint8(c.cp[refIndex]) != tag) return false;
        uint256 ref = c.cp[refIndex];
        uint256 ownerClassIndex = (ref >> 8) & 0xffff;
        uint256 natIndex = (ref >> 24) & 0xffff;
        if (ownerClassIndex == 0 || ownerClassIndex >= c.cp.length
            || uint8(c.cp[ownerClassIndex]) != 7 || natIndex == 0 || natIndex >= c.cp.length
            || uint8(c.cp[natIndex]) != 12) return false;
        uint256 ownerNameIndex = (c.cp[ownerClassIndex] >> 8) & 0xffff;
        uint256 nameIndex = (c.cp[natIndex] >> 8) & 0xffff;
        uint256 descriptorIndex = (c.cp[natIndex] >> 24) & 0xffff;
        if (ownerNameIndex == 0 || ownerNameIndex >= c.cp.length
            || nameIndex == 0 || nameIndex >= c.cp.length
            || descriptorIndex == 0 || descriptorIndex >= c.cp.length
            || uint8(c.cp[ownerNameIndex]) != 1 || uint8(c.cp[nameIndex]) != 1
            || uint8(c.cp[descriptorIndex]) != 1) return false;
        (uint256 oo, uint256 on) = _utf(c.cp[ownerNameIndex]);
        (uint256 no, uint256 nn) = _utf(c.cp[nameIndex]);
        (uint256 doff, uint256 dn) = _utf(c.cp[descriptorIndex]);
        return _equalsCross(c.data, oo, on, c.data, c.thisNameOffset, c.thisNameLength)
            && _equalsLiteral(c.data, no, nn, name)
            && _equalsLiteral(c.data, doff, dn, descriptor);
    }

    // Derive every pending-bind PC from the parsed reserved constructor Code. The
    // image itself is pinned, but neither serialized PCs nor old numeric constants
    // are treated as authority after a Java image revision.
    function _vfsBindPlan(ClassInfo[] memory classes, uint256 streamClass, bool input)
        private pure returns (VFSBindPlan memory plan)
    {
        ClassInfo memory c = classes[streamClass];
        bytes memory ctorDescriptor = input
            ? bytes("(Ljava/io/File;)V") : bytes("(Ljava/io/File;Z)V");
        uint256 found;
        for (uint256 i; i < c.methods.length; ++i) {
            uint256 meta = c.methods[i];
            (uint256 no, uint256 nn) = _utf(c.cp[(meta >> 16) & 0xffff]);
            (uint256 doff, uint256 dn) = _utf(c.cp[(meta >> 32) & 0xffff]);
            if (_equalsLiteral(c.data, no, nn, bytes("<init>"))
                && _equalsLiteral(c.data, doff, dn, ctorDescriptor)) {
                if (found != 0 || uint16(meta) != 0x0001 || _methodCodeCount(meta) != 1) {
                    revert VFS0aProfileError(4, 0);
                }
                found = i + 1;
            }
        }
        if (found == 0) revert VFS0aProfileError(4, 0);
        plan.method = found - 1;
        Selected memory sel = _loadSpecialCallee(c, plan.method, 0, true, streamClass);
        if (sel.maxStack != 4 || sel.maxLocals != (input ? 3 : 4)) {
            revert VFS0aProfileError(4, 0);
        }
        uint8 local = input ? 2 : 3;
        uint8 storeOp = uint8(0x3b + local);
        uint8 loadOp = uint8(0x1a + local);
        uint256 matched;
        for (uint256 at; at < sel.codeLength;) {
            uint8 op = uint8(c.data[sel.codeOffset + at]);
            uint256 width = _instructionWidth(c.data, sel.codeOffset, sel.codeLength, op, at);
            if (op == 0xb7 && _vfsMemberRefMatches(
                c, _unsigned16(c.data, sel.codeOffset + at + 1), 10,
                bytes("open0"), input ? bytes("(Ljava/io/File;)I")
                    : bytes("(Ljava/io/File;Z)I")
            )) {
                if (matched != 0 || at + 14 >= sel.codeLength
                    || uint8(c.data[sel.codeOffset + at + 3]) != storeOp
                    || uint8(c.data[sel.codeOffset + at + 4]) != loadOp
                    || uint8(c.data[sel.codeOffset + at + 5]) != 0x9e
                    || _decodedTarget(c.data, sel.codeOffset, at + 5) != at + 14
                    || uint8(c.data[sel.codeOffset + at + 8]) != 0x2a
                    || uint8(c.data[sel.codeOffset + at + 9]) != loadOp
                    || uint8(c.data[sel.codeOffset + at + 10]) != 0xb5
                    || !_vfsMemberRefMatches(
                        c, _unsigned16(c.data, sel.codeOffset + at + 11), 9,
                        bytes("handle"), bytes("I")
                    ) || uint8(c.data[sel.codeOffset + at + 13]) != 0xb1) {
                    revert VFS0aProfileError(4, at);
                }
                matched = at + 1;
            }
            at += width;
        }
        if (matched == 0) revert VFS0aProfileError(4, 0);
        uint32 invokePC = uint32(matched - 1);
        plan.invokePC = invokePC;
        plan.afterInvokePC = invokePC + 3;
        plan.afterStorePC = invokePC + 4;
        plan.afterLoadPC = invokePC + 5;
        plan.successPC = invokePC + 8;
        plan.afterOwnerPC = invokePC + 9;
        plan.putfieldPC = invokePC + 10;
        plan.idLocal = local;
    }

    function _requireVFSOpenFrame(
        ClassInfo[] memory classes, Frame memory f, uint256 owner, uint256 depth,
        uint256 pc, uint256 streamClass, bool input
    ) private pure returns (VFSBindPlan memory plan) {
        plan = _vfsBindPlan(classes, streamClass, input);
        if (depth == 0 || f.classIndex != streamClass || f.methodIndex != plan.method
            || !f.isConstructor || !f.isConstructorLinked || f.thisHandle != owner
            || f.pc != plan.afterInvokePC || pc != plan.invokePC || f.locals.length == 0
            || !f.initialized[0] || _valueKind(f.locals[0]) != KIND_REF
            || _payload(f.locals[0]) != owner) revert VFS0aProfileError(4, pc);
    }

    function _pendingVFSFrameValid(
        Frame memory f, VFSDescriptor memory d, VFSBindPlan memory plan
    ) private pure returns (bool) {
        if (!f.isConstructor || !f.isConstructorLinked || f.methodIndex != plan.method
            || f.thisHandle != d.ownerRef || f.locals.length <= plan.idLocal
            || !f.initialized[0] || _valueKind(f.locals[0]) != KIND_REF
            || _payload(f.locals[0]) != d.ownerRef) return false;
        uint256 idCell;
        if (f.pc == plan.afterInvokePC) {
            if (f.sp != 1 || f.initialized[plan.idLocal]) return false;
            idCell = f.stack[0];
        } else {
            if (!f.initialized[plan.idLocal]) return false;
            idCell = f.locals[plan.idLocal];
            if (f.pc == plan.afterStorePC || f.pc == plan.successPC) {
                if (f.sp != 0) return false;
            } else if (f.pc == plan.afterLoadPC) {
                if (f.sp != 1 || f.stack[0] != idCell) return false;
            } else if (f.pc == plan.afterOwnerPC) {
                if (f.sp != 1 || _valueKind(f.stack[0]) != KIND_REF
                    || _payload(f.stack[0]) != d.ownerRef) return false;
            } else if (f.pc == plan.putfieldPC) {
                if (f.sp != 2 || _valueKind(f.stack[0]) != KIND_REF
                    || _payload(f.stack[0]) != d.ownerRef || f.stack[1] != idCell) return false;
            } else return false;
        }
        return _valueKind(idCell) == KIND_INT && uint32(_payload(idCell)) == d.id;
    }

    function _maybeBindVFSHandle(
        ClassInfo[] memory classes, uint256 fieldClass, uint256 field, uint256 owner,
        uint256 value, Frame memory f, uint256 depth, VFSState memory fs,
        uint256[] memory parentLinks, uint256 pc
    ) private pure {
        ClassInfo memory c = classes[fieldClass];
        if (!_isNamedClass(c, bytes("java/io/FileInputStream"))
            && !_isNamedClass(c, bytes("java/io/FileOutputStream"))) return;
        FieldInfo memory fi = c.fields[field];
        (uint256 no, uint256 nn) = _utf(c.cp[fi.nameIndex]);
        (uint256 doff, uint256 dn) = _utf(c.cp[fi.descriptorIndex]);
        if (!_equalsLiteral(c.data, no, nn, bytes("handle"))
            || !_equalsLiteral(c.data, doff, dn, bytes("I"))) return;
        uint32 id = uint32(_payload(value));
        bool input = _isNamedClass(c, bytes("java/io/FileInputStream"));
        VFSBindPlan memory plan = _vfsBindPlan(classes, fieldClass, input);
        if (!f.isConstructor || !f.isConstructorLinked || f.classIndex != fieldClass
            || f.methodIndex != plan.method || f.thisHandle != owner
            || pc != plan.putfieldPC || id == 0 || depth == 0
            || f.locals.length == 0 || !f.initialized[0]
            || _valueKind(f.locals[0]) != KIND_REF || _payload(f.locals[0]) != owner) {
            revert VFS0aProfileError(4, pc);
        }
        _bindDescriptor(fs, id, uint32(owner), uint16(depth), plan.putfieldPC, pc);
        parentLinks; // field resolution already proved the canonical owner relation.
    }

    function _validateVFSHeap(Program memory p, RuntimeState memory s) private pure {
        _validateVFS(s.vfs, 0);
        uint256 fis = s.arena.stringClass + 10;
        uint256 fos = s.arena.stringClass + 11;
        uint256 fisOffset = _canonicalVFSFieldOffset(
            p.classes, fis, bytes("handle"), bytes("I"), KIND_INT, s.parentLinks, 0
        );
        uint256 fosOffset = _canonicalVFSFieldOffset(
            p.classes, fos, bytes("handle"), bytes("I"), KIND_INT, s.parentLinks, 0
        );
        uint256 pending;
        for (uint256 i; i < s.vfs.descriptors.length; ++i) {
            VFSDescriptor memory d = s.vfs.descriptors[i];
            if (d.ownerRef > s.nextHandle
                || _heapKindAt(s.arena.heap.metadata[d.ownerRef]) != HEAP_OBJECT) {
                revert VFS0aStateError(5, i);
            }
            bool input = d.flags == 1;
            uint256 wanted = input ? fis : fos;
            uint256 offset = input ? fisOffset : fosOffset;
            if (!_typeAssignable(p.classes, s.arena.heap.classes[d.ownerRef], wanted,
                s.parentLinks)) revert VFS0aStateError(5, i);
            uint256 fieldCell = s.arena.heap.objectHeap[d.ownerRef][offset];
            if (_valueKind(fieldCell) != KIND_INT) revert VFS0aStateError(5, i);
            uint32 fieldID = uint32(_payload(fieldCell));
            if (d.phase == 1) {
                ++pending;
                VFSBindPlan memory plan = _vfsBindPlan(p.classes, wanted, input);
                if (fieldID != 0 || d.bindDepth == 0 || d.bindDepth != s.depth
                    || d.bindPC != plan.putfieldPC) revert VFS0aStateError(5, i);
                Frame memory f = s.frames[d.bindDepth - 1];
                if (f.classIndex != wanted || !_pendingVFSFrameValid(f, d, plan)) {
                    revert VFS0aStateError(5, i);
                }
            } else if (fieldID != d.id) revert VFS0aStateError(5, i);
        }
        if (pending > 1) revert VFS0aStateError(5, 0);
        for (uint256 h = 1; h <= s.nextHandle; ++h) {
            if (_heapKindAt(s.arena.heap.metadata[h]) != HEAP_OBJECT) continue;
            uint256 ci = s.arena.heap.classes[h];
            bool input = _typeAssignable(p.classes, ci, fis, s.parentLinks);
            bool output = _typeAssignable(p.classes, ci, fos, s.parentLinks);
            if (!input && !output) continue;
            uint256 offset = input ? fisOffset : fosOffset;
            uint256 fieldCell = s.arena.heap.objectHeap[h][offset];
            if (_valueKind(fieldCell) != KIND_INT) revert VFS0aStateError(5, h);
            uint32 id = uint32(_payload(fieldCell));
            if (id != 0) {
                VFSDescriptor memory d = _descriptor(s.vfs, id, 0);
                if (d.ownerRef != h || d.phase == 1) revert VFS0aStateError(5, h);
            }
        }
    }

    function _vfsNativeBinding(ClassInfo memory c, uint256 method) private pure returns (uint8) {
        uint256 meta = c.methods[method];
        if (uint16(meta) != 0x0102 || _methodCodeCount(meta) != 0) return 0;
        (uint256 no, uint256 nn) = _utf(c.cp[(meta >> 16) & 0xffff]);
        (uint256 doff, uint256 dn) = _utf(c.cp[(meta >> 32) & 0xffff]);
        if (_isNamedClass(c, bytes("java/io/File"))) {
            if (_equalsLiteral(c.data, no, nn, bytes("stat0"))
                && _equalsLiteral(c.data, doff, dn, bytes("()I"))) return 1;
            if (_equalsLiteral(c.data, no, nn, bytes("mkdir0"))
                && _equalsLiteral(c.data, doff, dn, bytes("(Z)I"))) return 2;
        } else if (_isNamedClass(c, bytes("java/io/FileInputStream"))) {
            if (_equalsLiteral(c.data, no, nn, bytes("open0"))
                && _equalsLiteral(c.data, doff, dn, bytes("(Ljava/io/File;)I"))) return 3;
            if (_equalsLiteral(c.data, no, nn, bytes("readOne0"))
                && _equalsLiteral(c.data, doff, dn, bytes("()I"))) return 4;
            if (_equalsLiteral(c.data, no, nn, bytes("read0"))
                && _equalsLiteral(c.data, doff, dn, bytes("([BII)I"))) return 5;
            if (_equalsLiteral(c.data, no, nn, bytes("close0"))
                && _equalsLiteral(c.data, doff, dn, bytes("()I"))) return 6;
        } else if (_isNamedClass(c, bytes("java/io/FileOutputStream"))) {
            if (_equalsLiteral(c.data, no, nn, bytes("open0"))
                && _equalsLiteral(c.data, doff, dn, bytes("(Ljava/io/File;Z)I"))) return 7;
            if (_equalsLiteral(c.data, no, nn, bytes("writeOne0"))
                && _equalsLiteral(c.data, doff, dn, bytes("(I)I"))) return 8;
            if (_equalsLiteral(c.data, no, nn, bytes("write0"))
                && _equalsLiteral(c.data, doff, dn, bytes("([BII)I"))) return 9;
            if (_equalsLiteral(c.data, no, nn, bytes("close0"))
                && _equalsLiteral(c.data, doff, dn, bytes("()I"))) return 10;
        }
    }

    function _loadVFSNativeCallee(
        ClassInfo memory c, uint256 method, uint256 callPC, uint256 classIndex
    ) private pure returns (Selected memory s) {
        if (_vfsNativeBinding(c, method) == 0) revert CallError(4, callPC);
        uint256 meta = c.methods[method];
        (s.descriptorOffset, s.descriptorLength) = _utf(c.cp[(meta >> 32) & 0xffff]);
        if (!_descriptor(c.data, s.descriptorOffset, s.descriptorLength, s)
            || s.returnKind != 1) revert CallError(4, callPC);
        s.argumentCount = s.argumentKinds.length;
        s.declaringClass = classIndex;
        s.methodIndex = method;
        s.loaded = true;
    }

    function _findNamedClassOrFail(ClassInfo[] memory classes, bytes memory name, uint256 pc)
        private pure returns (uint256)
    {
        for (uint256 i; i < classes.length; ++i) {
            if (classes[i].cp.length == 0) classes[i] = _parseBundleClass(classes[i].data);
            if (_isNamedClass(classes[i], name)) return i;
        }
        revert VFS0aProfileError(2, pc);
    }

    function _fileLexicalPath(
        ClassInfo[] memory classes, ExceptionArena memory arena, uint256[] memory parentLinks,
        uint256 fileRef, uint256 pc
    ) private pure returns (bytes memory lexical) {
        uint256 fileClass = arena.stringClass + 7;
        if (fileRef == 0 || fileRef > arena.nextHandle
            || _heapKindAt(arena.heap.metadata[fileRef]) != HEAP_OBJECT
            || !_typeAssignable(classes, arena.heap.classes[fileRef], fileClass, parentLinks)) {
            revert VFS0aProfileError(4, pc);
        }
        uint256 offset = _canonicalFieldOffset(
            classes, fileClass, bytes("path"), bytes("Ljava/lang/String;"),
            parentLinks, pc
        );
        uint256 pathCell = arena.heap.objectHeap[fileRef][offset];
        if (_valueKind(pathCell) != KIND_REF) revert VFS0aProfileError(4, pc);
        uint256 stringRef = _payload(pathCell);
        if (stringRef == 0 || stringRef > arena.nextHandle
            || arena.heap.classes[stringRef] != arena.stringClass) revert VFS0aProfileError(1, pc);
        uint64[] memory units = _stringUnits(arena, stringRef, pc);
        lexical = new bytes(units.length);
        for (uint256 i; i < units.length; ++i) {
            if (units[i] < 0x20 || units[i] > 0x7e) revert VFS0aProfileError(1, pc);
            lexical[i] = bytes1(uint8(units[i]));
        }
        lexical = _lexicalPath(lexical, pc);
        // Validate root escape, component/depth and canonical length bounds without
        // using the collapsed result for Java stat/mkdir/open traversal.
        _canonicalPath(lexical, pc);
        return lexical;
    }

    function _streamHandle(
        ClassInfo[] memory classes, ExceptionArena memory arena, uint256[] memory parentLinks,
        uint256 owner, bool input, uint256 pc
    ) private pure returns (uint32) {
        uint256 streamClass = arena.stringClass + (input ? 10 : 11);
        if (!_typeAssignable(classes, arena.heap.classes[owner], streamClass, parentLinks)) {
            revert VFS0aProfileError(4, pc);
        }
        uint256 offset = _canonicalVFSFieldOffset(
            classes, streamClass, bytes("handle"), bytes("I"), KIND_INT, parentLinks, pc
        );
        uint256 handleCell = arena.heap.objectHeap[owner][offset];
        if (_valueKind(handleCell) != KIND_INT) revert VFS0aProfileError(4, pc);
        return uint32(_payload(handleCell));
    }

    function _runVFSNative(
        uint8 binding, Frame memory f, uint256 base, uint256 owner, ExceptionArena memory arena,
        ClassInfo[] memory classes, uint256[] memory parentLinks, VFSState memory fs,
        uint256 depth, uint256 pc
    ) private pure returns (uint256 packed) {
        int32 status;
        if (binding == 1 || binding == 2) {
            bytes memory path = _fileLexicalPath(classes, arena, parentLinks, owner, pc);
            if (binding == 1) {
                (uint32 id,,, uint8 failure) = _walkVFSPath(fs, path);
                // Inode wire kinds are DIR=1/FILE=2, while File.stat0's Java-facing
                // statuses are missing=0/FILE=1/DIR=2. Both ENOENT and ENOTDIR are
                // false for the boolean File stat surface.
                status = failure != 0 || id == 0 ? int32(0)
                    : (fs.inodes[id - 1].kind == 2 ? int32(1) : int32(2));
            } else {
                status = _mkdirVFS(fs, path, _payload(f.stack[base + 1]) != 0) ? int32(1) : int32(0);
            }
        } else if (binding == 3 || binding == 7) {
            bool input = binding == 3;
            uint256 streamClass = arena.stringClass + (input ? 10 : 11);
            VFSBindPlan memory plan = _requireVFSOpenFrame(
                classes, f, owner, depth, pc, streamClass, input
            );
            bytes memory path = _fileLexicalPath(
                classes, arena, parentLinks, _payload(f.stack[base + 1]), pc
            );
            bool append = binding == 7 && _payload(f.stack[base + 2]) != 0;
            status = _openVFS(fs, path, uint32(owner), uint16(depth), plan.putfieldPC,
                pc, input, append);
        } else if (binding == 4 || binding == 5) {
            uint32 id = _streamHandle(classes, arena, parentLinks, owner, true, pc);
            uint32 requested = binding == 4 ? 1 : uint32(_payload(f.stack[base + 3]));
            bytes memory data;
            (status, data) = _readVFS(fs, id, requested, pc);
            if (binding == 4 && status > 0) status = int32(uint32(uint8(data[0])));
            if (binding == 5 && status > 0) {
                uint256 arrayRef = _payload(f.stack[base + 1]);
                uint256 offset = uint32(_payload(f.stack[base + 2]));
                for (uint256 i; i < data.length; ++i) {
                    arena.heap.arrayHeap[arrayRef][offset + i] = uint64(uint32(int32(int8(uint8(data[i])))));
                }
            }
        } else if (binding == 8 || binding == 9) {
            uint32 id = _streamHandle(classes, arena, parentLinks, owner, false, pc);
            bytes memory data;
            if (binding == 8) {
                data = new bytes(1);
                data[0] = bytes1(uint8(_payload(f.stack[base + 1])));
            } else {
                uint256 arrayRef = _payload(f.stack[base + 1]);
                uint256 offset = uint32(_payload(f.stack[base + 2]));
                uint256 count = uint32(_payload(f.stack[base + 3]));
                if (count > 4096) revert VFS0aProfileError(3, pc);
                data = new bytes(count);
                for (uint256 i; i < count; ++i) {
                    data[i] = bytes1(uint8(arena.heap.arrayHeap[arrayRef][offset + i]));
                }
            }
            status = _writeVFS(fs, id, data, pc);
        } else {
            uint32 id = _streamHandle(classes, arena, parentLinks, owner, binding == 6, pc);
            status = _closeVFS(fs, id, pc);
        }
        packed = _packInt(uint32(status));
    }

    function _requireVFSObjectProfile(
        ClassInfo[] memory classes, uint256 allocatedClass, uint256 pc,
        uint256[] memory parentLinks, uint8[] memory hierarchyState
    ) private pure {
        _validateHierarchy(classes, allocatedClass, parentLinks, hierarchyState);
        uint256 current = allocatedClass;
        while (parentLinks[current] != type(uint256).max) current = parentLinks[current] - 1;
        if (!_isObjectClass(classes[current])) revert VFS0aProfileError(5, pc);
        uint256 found;
        for (uint256 i; i < classes[current].methods.length; ++i) {
            uint256 meta = classes[current].methods[i];
            (uint256 no, uint256 nn) = _utf(classes[current].cp[(meta >> 16) & 0xffff]);
            (uint256 d, uint256 dn) = _utf(classes[current].cp[(meta >> 32) & 0xffff]);
            if (_equalsLiteral(classes[current].data, no, nn, bytes("<init>"))
                && _equalsLiteral(classes[current].data, d, dn, bytes("()V"))) {
                if (found != 0) revert VFS0aProfileError(5, pc);
                found = i + 1;
            }
        }
        if (found == 0) revert VFS0aProfileError(5, pc);
        Selected memory sel = _loadSpecialCallee(classes[current], found - 1, pc, true, current);
        if (sel.maxStack != 0 || sel.maxLocals != 1 || sel.codeLength != 1
            || sel.handlerStarts.length != 0
            || uint8(classes[current].data[sel.codeOffset]) != 0xb1) {
            revert VFS0aProfileError(5, pc);
        }
    }

    function _nativeBinding(ClassInfo memory c, uint256 method)
        private pure returns (uint8)
    {
        uint256 meta = c.methods[method];
        if ((uint16(meta) & 0x0100) == 0) return 0; // ordinary Code always wins
        (uint256 nameOffset, uint256 nameLength) = _utf(c.cp[(meta >> 16) & 0xffff]);
        (uint256 descriptorOffset, uint256 descriptorLength) =
            _utf(c.cp[(meta >> 32) & 0xffff]);
        if (_isNamedClass(c, bytes("java/lang/Float"))) {
            if (_equalsLiteral(c.data, nameOffset, nameLength, bytes("intBitsToFloat"))
                && _equalsLiteral(c.data, descriptorOffset, descriptorLength, bytes("(I)F"))) {
                return 1;
            }
            if (_equalsLiteral(c.data, nameOffset, nameLength, bytes("floatToRawIntBits"))
                && _equalsLiteral(c.data, descriptorOffset, descriptorLength, bytes("(F)I"))) {
                return 2;
            }
        } else if (_isNamedClass(c, bytes("java/lang/Double"))) {
            if (_equalsLiteral(c.data, nameOffset, nameLength, bytes("longBitsToDouble"))
                && _equalsLiteral(c.data, descriptorOffset, descriptorLength, bytes("(J)D"))) {
                return 3;
            }
            if (_equalsLiteral(c.data, nameOffset, nameLength, bytes("doubleToRawLongBits"))
                && _equalsLiteral(c.data, descriptorOffset, descriptorLength, bytes("(D)J"))) {
                return 4;
            }
        } else if (_isNamedClass(c, bytes("java/lang/System"))) {
            if (_equalsLiteral(c.data, nameOffset, nameLength, bytes("arraycopy"))
                && _equalsLiteral(c.data, descriptorOffset, descriptorLength,
                    bytes("(Ljava/lang/Object;ILjava/lang/Object;II)V"))) return 5;
        }
        return 0;
    }

    // A missing profile API is not permission to hide a malformed descriptor.
    // Scope this check to the profile fallback; ordinary linkage precedence stays
    // unchanged, and a well-formed deferred API still receives StringProfileError.
    function _rejectStringProfileCall(bytes memory data, uint256 off, uint256 n, uint256 pc)
        private pure
    {
        Selected memory signature;
        if (!_descriptor(data, off, n, signature)) revert CallError(4, pc);
        revert StringProfileError(1, pc);
    }

    function _stringNativeBinding(ClassInfo memory c, uint256 method)
        private pure returns (uint8)
    {
        uint256 meta = c.methods[method];
        if (!_isNamedClass(c, bytes("java/lang/String")) || (uint16(meta) & 0x0100) == 0) {
            return 0;
        }
        (uint256 no, uint256 nn) = _utf(c.cp[(meta >> 16) & 0xffff]);
        (uint256 doff, uint256 dn) = _utf(c.cp[(meta >> 32) & 0xffff]);
        if (_equalsLiteral(c.data, no, nn, bytes("length"))
            && _equalsLiteral(c.data, doff, dn, bytes("()I"))) return 1;
        if (_equalsLiteral(c.data, no, nn, bytes("isEmpty"))
            && _equalsLiteral(c.data, doff, dn, bytes("()Z"))) return 2;
        if (_equalsLiteral(c.data, no, nn, bytes("charAt"))
            && _equalsLiteral(c.data, doff, dn, bytes("(I)C"))) return 3;
        if (_equalsLiteral(c.data, no, nn, bytes("equals"))
            && _equalsLiteral(c.data, doff, dn, bytes("(Ljava/lang/Object;)Z"))) return 4;
        if (_equalsLiteral(c.data, no, nn, bytes("hashCode"))
            && _equalsLiteral(c.data, doff, dn, bytes("()I"))) return 5;
        if (_equalsLiteral(c.data, no, nn, bytes("toString"))
            && _equalsLiteral(c.data, doff, dn, bytes("()Ljava/lang/String;"))) return 6;
        if (_equalsLiteral(c.data, no, nn, bytes("compareTo"))
            && _equalsLiteral(c.data, doff, dn, bytes("(Ljava/lang/String;)I"))) return 7;
        if (_equalsLiteral(c.data, no, nn, bytes("intern"))
            && _equalsLiteral(c.data, doff, dn, bytes("()Ljava/lang/String;"))) return 8;
        if (_equalsLiteral(c.data, no, nn, bytes("subSequence"))
            && _equalsLiteral(c.data, doff, dn, bytes("(II)Ljava/lang/CharSequence;"))) return 9;
        return 0;
    }

    function _loadStringNativeCallee(
        ClassInfo memory c, uint256 method, uint256 callPC, uint256 classIndex
    ) private pure returns (Selected memory s) {
        uint256 meta = c.methods[method];
        if (uint16(meta) != 0x0101 || _methodCodeCount(meta) != 0
            || _stringNativeBinding(c, method) == 0) revert CallError(4, callPC);
        s = _loadVirtualSignature(c, method, callPC);
        s.declaringClass = classIndex;
        s.methodIndex = method;
        s.loaded = true;
    }

    function _validateNativeBinding(ClassInfo memory c, uint256 method, uint256 callPC)
        private pure
    {
        uint16 access = uint16(c.methods[method]);
        if ((access & 0x0109) != 0x0109 || (access & (0x0002 | 0x0004 | 0x0020 | 0x0400)) != 0
            || _methodCodeCount(c.methods[method]) != 0) revert CallError(4, callPC);
    }

    function _loadNativeCallee(ClassInfo memory c, uint256 method, uint256 callPC)
        private pure returns (Selected memory s)
    {
        _validateNativeBinding(c, method, callPC);
        uint256 meta = c.methods[method];
        (s.descriptorOffset, s.descriptorLength) = _utf(c.cp[(meta >> 32) & 0xffff]);
        if (!_descriptor(c.data, s.descriptorOffset, s.descriptorLength, s)
            || s.argumentWords > MAX_LOCALS) revert CallError(4, callPC);
        uint8 binding = _nativeBinding(c, method);
        if ((binding != 5 && s.argumentKinds.length != 1)
            || (binding == 5 && (s.argumentKinds.length != 5 || s.returnKind != 2))) {
            revert CallError(4, callPC);
        }
        s.argumentCount = s.argumentKinds.length;
        s.loaded = true;
    }

    /// @dev Bounded EVM implementation of the sole owned System native.  It copies
    /// raw primitive cells (preserving long/FP bits) and reference cells separately;
    /// a reference-store failure leaves the already-copied prefix intact.
    function _runSystemArraycopy(
        uint256[] memory stack, uint256 base, uint64[][] memory arrays,
        ExceptionArena memory arena, ClassInfo[] memory classes, uint256[][] memory objectHeap,
        uint256[] memory heapKinds, uint256[] memory heapClasses, uint8[] memory arrayRanks,
        uint256[] memory arrayLeafTypes, uint256[] memory parentLinks,
        uint8[] memory hierarchyState, uint256 nextHandle, uint256 pc
    ) private pure returns (uint256) {
        uint256 source = _payload(stack[base]);
        uint256 destination = _payload(stack[base + 2]);
        // Java's documented null precedence is before array/type/range validation.
        if (source == 0 || destination == 0) return _raiseJava(
            6, pc, arena, classes, objectHeap, heapKinds, heapClasses,
            arrayLeafTypes, parentLinks, hierarchyState, nextHandle
        );
        if (_heapKindAt(heapKinds[source]) != HEAP_ARRAY
            || _heapKindAt(heapKinds[destination]) != HEAP_ARRAY) return _raiseJava(
            9, pc, arena, classes, objectHeap, heapKinds, heapClasses,
            arrayLeafTypes, parentLinks, hierarchyState, nextHandle
        );
        bool sourceReferences = _arrayHasReferenceComponents(arrayRanks[source], arrayLeafTypes[source]);
        bool destinationReferences = _arrayHasReferenceComponents(
            arrayRanks[destination], arrayLeafTypes[destination]
        );
        // Primitive kinds are never conflated.  Java rejects a primitive/reference
        // pair or distinct primitive leaves before range validation, even at length 0.
        if (sourceReferences != destinationReferences
            || (!sourceReferences && arrayLeafTypes[source] != arrayLeafTypes[destination])) {
            return _raiseJava(9, pc, arena, classes, objectHeap, heapKinds, heapClasses,
                arrayLeafTypes, parentLinks, hierarchyState, nextHandle);
        }
        int32 sourcePos = int32(uint32(_payload(stack[base + 1])));
        int32 destinationPos = int32(uint32(_payload(stack[base + 3])));
        int32 length = int32(uint32(_payload(stack[base + 4])));
        if (sourcePos < 0 || destinationPos < 0 || length < 0
            || uint256(uint32(sourcePos)) > arrays[source].length
            || uint256(uint32(destinationPos)) > arrays[destination].length
            || uint256(uint32(length)) > arrays[source].length - uint256(uint32(sourcePos))
            || uint256(uint32(length)) > arrays[destination].length - uint256(uint32(destinationPos))) {
            return _raiseJava(5, pc, arena, classes, objectHeap, heapKinds, heapClasses,
                arrayLeafTypes, parentLinks, hierarchyState, nextHandle);
        }
        uint256 n = uint256(uint32(length));
        uint256 srcAt = uint256(uint32(sourcePos));
        uint256 dstAt = uint256(uint32(destinationPos));
        bool backwards = source == destination && dstAt > srcAt && dstAt < srcAt + n;
        for (uint256 i; i < n; ++i) {
            uint256 at = backwards ? n - 1 - i : i;
            uint64 cell = arrays[source][srcAt + at];
            if (destinationReferences && !_valueFitsArrayComponent(
                classes, uint256(cell), arrayRanks[destination], arrayLeafTypes[destination],
                heapKinds, heapClasses, arrayRanks, arrayLeafTypes, parentLinks
            )) return _raiseJava(9, pc, arena, classes, objectHeap, heapKinds, heapClasses,
                arrayLeafTypes, parentLinks, hierarchyState, nextHandle);
            arrays[destination][dstAt + at] = cell;
        }
        return nextHandle;
    }

    function _execute(
        ClassInfo[] memory classes,
        Selected[][][] memory selected,
        uint256[][] memory referenceCaches,
        uint256[][] memory fieldCaches,
        uint256 rootClass,
        uint256 root,
        bool bundleMode,
        uint256 throwableBootstrapAt,
        RuntimeState memory state,
        uint64 maxJvmSteps,
        uint32 maxInternalSteps
    ) private view returns (uint64 executedJvmSteps, uint32 executedInternalSteps) {
        Frame[] memory frames = state.frames;
        uint256 depth = state.depth;
        uint8[] memory initializationState = state.initializationState;
        bool[] memory initializerStarted = state.initializerStarted;
        uint256[][] memory staticValues = state.staticValues;
        uint256[] memory parentLinks = state.parentLinks;
        uint8[] memory hierarchyState = state.hierarchyState;
        uint64[][] memory arrayHeap = state.arena.heap.arrayHeap;
        uint256[][] memory objectHeap = state.arena.heap.objectHeap;
        uint256[] memory heapKinds = state.arena.heap.metadata;
        uint256[] memory heapClasses = state.arena.heap.classes;
        uint8[] memory arrayRanks = state.arena.heap.ranks;
        uint256[] memory arrayLeafTypes = state.arena.heap.metadata;
        uint256 nextHandle = state.nextHandle;
        uint256[][] memory objectFieldDefaults = new uint256[][](classes.length);
        bool[] memory objectLayoutsLoaded = new bool[](classes.length);
        ExceptionArena memory arena = state.arena;
        bool inPendingUnit;

        while (depth != 0) {
            if (!inPendingUnit) {
                if (executedJvmSteps >= maxJvmSteps
                    || executedInternalSteps >= maxInternalSteps) break;
                if (gasleft() <= COMMIT_RESERVE) revert LC0ControlError(7);
            }
            if (!state.rootInitializationScheduled) {
                if (state.totalInternalSteps == type(uint64).max) revert LC0ControlError(6);
                state.rootInitializationScheduled = true;
                ++executedInternalSteps;
                ++state.totalInternalSteps;
                frames[0].entered = false;
                depth = _initializeClass(
                    classes, staticValues, initializationState, frames, depth, rootClass,
                    parentLinks, hierarchyState, arena, ROOT_FAULT_SENTINEL,
                    objectHeap, heapKinds, heapClasses, arrayLeafTypes, nextHandle
                );
                nextHandle = arena.nextHandle;
                if (arena.heap.metadata.length != 0) {
                    arrayHeap = arena.heap.arrayHeap;
                    objectHeap = arena.heap.objectHeap;
                    arrayLeafTypes = arena.heap.metadata;
                    heapKinds = arrayLeafTypes;
                    heapClasses = arena.heap.classes;
                    arrayRanks = arena.heap.ranks;
                }
                if (!arena.pending.active && depth == 1) frames[0].entered = true;
                continue;
            }
            if (arena.pending.active) {
                if (!inPendingUnit) {
                    if (state.totalInternalSteps == type(uint64).max) revert LC0ControlError(6);
                    ++executedInternalSteps;
                    ++state.totalInternalSteps;
                    inPendingUnit = true;
                }
                Frame memory throwing = frames[depth - 1];
                if (throwing.isInitContinuation) {
                    if (initializationState[throwing.classIndex] == 1) {
                        initializationState[throwing.classIndex] = 3;
                    }
                    arena.pending.faultPC = throwing.callPC;
                    --depth;
                    if (depth == 0) {
                        state.lifecycle = 3;
                        break;
                    }
                    continue;
                }
                if (!throwing.entered) {
                    --depth;
                    if (depth == 0) {
                        state.lifecycle = 3;
                        break;
                    }
                    continue;
                }
                Selected memory throwingSelection =
                    selected[throwing.classIndex][throwing.methodIndex][0];
                bool caught;
                for (uint256 hi = 0; hi < throwingSelection.handlerStarts.length; ++hi) {
                    if (arena.pending.faultPC < throwingSelection.handlerStarts[hi]
                        || arena.pending.faultPC >= throwingSelection.handlerEnds[hi]) continue;
                    bool matches = throwingSelection.handlerCatchTypes[hi] == 0;
                    if (!matches) {
                        uint256 catchClass = _resolveCatchClass(
                            classes, throwing.classIndex, throwingSelection, hi,
                            parentLinks, hierarchyState, arena.throwableClass
                        );
                        matches = _typeAssignable(
                            classes, arena.heap.classes[arena.pending.ref], catchClass, parentLinks
                        );
                    }
                    if (!matches) continue;
                    if (throwing.isConstructor && !throwing.isConstructorLinked) {
                        revert HandlerError(
                            8, throwing.classIndex, throwing.methodIndex, hi
                        );
                    }
                    // A caught reference makes the lazy shared registry reachable
                    // by subsequent guest bytecodes.
                    objectHeap = arena.heap.objectHeap;
                    arrayLeafTypes = arena.heap.metadata;
                    heapKinds = arrayLeafTypes;
                    heapClasses = arena.heap.classes;
                    arrayHeap = arena.heap.arrayHeap;
                    arrayRanks = arena.heap.ranks;
                    nextHandle = arena.nextHandle;
                    throwing.sp = 0;
                    throwing.pc = throwingSelection.handlerPCs[hi];
                    throwing.sp = _push(
                        throwing.stack, throwing.sp, _packRef(uint32(arena.pending.ref)),
                        arena.pending.faultPC
                    );
                    arena.pending.active = false;
                    inPendingUnit = false;
                    caught = true;
                    break;
                }
                if (caught) continue;

                uint256 callerPC = throwing.callPC;
                bool failedConstructor = throwing.isConstructor;
                uint256 failedHandle = throwing.thisHandle;
                if (throwing.isInitializer) {
                    initializationState[throwing.classIndex] = 3;
                    if (!_typeAssignable(
                        classes, arena.heap.classes[arena.pending.ref], arena.errorClass, parentLinks
                    )) {
                        uint256 causeRef = arena.pending.ref;
                        nextHandle = _raiseJava(
                            3, callerPC, arena, classes, objectHeap, heapKinds,
                            heapClasses, arrayLeafTypes, parentLinks, hierarchyState, nextHandle
                        );
                        if (arena.pending.kind == 3
                            && (arena.heap.metadata[arena.pending.ref] & 0xff) == 3) {
                            _storeVMWrapperException(
                                arena, classes, arena.pending.ref, causeRef,
                                parentLinks, callerPC
                            );
                        }
                    }
                }
                --depth;
                if (failedConstructor && depth != 0) {
                    _poisonAliases(frames[depth - 1], failedHandle);
                }
                arena.pending.faultPC = callerPC;
                if (depth == 0) {
                    state.lifecycle = 3;
                    break;
                }
                continue;
            }
            Frame memory f = frames[depth - 1];
            if (f.isInitContinuation) {
                if (state.totalInternalSteps == type(uint64).max) revert LC0ControlError(6);
                ++executedInternalSteps;
                ++state.totalInternalSteps;
                uint256 initializingClass = f.classIndex;
                ClassInfo memory initializing = classes[initializingClass];
                // JVMS 5.5 initializes default-declaring superinterfaces only as
                // prerequisites of an ordinary class. The traversal is repeated after
                // each prerequisite returns; initializationState both deduplicates
                // diamonds and makes reentrant requests harmless.
                if (!_isInterface(initializing)) {
                    (bool hasDefaultPrerequisite, uint256 defaultPrerequisite) =
                        _nextDefaultInterface(classes, initializingClass, initializationState);
                    if (hasDefaultPrerequisite) {
                        arena.nextHandle = nextHandle;
                        depth = _initializeClass(
                            classes, staticValues, initializationState, frames, depth,
                            defaultPrerequisite, parentLinks, hierarchyState, arena, f.callPC,
                            objectHeap, heapKinds, heapClasses, arrayLeafTypes, nextHandle
                        );
                        nextHandle = arena.nextHandle;
                        if (arena.heap.metadata.length != 0) {
                            arrayHeap = arena.heap.arrayHeap;
                            objectHeap = arena.heap.objectHeap;
                            arrayLeafTypes = arena.heap.metadata;
                            heapKinds = arrayLeafTypes;
                            heapClasses = arena.heap.classes;
                            arrayRanks = arena.heap.ranks;
                        }
                        continue;
                    }
                }
                if (initializing.initializerPlusOne != 0 && !initializerStarted[initializingClass]) {
                    initializerStarted[initializingClass] = true;
                    if (selected[initializingClass].length == 0) {
                        selected[initializingClass] = new Selected[][](initializing.methods.length);
                        referenceCaches[initializingClass] = new uint256[](initializing.cp.length);
                        fieldCaches[initializingClass] = new uint256[](initializing.cp.length);
                    }
                    uint256 initializerMethod = initializing.initializerPlusOne - 1;
                    Selected memory initializerSelection =
                        _loadInitializer(initializing, initializerMethod, initializingClass);
                    _predecode(initializing, initializerSelection);
                    _putSelection(
                        selected, initializingClass, initializerMethod, initializerSelection
                    );
                    if (depth == MAX_FRAMES) {
                        nextHandle = _raiseJava(
                            2, f.callPC, arena, classes, objectHeap, heapKinds,
                            heapClasses, arrayLeafTypes, parentLinks, hierarchyState, nextHandle
                        );
                        continue;
                    }
                    Frame memory initializer = _newFrame(
                        initializingClass, initializerMethod,
                        selected[initializingClass][initializerMethod][0], f.callPC
                    );
                    initializer.isInitializer = true;
                    frames[depth] = initializer;
                    ++depth;
                    continue;
                }
                initializationState[initializingClass] = 2;
                --depth;
                if (depth == 1 && !frames[0].entered) frames[0].entered = true;
                continue;
            }
            ClassInfo memory c = classes[f.classIndex];
            Selected memory selection = selected[f.classIndex][f.methodIndex][0];
            if (f.pc >= selection.codeLength) revert BytecodeError(7, f.pc);
            if (state.totalJvmSteps == type(uint64).max) revert LC0ControlError(6);
            ++executedJvmSteps;
            ++state.totalJvmSteps;
            uint256 opPC = f.pc;
            uint8 op = uint8(c.data[selection.codeOffset + f.pc]);
            ++f.pc;
            // Keep the common compiler-emitted local increment near dispatch entry.
            // This is still one ordinary JVM instruction per interpreter iteration;
            // it only avoids traversing unrelated arithmetic dispatch branches.
            if (op == 0x84) { // iinc
                uint256 local = uint8(c.data[selection.codeOffset + f.pc]);
                int8 amount = int8(uint8(c.data[selection.codeOffset + f.pc + 1]));
                if (local >= f.locals.length) revert BytecodeError(8, opPC);
                if (!f.initialized[local]) revert BytecodeError(11, opPC);
                _requireKind(f.locals[local], KIND_INT, opPC);
                unchecked {
                    f.locals[local] = _packInt(
                        uint32(_payload(f.locals[local])) + uint32(int32(amount))
                    );
                }
                f.pc += 2;
            } else if (op == 0x00) { // nop
                continue;
            } else if (op == 0x01) { // aconst_null
                f.sp = _push(f.stack, f.sp, _packRef(0), opPC);
            } else if (op >= 0x02 && op <= 0x08) { // iconst_m1 ... iconst_5
                uint32 value = op == 0x02 ? type(uint32).max : uint32(op - 0x03);
                f.sp = _push(f.stack, f.sp, _packInt(value), opPC);
            } else if (op == 0x09 || op == 0x0a) { // lconst_0, lconst_1
                f.sp = _push(f.stack, f.sp, _packLong(uint64(op - 0x09)), opPC);
            } else if (op == 0x10) { // bipush
                f.sp = _push(f.stack, f.sp, _packInt(
                    uint32(int32(int8(uint8(c.data[selection.codeOffset + f.pc]))))
                ), opPC);
                ++f.pc;
            } else if (op == 0x11) { // sipush
                f.sp = _push(f.stack, f.sp, _packInt(
                    uint32(int32(_signed16(c.data, selection.codeOffset + f.pc)))
                ), opPC);
                f.pc += 2;
            } else if (op == 0x12 || op == 0x13) { // ldc / ldc_w, Integer, Float, or String
                uint256 index;
                if (op == 0x12) {
                    index = uint8(c.data[selection.codeOffset + f.pc]);
                    ++f.pc;
                } else {
                    index = _unsigned16(c.data, selection.codeOffset + f.pc);
                    f.pc += 2;
                }
                if (index == 0 || index >= c.cp.length) revert BytecodeError(13, opPC);
                uint8 tag = uint8(c.cp[index]);
                if (tag != 3 && tag != 4 && tag != 8 && tag != 7) revert BytecodeError(13, opPC);
                if (tag == 7) {
                    if (_stackWords(f.stack, f.sp) >= f.stack.length) revert BytecodeError(9, opPC);
                    (uint256 mirror, bool oom) = _classLiteralMirror(
                        arena, classes, f.classIndex, index, parentLinks, hierarchyState, opPC
                    );
                    if (oom) {
                        nextHandle = _raiseJava(7, opPC, arena, classes, objectHeap, heapKinds,
                            heapClasses, arrayLeafTypes, parentLinks, hierarchyState, nextHandle);
                        continue;
                    }
                    nextHandle = arena.nextHandle;
                    arrayHeap = arena.heap.arrayHeap; objectHeap = arena.heap.objectHeap;
                    arrayLeafTypes = arena.heap.metadata; heapKinds = arrayLeafTypes;
                    heapClasses = arena.heap.classes; arrayRanks = arena.heap.ranks;
                    f.sp = _push(f.stack, f.sp, _packRef(uint32(mirror)), opPC);
                } else if (tag == 8) {
                    // A miss must not allocate before discovering a full operand stack.
                    if (_stackWords(f.stack, f.sp) >= f.stack.length) {
                        revert BytecodeError(9, opPC);
                    }
                    (uint256 stringRef, bool oom) = _internStringConstant(
                        arena, classes, f.classIndex, index, parentLinks, hierarchyState
                    );
                    if (oom) {
                        nextHandle = _raiseJava(
                            7, opPC, arena, classes, objectHeap, heapKinds, heapClasses,
                            arrayLeafTypes, parentLinks, hierarchyState, nextHandle
                        );
                        continue;
                    }
                    nextHandle = arena.nextHandle;
                    arrayHeap = arena.heap.arrayHeap;
                    objectHeap = arena.heap.objectHeap;
                    arrayLeafTypes = arena.heap.metadata;
                    heapKinds = arrayLeafTypes;
                    heapClasses = arena.heap.classes;
                    arrayRanks = arena.heap.ranks;
                    f.sp = _push(f.stack, f.sp, _packRef(uint32(stringRef)), opPC);
                } else {
                    f.sp = _push(f.stack, f.sp, tag == 3
                        ? _packInt(uint32(c.cp[index] >> 8))
                        : _packFloat(uint32(c.cp[index] >> 8)), opPC);
                }
            } else if (op == 0x14) { // ldc2_w (CONSTANT_Long or Double)
                uint256 index = _unsigned16(c.data, selection.codeOffset + f.pc);
                f.pc += 2;
                if (index == 0 || index >= c.cp.length) revert BytecodeError(13, opPC);
                uint8 tag = uint8(c.cp[index]);
                if (tag != 5 && tag != 6) revert BytecodeError(13, opPC);
                f.sp = _push(f.stack, f.sp, tag == 5
                    ? _packLong(uint64(c.cp[index] >> 8))
                    : _packDouble(uint64(c.cp[index] >> 8)), opPC);
            } else if (op >= 0x15 && op <= 0x19) { // iload / lload / fload / dload / aload
                uint256 local = uint8(c.data[selection.codeOffset + f.pc]);
                ++f.pc;
                if (op == 0x19) f.sp = _loadReference(
                    f.stack, f.sp, f.locals, f.initialized, local, opPC
                );
                else if (op == 0x16) f.sp = _loadLong(
                    f.stack, f.sp, f.locals, f.initialized, local, opPC
                );
                else if (op == 0x18) f.sp = _loadDouble(
                    f.stack, f.sp, f.locals, f.initialized, local, opPC
                );
                else f.sp = _loadKind(
                    f.stack, f.sp, f.locals, f.initialized, local,
                    op == 0x17 ? KIND_FLOAT : KIND_INT, opPC
                );
            } else if (op >= 0x1a && op <= 0x1d) { // iload_0..3
                f.sp = _loadKind(
                    f.stack, f.sp, f.locals, f.initialized, op - 0x1a, KIND_INT, opPC
                );
            } else if (op >= 0x1e && op <= 0x21) { // lload_0..3
                f.sp = _loadLong(
                    f.stack, f.sp, f.locals, f.initialized, op - 0x1e, opPC
                );
            } else if (op >= 0x2a && op <= 0x2d) { // aload_0..3
                f.sp = _loadReference(
                    f.stack, f.sp, f.locals, f.initialized, op - 0x2a, opPC
                );
            } else if (op >= 0x2e && op <= 0x35) {
                // iaload / laload / faload / daload / aaload / baload / caload / saload
                if (f.sp < 2) revert BytecodeError(3, opPC);
                _requireKind(f.stack[f.sp - 2], KIND_REF, opPC);
                _requireKind(f.stack[f.sp - 1], KIND_INT, opPC);
                uint256 handle = _payload(f.stack[f.sp - 2]);
                if (handle == 0) nextHandle = _raiseJava(
                        6, opPC, arena, classes, objectHeap, heapKinds, heapClasses,
                        arrayLeafTypes, parentLinks, hierarchyState, nextHandle
                    );
                if (arena.pending.active) continue;
                _requireHeapKind(handle, heapKinds, nextHandle, HEAP_ARRAY, opPC);
                uint8 rank = arrayRanks[handle];
                uint256 leafType = arrayLeafTypes[handle];
                bool referenceComponents = _arrayHasReferenceComponents(rank, leafType);
                bool matching = (op == 0x32 && referenceComponents)
                    || (op == 0x2e && rank == 1 && leafType == PRIMITIVE_INT)
                    || (op == 0x2f && rank == 1 && leafType == PRIMITIVE_LONG)
                    || (op == 0x30 && rank == 1 && leafType == PRIMITIVE_FLOAT)
                    || (op == 0x31 && rank == 1 && leafType == PRIMITIVE_DOUBLE)
                    || (op == 0x33 && rank == 1
                        && (leafType == PRIMITIVE_BYTE || leafType == PRIMITIVE_BOOLEAN))
                    || (op == 0x34 && rank == 1 && leafType == PRIMITIVE_CHAR)
                    || (op == 0x35 && rank == 1 && leafType == PRIMITIVE_SHORT);
                if (!matching) revert ReferenceError(1, opPC);
                int32 index = int32(uint32(_payload(f.stack[f.sp - 1])));
                if (index < 0 || uint256(uint32(index)) >= arrayHeap[handle].length) {
                    nextHandle = _raiseJava(
                        5, opPC, arena, classes, objectHeap, heapKinds, heapClasses,
                        arrayLeafTypes, parentLinks, hierarchyState, nextHandle
                    );
                if (arena.pending.active) continue;
                }
                uint64 cell = arrayHeap[handle][uint256(uint32(index))];
                if (op == 0x2f) f.stack[f.sp - 2] = _packLong(cell);
                else if (op == 0x30) f.stack[f.sp - 2] = _packFloat(uint32(cell));
                else if (op == 0x31) f.stack[f.sp - 2] = _packDouble(cell);
                else if (referenceComponents) f.stack[f.sp - 2] = _packRef(uint32(cell));
                else f.stack[f.sp - 2] = _packInt(_normalizeInt(uint32(cell), uint8(leafType)));
                --f.sp;
            } else if (op >= 0x36 && op <= 0x3a) { // istore/lstore/fstore/dstore/astore
                uint256 local = uint8(c.data[selection.codeOffset + f.pc]);
                ++f.pc;
                if (op == 0x3a) f.sp = _storeReference(
                    f.stack, f.sp, f.locals, f.initialized, local, opPC
                );
                else if (op == 0x37) f.sp = _storeLong(
                    f.stack, f.sp, f.locals, f.initialized, local, opPC
                );
                else if (op == 0x39) f.sp = _storeDouble(
                    f.stack, f.sp, f.locals, f.initialized, local, opPC
                );
                else f.sp = _storeKind(
                    f.stack, f.sp, f.locals, f.initialized, local,
                    op == 0x38 ? KIND_FLOAT : KIND_INT, opPC
                );
            } else if (op >= 0x3b && op <= 0x3e) { // istore_0..3
                f.sp = _storeKind(
                    f.stack, f.sp, f.locals, f.initialized, op - 0x3b, KIND_INT, opPC
                );
            } else if (op >= 0x3f && op <= 0x42) { // lstore_0..3
                f.sp = _storeLong(
                    f.stack, f.sp, f.locals, f.initialized, op - 0x3f, opPC
                );
            } else if (op >= 0x4b && op <= 0x4e) { // astore_0..3
                f.sp = _storeReference(
                    f.stack, f.sp, f.locals, f.initialized, op - 0x4b, opPC
                );
            } else if (op >= 0x4f && op <= 0x56) {
                // iastore / lastore / fastore / dastore / aastore / bastore / castore / sastore
                if (f.sp < 3) revert BytecodeError(3, opPC);
                _requireKind(f.stack[f.sp - 3], KIND_REF, opPC);
                _requireKind(f.stack[f.sp - 2], KIND_INT, opPC);
                uint256 valueKind = op == 0x53 ? KIND_REF
                    : (op == 0x50 ? KIND_LONG
                        : (op == 0x51 ? KIND_FLOAT : (op == 0x52 ? KIND_DOUBLE : KIND_INT)));
                _requireKind(f.stack[f.sp - 1], valueKind, opPC);
                uint256 handle = _payload(f.stack[f.sp - 3]);
                if (op == 0x53) {
                    // Constructor tokens and forged references are rejected before Java's
                    // receiver/bounds/store checks; initialized null remains a valid value.
                    _validatePackedRef(f.stack[f.sp - 1], heapKinds, nextHandle, opPC);
                }
                if (handle == 0) nextHandle = _raiseJava(
                        6, opPC, arena, classes, objectHeap, heapKinds, heapClasses,
                        arrayLeafTypes, parentLinks, hierarchyState, nextHandle
                    );
                if (arena.pending.active) continue;
                _requireHeapKind(handle, heapKinds, nextHandle, HEAP_ARRAY, opPC);
                uint8 rank = arrayRanks[handle];
                uint256 leafType = arrayLeafTypes[handle];
                bool referenceComponents = _arrayHasReferenceComponents(rank, leafType);
                bool matching = (op == 0x53 && referenceComponents)
                    || (op == 0x4f && rank == 1 && leafType == PRIMITIVE_INT)
                    || (op == 0x50 && rank == 1 && leafType == PRIMITIVE_LONG)
                    || (op == 0x51 && rank == 1 && leafType == PRIMITIVE_FLOAT)
                    || (op == 0x52 && rank == 1 && leafType == PRIMITIVE_DOUBLE)
                    || (op == 0x54 && rank == 1
                        && (leafType == PRIMITIVE_BYTE || leafType == PRIMITIVE_BOOLEAN))
                    || (op == 0x55 && rank == 1 && leafType == PRIMITIVE_CHAR)
                    || (op == 0x56 && rank == 1 && leafType == PRIMITIVE_SHORT);
                if (!matching) revert ReferenceError(1, opPC);
                int32 index = int32(uint32(_payload(f.stack[f.sp - 2])));
                if (index < 0 || uint256(uint32(index)) >= arrayHeap[handle].length) {
                    nextHandle = _raiseJava(
                        5, opPC, arena, classes, objectHeap, heapKinds, heapClasses,
                        arrayLeafTypes, parentLinks, hierarchyState, nextHandle
                    );
                if (arena.pending.active) continue;
                }
                if (op == 0x53 && !_valueFitsArrayComponent(
                    classes, f.stack[f.sp - 1], rank, leafType,
                    heapKinds, heapClasses, arrayRanks, arrayLeafTypes, parentLinks
                )) nextHandle = _raiseJava(
                        9, opPC, arena, classes, objectHeap, heapKinds, heapClasses,
                        arrayLeafTypes, parentLinks, hierarchyState, nextHandle
                    );
                if (arena.pending.active) continue;
                uint64 stored = uint64(_payload(f.stack[f.sp - 1]));
                if (op != 0x50 && op != 0x51 && op != 0x52 && !referenceComponents) {
                    stored = uint64(_normalizeInt(uint32(stored), uint8(leafType)));
                }
                arrayHeap[handle][uint256(uint32(index))] = stored;
                f.sp -= 3;
            } else if (op == 0x57) { // pop (category 1 only)
                if (f.sp == 0) revert BytecodeError(3, opPC);
                if (!_isCategory1(f.stack[f.sp - 1])) revert BytecodeError(14, opPC);
                --f.sp;
            } else if (op >= 0x58 && op <= 0x5f) {
                f.sp = _permuteStack(f.stack, f.sp, op, opPC);
            } else if (op == 0x60 || op == 0x64 || op == 0x68) {
                if (f.sp < 2) revert BytecodeError(3, opPC);
                _requireIntPair(f.stack, f.sp, opPC);
                uint32 left = uint32(_payload(f.stack[f.sp - 2]));
                uint32 right = uint32(_payload(f.stack[f.sp - 1]));
                unchecked {
                    if (op == 0x60) left += right;
                    else if (op == 0x64) left -= right;
                    else left *= right;
                }
                f.stack[f.sp - 2] = _packInt(left);
                --f.sp;
            } else if (op == 0x61 || op == 0x65 || op == 0x69) { // ladd/lsub/lmul
                if (f.sp < 2) revert BytecodeError(3, opPC);
                _requireLongPair(f.stack, f.sp, opPC);
                uint64 left = uint64(_payload(f.stack[f.sp - 2]));
                uint64 right = uint64(_payload(f.stack[f.sp - 1]));
                unchecked {
                    if (op == 0x61) left += right;
                    else if (op == 0x65) left -= right;
                    else left *= right;
                }
                f.stack[f.sp - 2] = _packLong(left);
                --f.sp;
            } else if (op == 0x62 || op == 0x63 || op == 0x66 || op == 0x67
                || op == 0x6a || op == 0x6b || op == 0x6e || op == 0x6f
                || op == 0x72 || op == 0x73) { // scalar F/D add/sub/mul/div/rem
                if (f.sp < 2) revert BytecodeError(3, opPC);
                bool doubles = (op & 1) != 0;
                uint256 wanted = doubles ? KIND_DOUBLE : KIND_FLOAT;
                _requireKind(f.stack[f.sp - 2], wanted, opPC);
                _requireKind(f.stack[f.sp - 1], wanted, opPC);
                uint64 result = _ieeeArithmetic(
                    uint64(_payload(f.stack[f.sp - 2])),
                    uint64(_payload(f.stack[f.sp - 1])), op, doubles
                );
                f.stack[f.sp - 2] = doubles ? _packDouble(result) : _packFloat(uint32(result));
                --f.sp;
            } else if (op == 0x6c || op == 0x70) {
                if (f.sp < 2) revert BytecodeError(3, opPC);
                _requireIntPair(f.stack, f.sp, opPC);
                int32 dividend = int32(uint32(_payload(f.stack[f.sp - 2])));
                int32 divisor = int32(uint32(_payload(f.stack[f.sp - 1])));
                if (divisor == 0) nextHandle = _raiseJava(
                        1, opPC, arena, classes, objectHeap, heapKinds, heapClasses,
                        arrayLeafTypes, parentLinks, hierarchyState, nextHandle
                    );
                if (arena.pending.active) continue;
                uint32 result;
                if (dividend == type(int32).min && divisor == -1) {
                    result = op == 0x6c ? uint32(0x80000000) : 0;
                } else if (op == 0x6c) result = uint32(dividend / divisor);
                else result = uint32(dividend % divisor);
                f.stack[f.sp - 2] = _packInt(result);
                --f.sp;
            } else if (op == 0x6d || op == 0x71) { // ldiv/lrem
                if (f.sp < 2) revert BytecodeError(3, opPC);
                _requireLongPair(f.stack, f.sp, opPC);
                int64 dividend = int64(uint64(_payload(f.stack[f.sp - 2])));
                int64 divisor = int64(uint64(_payload(f.stack[f.sp - 1])));
                if (divisor == 0) nextHandle = _raiseJava(
                        1, opPC, arena, classes, objectHeap, heapKinds, heapClasses,
                        arrayLeafTypes, parentLinks, hierarchyState, nextHandle
                    );
                if (arena.pending.active) continue;
                uint64 result;
                if (dividend == type(int64).min && divisor == -1) {
                    result = op == 0x6d ? uint64(0x8000000000000000) : 0;
                } else if (op == 0x6d) result = uint64(dividend / divisor);
                else result = uint64(dividend % divisor);
                f.stack[f.sp - 2] = _packLong(result);
                --f.sp;
            } else if (op == 0x74) {
                if (f.sp == 0) revert BytecodeError(3, opPC);
                _requireKind(f.stack[f.sp - 1], KIND_INT, opPC);
                unchecked {
                    f.stack[f.sp - 1] = _packInt(uint32(0) - uint32(_payload(f.stack[f.sp - 1])));
                }
            } else if (op == 0x75) { // lneg
                if (f.sp == 0) revert BytecodeError(3, opPC);
                _requireKind(f.stack[f.sp - 1], KIND_LONG, opPC);
                unchecked {
                    f.stack[f.sp - 1] = _packLong(uint64(0) - uint64(_payload(f.stack[f.sp - 1])));
                }
            } else if (op == 0x78 || op == 0x7a || op == 0x7c) {
                if (f.sp < 2) revert BytecodeError(3, opPC);
                _requireIntPair(f.stack, f.sp, opPC);
                uint32 left = uint32(_payload(f.stack[f.sp - 2]));
                uint256 shift = _payload(f.stack[f.sp - 1]) & 31;
                if (op == 0x78) left <<= shift;
                else if (op == 0x7a) left = uint32(int32(left) >> shift);
                else left >>= shift;
                f.stack[f.sp - 2] = _packInt(left);
                --f.sp;
            } else if (op == 0x79 || op == 0x7b || op == 0x7d) { // lshl/lshr/lushr
                if (f.sp < 2) revert BytecodeError(3, opPC);
                _requireKind(f.stack[f.sp - 2], KIND_LONG, opPC);
                _requireKind(f.stack[f.sp - 1], KIND_INT, opPC);
                uint64 left = uint64(_payload(f.stack[f.sp - 2]));
                uint256 shift = _payload(f.stack[f.sp - 1]) & 63;
                if (op == 0x79) left <<= shift;
                else if (op == 0x7b) left = uint64(int64(left) >> shift);
                else left >>= shift;
                f.stack[f.sp - 2] = _packLong(left);
                --f.sp;
            } else if (op == 0x7e || op == 0x80 || op == 0x82) {
                if (f.sp < 2) revert BytecodeError(3, opPC);
                _requireIntPair(f.stack, f.sp, opPC);
                uint32 left = uint32(_payload(f.stack[f.sp - 2]));
                uint32 right = uint32(_payload(f.stack[f.sp - 1]));
                if (op == 0x7e) left &= right;
                else if (op == 0x80) left |= right;
                else left ^= right;
                f.stack[f.sp - 2] = _packInt(left);
                --f.sp;
            } else if (op == 0x7f || op == 0x81 || op == 0x83) { // land/lor/lxor
                if (f.sp < 2) revert BytecodeError(3, opPC);
                _requireLongPair(f.stack, f.sp, opPC);
                uint64 left = uint64(_payload(f.stack[f.sp - 2]));
                uint64 right = uint64(_payload(f.stack[f.sp - 1]));
                if (op == 0x7f) left &= right;
                else if (op == 0x81) left |= right;
                else left ^= right;
                f.stack[f.sp - 2] = _packLong(left);
                --f.sp;
            } else if (op == 0x85) { // i2l
                if (f.sp == 0) revert BytecodeError(3, opPC);
                _requireKind(f.stack[f.sp - 1], KIND_INT, opPC);
                int64 extended = int64(int32(uint32(_payload(f.stack[f.sp - 1]))));
                f.stack[f.sp - 1] = _packLong(uint64(extended));
                if (_stackWords(f.stack, f.sp) > f.stack.length) revert BytecodeError(9, opPC);
            } else if (op == 0x88) { // l2i
                if (f.sp == 0) revert BytecodeError(3, opPC);
                _requireKind(f.stack[f.sp - 1], KIND_LONG, opPC);
                f.stack[f.sp - 1] = _packInt(uint32(_payload(f.stack[f.sp - 1])));
            } else if (op == 0x91 || op == 0x92 || op == 0x93) {
                if (f.sp == 0) revert BytecodeError(3, opPC);
                _requireKind(f.stack[f.sp - 1], KIND_INT, opPC);
                uint32 value = uint32(_payload(f.stack[f.sp - 1]));
                if (op == 0x91) value = uint32(int32(int8(uint8(value))));
                else if (op == 0x92) value = uint32(uint16(value));
                else value = uint32(int32(int16(uint16(value))));
                f.stack[f.sp - 1] = _packInt(value);
            } else if (op == 0x94) { // lcmp
                if (f.sp < 2) revert BytecodeError(3, opPC);
                _requireLongPair(f.stack, f.sp, opPC);
                int64 left = int64(uint64(_payload(f.stack[f.sp - 2])));
                int64 right = int64(uint64(_payload(f.stack[f.sp - 1])));
                uint32 result = left == right ? 0 : (left < right ? type(uint32).max : 1);
                f.stack[f.sp - 2] = _packInt(result);
                --f.sp;
            } else if (op >= 0x99 && op <= 0x9e) {
                if (f.sp == 0) revert BytecodeError(3, opPC);
                _requireKind(f.stack[f.sp - 1], KIND_INT, opPC);
                int32 value = int32(uint32(_payload(f.stack[f.sp - 1])));
                --f.sp;
                f.pc = _unaryCondition(op, value)
                    ? _decodedTarget(c.data, selection.codeOffset, opPC) : f.pc + 2;
            } else if (op >= 0x9f && op <= 0xa4) {
                if (f.sp < 2) revert BytecodeError(3, opPC);
                _requireIntPair(f.stack, f.sp, opPC);
                int32 left = int32(uint32(_payload(f.stack[f.sp - 2])));
                int32 right = int32(uint32(_payload(f.stack[f.sp - 1])));
                f.sp -= 2;
                f.pc = _binaryCondition(op, left, right)
                    ? _decodedTarget(c.data, selection.codeOffset, opPC) : f.pc + 2;
            } else if (op == 0xa5 || op == 0xa6) { // if_acmpeq / if_acmpne
                if (f.sp < 2) revert BytecodeError(3, opPC);
                _requireKind(f.stack[f.sp - 2], KIND_REF, opPC);
                _requireKind(f.stack[f.sp - 1], KIND_REF, opPC);
                _validatePackedRef(f.stack[f.sp - 2], heapKinds, nextHandle, opPC);
                _validatePackedRef(f.stack[f.sp - 1], heapKinds, nextHandle, opPC);
                bool equal = _payload(f.stack[f.sp - 2]) == _payload(f.stack[f.sp - 1]);
                f.sp -= 2;
                f.pc = ((op == 0xa5) == equal)
                    ? _decodedTarget(c.data, selection.codeOffset, opPC) : f.pc + 2;
            } else if (op == 0xa7) {
                f.pc = _decodedTarget(c.data, selection.codeOffset, opPC);
            } else if (op == 0xaa || op == 0xab) { // tableswitch / lookupswitch
                if (f.sp == 0) revert BytecodeError(3, opPC);
                _requireKind(f.stack[f.sp - 1], KIND_INT, opPC);
                int32 key = int32(uint32(_payload(f.stack[f.sp - 1])));
                --f.sp;
                f.pc = _decodedSwitchTarget(
                    c.data, selection.codeOffset, opPC, key, op == 0xab
                );
            } else if (op == 0xc4) { // wide local access / iinc
                uint8 embedded = uint8(c.data[selection.codeOffset + f.pc]);
                uint256 local = _unsigned16(c.data, selection.codeOffset + f.pc + 1);
                if (embedded >= 0x15 && embedded <= 0x19) {
                    if (embedded == 0x19) f.sp = _loadReference(
                        f.stack, f.sp, f.locals, f.initialized, local, opPC
                    );
                    else if (embedded == 0x16) f.sp = _loadLong(
                        f.stack, f.sp, f.locals, f.initialized, local, opPC
                    );
                    else if (embedded == 0x18) f.sp = _loadDouble(
                        f.stack, f.sp, f.locals, f.initialized, local, opPC
                    );
                    else f.sp = _loadKind(
                        f.stack, f.sp, f.locals, f.initialized, local,
                        embedded == 0x17 ? KIND_FLOAT : KIND_INT, opPC
                    );
                    f.pc += 3;
                } else if (embedded >= 0x36 && embedded <= 0x3a) {
                    if (embedded == 0x3a) f.sp = _storeReference(
                        f.stack, f.sp, f.locals, f.initialized, local, opPC
                    );
                    else if (embedded == 0x37) f.sp = _storeLong(
                        f.stack, f.sp, f.locals, f.initialized, local, opPC
                    );
                    else if (embedded == 0x39) f.sp = _storeDouble(
                        f.stack, f.sp, f.locals, f.initialized, local, opPC
                    );
                    else f.sp = _storeKind(
                        f.stack, f.sp, f.locals, f.initialized, local,
                        embedded == 0x38 ? KIND_FLOAT : KIND_INT, opPC
                    );
                    f.pc += 3;
                } else { // the predecoder admits only supported wide iinc here
                    if (local >= f.locals.length) revert BytecodeError(8, opPC);
                    if (!f.initialized[local]) revert BytecodeError(11, opPC);
                    _requireKind(f.locals[local], KIND_INT, opPC);
                    int16 amount = _signed16(c.data, selection.codeOffset + f.pc + 3);
                    unchecked {
                        f.locals[local] = _packInt(
                            uint32(_payload(f.locals[local])) + uint32(int32(amount))
                        );
                    }
                    f.pc += 5;
                }
            } else if (op == 0xc8) { // goto_w
                f.pc = _decodedWideTarget(c.data, selection.codeOffset, opPC, opPC + 1);
            } else if (op == 0xbb) { // new
                uint256 refIndex = _unsigned16(c.data, selection.codeOffset + f.pc);
                f.pc += 2;
                uint256 allocatedClass = _resolveNewClass(
                    classes, f.classIndex, refIndex, opPC, referenceCaches[f.classIndex],
                    parentLinks, hierarchyState
                );
                if (allocatedClass == arena.stringClass) {
                    // SC0 permits only the pinned String allocation path. Resolve and
                    // parse the actual direct Object constructor before initialization
                    // or allocation can mutate Java-visible state.
                    _ensureStringLayout(
                        arena, classes, allocatedClass, parentLinks, hierarchyState
                    );
                    _requireStringObjectProfile(
                        classes, allocatedClass, opPC, parentLinks, hierarchyState, false
                    );
                } else if (_typeAssignable(classes, allocatedClass, arena.stringClass + 7, parentLinks)
                    || _typeAssignable(classes, allocatedClass, arena.stringClass + 8, parentLinks)
                    || _typeAssignable(classes, allocatedClass, arena.stringClass + 9, parentLinks)) {
                    _requireVFSObjectProfile(
                        classes, allocatedClass, opPC, parentLinks, hierarchyState
                    );
                }
                _rejectThrowableFillOverride(
                    classes, allocatedClass, arena.throwableClass, parentLinks
                );
                uint256 fieldSlots = objectLayoutsLoaded[allocatedClass]
                    ? objectFieldDefaults[allocatedClass].length
                    : _instanceFieldCount(classes, allocatedClass, parentLinks, opPC);
                if (initializationState[allocatedClass] == 3) {
                    nextHandle = _raiseJava(
                        12, opPC, arena, classes, objectHeap, heapKinds, heapClasses,
                        arrayLeafTypes, parentLinks, hierarchyState, nextHandle
                    );
                    continue;
                }
                if (initializationState[allocatedClass] == 0) {
                    uint256 oldDepth = depth;
                    arena.nextHandle = nextHandle;
                    depth = _initializeClass(
                        classes, staticValues, initializationState, frames, depth, allocatedClass,
                        parentLinks, hierarchyState, arena, opPC, objectHeap, heapKinds,
                        heapClasses, arrayLeafTypes, nextHandle
                    );
                    nextHandle = arena.nextHandle;
                    if (arena.heap.metadata.length != 0) {
                        arrayHeap = arena.heap.arrayHeap;
                        objectHeap = arena.heap.objectHeap;
                        arrayLeafTypes = arena.heap.metadata;
                        heapKinds = arrayLeafTypes;
                        heapClasses = arena.heap.classes;
                        arrayRanks = arena.heap.ranks;
                    }
                    if (arena.pending.active) continue;
                    if (depth != oldDepth) {
                        f.pc = opPC;
                        continue;
                    }
                }
                if (fieldSlots > MAX_OBJECT_FIELDS || arena.ordinaryObjectCount == MAX_OBJECTS
                    || fieldSlots > MAX_OBJECT_FIELD_SLOTS - arena.ordinaryFieldSlots) {
                    nextHandle = _raiseJava(
                        7, opPC, arena, classes, objectHeap, heapKinds, heapClasses,
                        arrayLeafTypes, parentLinks, hierarchyState, nextHandle
                    );
                if (arena.pending.active) continue;
                }
                _ensureExceptionRegistry(arena, classes, parentLinks, hierarchyState);
                if (heapKinds.length == 0) {
                    arrayHeap = arena.heap.arrayHeap;
                    objectHeap = arena.heap.objectHeap;
                    arrayLeafTypes = arena.heap.metadata;
                    heapKinds = arrayLeafTypes;
                    heapClasses = arena.heap.classes;
                    arrayRanks = arena.heap.ranks;
                    nextHandle = arena.nextHandle;
                }
                if (!objectLayoutsLoaded[allocatedClass]) {
                    objectFieldDefaults[allocatedClass] = _objectFieldDefaults(
                        classes, allocatedClass, fieldSlots, parentLinks
                    );
                    objectLayoutsLoaded[allocatedClass] = true;
                }
                ++arena.ordinaryObjectCount;
                ++nextHandle;
                arena.nextHandle = nextHandle;
                arena.ordinaryFieldSlots += fieldSlots;
                arrayLeafTypes[nextHandle] = HEAP_OBJECT_MARKER;
                heapClasses[nextHandle] = allocatedClass;
                objectHeap[nextHandle] = new uint256[](fieldSlots);
                for (uint256 i = 0; i < fieldSlots; ++i) {
                    objectHeap[nextHandle][i] = objectFieldDefaults[allocatedClass][i];
                }
                f.sp = _push(f.stack, f.sp, (KIND_UNINIT << KIND_SHIFT) | nextHandle, opPC);
            } else if (op == 0xb2 || op == 0xb3) { // getstatic / putstatic
                uint256 refIndex = _unsigned16(c.data, selection.codeOffset + f.pc);
                f.pc += 2;
                (uint256 fieldClass, uint256 field, uint8 fieldKind,) = _resolveField(
                    classes, f.classIndex, refIndex, opPC, fieldCaches[f.classIndex],
                    op == 0xb3, true, f.isInitializer, parentLinks, hierarchyState
                );
                if (initializationState[fieldClass] == 3) {
                    nextHandle = _raiseJava(
                        12, opPC, arena, classes, objectHeap, heapKinds, heapClasses,
                        arrayLeafTypes, parentLinks, hierarchyState, nextHandle
                    );
                    continue;
                }
                if (initializationState[fieldClass] == 0) {
                    uint256 oldDepth = depth;
                    arena.nextHandle = nextHandle;
                    depth = _initializeClass(
                        classes, staticValues, initializationState, frames, depth, fieldClass,
                        parentLinks, hierarchyState, arena, opPC, objectHeap, heapKinds,
                        heapClasses, arrayLeafTypes, nextHandle
                    );
                    nextHandle = arena.nextHandle;
                    if (arena.heap.metadata.length != 0) {
                        arrayHeap = arena.heap.arrayHeap;
                        objectHeap = arena.heap.objectHeap;
                        arrayLeafTypes = arena.heap.metadata;
                        heapKinds = arrayLeafTypes;
                        heapClasses = arena.heap.classes;
                        arrayRanks = arena.heap.ranks;
                    }
                    if (arena.pending.active) continue;
                    if (depth != oldDepth) {
                        f.pc = opPC;
                        continue;
                    }
                }
                if (op == 0xb2) {
                    if (fieldKind == KIND_REF) {
                        _validatePackedRef(staticValues[fieldClass][field], heapKinds, nextHandle, opPC);
                    }
                    f.sp = _push(f.stack, f.sp, staticValues[fieldClass][field], opPC);
                } else {
                    if (f.sp == 0) revert BytecodeError(3, opPC);
                    _requireKind(f.stack[f.sp - 1], fieldKind, opPC);
                    if (fieldKind == KIND_REF) {
                        FieldInfo memory staticField = classes[fieldClass].fields[field];
                        (uint256 fieldOff, uint256 fieldLen) =
                            _utf(classes[fieldClass].cp[staticField.descriptorIndex]);
                        _requireAssignable(
                            classes, f.stack[f.sp - 1], classes[fieldClass].data, fieldOff, fieldLen,
                            heapKinds, heapClasses, arrayRanks, arrayLeafTypes, nextHandle, parentLinks, opPC
                        );
                    }
                    uint256 stored = f.stack[f.sp - 1];
                    if (fieldKind == KIND_INT) {
                        stored = _normalizePackedInt(
                            stored, _fieldSubtype(classes[fieldClass], classes[fieldClass].fields[field])
                        );
                    }
                    staticValues[fieldClass][field] = stored;
                    --f.sp;
                }
            } else if (op == 0xb4 || op == 0xb5) { // getfield / putfield
                uint256 refIndex = _unsigned16(c.data, selection.codeOffset + f.pc);
                f.pc += 2;
                (uint256 fieldClass, uint256 field, uint8 fieldKind, uint256 symbolicClass) =
                    _resolveField(
                        classes, f.classIndex, refIndex, opPC, fieldCaches[f.classIndex],
                        op == 0xb5, false, f.isConstructor, parentLinks, hierarchyState
                    );
                uint256 needed = op == 0xb4 ? 1 : 2;
                if (f.sp < needed) revert BytecodeError(3, opPC);
                uint256 receiverSlot = f.sp - needed;
                uint256 receiver = f.stack[receiverSlot];
                uint256 receiverKind = _valueKind(receiver);
                uint256 handle = _payload(receiver);
                bool preSuperWrite = op == 0xb5 && receiverKind == KIND_UNINIT
                    && f.isConstructor && f.thisHandle == handle && f.classIndex == fieldClass;
                if (!preSuperWrite) _requireKind(receiver, KIND_REF, opPC);
                if (handle == 0) nextHandle = _raiseJava(
                        6, opPC, arena, classes, objectHeap, heapKinds, heapClasses,
                        arrayLeafTypes, parentLinks, hierarchyState, nextHandle
                    );
                if (arena.pending.active) continue;
                _requireHeapKind(handle, heapKinds, nextHandle, HEAP_OBJECT, opPC);
                if (!_objectIsClass(heapClasses[handle], symbolicClass, parentLinks)) {
                    revert ReferenceError(2, opPC);
                }
                _requireProtectedReceiver(
                    classes, f.classIndex, fieldClass,
                    classes[fieldClass].fields[field].accessFlags, heapClasses[handle],
                    parentLinks, opPC
                );
                uint256 objectOffset = _instanceFieldOffset(
                    classes, heapClasses[handle], fieldClass, field, parentLinks, opPC
                );
                if (op == 0xb4) {
                    if (_isCategory2Kind(fieldKind)) _requireExtraWords(f.stack, f.sp, 1, opPC);
                    f.stack[receiverSlot] = objectHeap[handle][objectOffset];
                } else {
                    uint256 fieldValue = f.stack[f.sp - 1];
                    _requireKind(fieldValue, fieldKind, opPC);
                    if (fieldKind == KIND_REF) {
                        FieldInfo memory instanceField = classes[fieldClass].fields[field];
                        (uint256 fieldOff, uint256 fieldLen) =
                            _utf(classes[fieldClass].cp[instanceField.descriptorIndex]);
                        _requireAssignable(
                            classes, fieldValue, classes[fieldClass].data, fieldOff, fieldLen,
                            heapKinds, heapClasses, arrayRanks, arrayLeafTypes, nextHandle, parentLinks, opPC
                        );
                    }
                    if (fieldKind == KIND_INT) {
                        fieldValue = _normalizePackedInt(
                            fieldValue, _fieldSubtype(classes[fieldClass], classes[fieldClass].fields[field])
                        );
                        _maybeBindVFSHandle(
                            classes, fieldClass, field, handle, fieldValue, f, depth,
                            state.vfs, parentLinks, opPC
                        );
                    }
                    objectHeap[handle][objectOffset] = fieldValue;
                    f.sp -= 2;
                }
            } else if (op == 0xb6) { // invokevirtual
                uint256 refIndex = _unsigned16(c.data, selection.codeOffset + f.pc);
                f.pc += 2;
                VirtualResolution memory resolved = _resolveVirtual(
                    classes, f.classIndex, refIndex, opPC, parentLinks, hierarchyState
                );
                if (resolved.javaFault != 0) {
                    nextHandle = _raiseJava(
                        resolved.javaFault, opPC, arena, classes, objectHeap, heapKinds,
                        heapClasses, arrayLeafTypes, parentLinks, hierarchyState, nextHandle
                    );
                    continue;
                }
                Selected memory signature = _loadVirtualSignature(
                    classes[resolved.owner], resolved.method, opPC
                );
                uint8 resolvedStringBinding = _stringNativeBinding(
                    classes[resolved.owner], resolved.method
                );
                if (f.sp < signature.argumentCount + 1) revert BytecodeError(3, opPC);
                uint256 base = f.sp - signature.argumentCount - 1;
                uint256 receiver = f.stack[base];
                _requireKind(receiver, KIND_REF, opPC);
                for (uint256 i = 0; i < signature.argumentCount; ++i) {
                    uint256 argument = f.stack[base + 1 + i];
                    _requireKind(argument, signature.argumentKinds[i], opPC);
                    if (signature.argumentKinds[i] == KIND_REF
                        && !(resolvedStringBinding == 7 && i == 0)) {
                        _requireAssignable(
                            classes, argument, classes[resolved.owner].data,
                            signature.argumentTypeOffsets[i], signature.argumentTypeLengths[i],
                            heapKinds, heapClasses, arrayRanks, arrayLeafTypes, nextHandle, parentLinks, opPC
                        );
                    }
                }
                uint256 handle = _payload(receiver);
                if (handle == 0) nextHandle = _raiseJava(
                        6, opPC, arena, classes, objectHeap, heapKinds, heapClasses,
                        arrayLeafTypes, parentLinks, hierarchyState, nextHandle
                    );
                if (arena.pending.active) continue;
                _validatePackedRef(receiver, heapKinds, nextHandle, opPC);
                if (_heapKindAt(heapKinds[handle]) == HEAP_ARRAY) {
                    // A valid array receiver is deliberately deferred after symbolic
                    // method resolution, before ordinary-object assignability/selection.
                    revert CallError(4, opPC);
                }
                if (_heapKindAt(heapKinds[handle]) != HEAP_OBJECT) revert ReferenceError(1, opPC);
                uint256 dynamicClass = heapClasses[handle];
                if (!_objectIsClass(dynamicClass, resolved.symbolic, parentLinks)) {
                    revert ReferenceError(2, opPC);
                }
                _requireProtectedMethodReceiver(
                    classes, f.classIndex, resolved.owner,
                    uint16(classes[resolved.owner].methods[resolved.method]), dynamicClass,
                    parentLinks, opPC
                );
                (uint256 calleeClass, uint256 callee) = _selectVirtual(
                    classes, dynamicClass, resolved, parentLinks, opPC
                );
                if (calleeClass == type(uint256).max) {
                    nextHandle = _raiseJava(
                        callee, opPC, arena, classes, objectHeap, heapKinds, heapClasses,
                        arrayLeafTypes, parentLinks, hierarchyState, nextHandle
                    );
                    continue;
                }
                if (selected[calleeClass].length == 0) {
                    selected[calleeClass] = new Selected[][](classes[calleeClass].methods.length);
                    referenceCaches[calleeClass] = new uint256[](classes[calleeClass].cp.length);
                    fieldCaches[calleeClass] = new uint256[](classes[calleeClass].cp.length);
                }
                uint8 stringBinding = _stringNativeBinding(classes[calleeClass], callee);
                if (!_selectionLoaded(selected, calleeClass, callee)) {
                    Selected memory loadedTarget = stringBinding == 0
                        ? _loadVirtualCallee(classes[calleeClass], callee, opPC, calleeClass)
                        : _loadStringNativeCallee(classes[calleeClass], callee, opPC, calleeClass);
                    if (stringBinding == 0) _predecode(classes[calleeClass], loadedTarget);
                    _putSelection(selected, calleeClass, callee, loadedTarget);
                }
                Selected memory target = selected[calleeClass][callee][0];
                if (!_sameMethodDescriptor(classes[resolved.owner], resolved.method,
                    classes[calleeClass], callee)) revert CallError(4, opPC);
                _guardCanonicalThrowableGetter(
                    classes, calleeClass, callee, handle, arena, opPC
                );
                if (stringBinding != 0) {
                    if (stringBinding == 9) revert StringProfileError(1, opPC);
                    if (stringBinding == 7) {
                        uint256 argumentHandle = _payload(f.stack[base + 1]);
                        if (argumentHandle == 0) {
                            nextHandle = _raiseJava(
                                6, opPC, arena, classes, objectHeap, heapKinds, heapClasses,
                                arrayLeafTypes, parentLinks, hierarchyState, nextHandle
                            );
                            continue;
                        }
                        if (argumentHandle > arena.nextHandle
                            || _heapKindAt(arena.heap.metadata[argumentHandle]) != HEAP_OBJECT
                            || arena.heap.classes[argumentHandle] != arena.stringClass) {
                            revert BytecodeError(14, opPC);
                        }
                    }
                    if (stringBinding == 8) {
                        (uint256 interned, bool oom) = _internStringReceiver(arena, handle, opPC);
                        if (oom) {
                            nextHandle = _raiseJava(
                                7, opPC, arena, classes, objectHeap, heapKinds,
                                heapClasses, arrayLeafTypes, parentLinks,
                                hierarchyState, nextHandle
                            );
                            continue;
                        }
                        f.stack[base] = _packRef(uint32(interned));
                    } else {
                        f.stack[base] = _runStringNative(
                            stringBinding, f, base, handle, arena, opPC
                        );
                    }
                    f.sp = base + 1;
                    continue;
                }
                if (depth == MAX_FRAMES) {
                    nextHandle = _raiseJava(
                        2, opPC, arena, classes, objectHeap, heapKinds, heapClasses,
                        arrayLeafTypes, parentLinks, hierarchyState, nextHandle
                    );
                    continue;
                }
                Frame memory child = _newFrame(calleeClass, callee, target, opPC);
                child.locals[0] = receiver;
                child.initialized[0] = true;
                _copyArguments(child, target, f.stack, base + 1, 1);
                f.sp = base;
                frames[depth] = child;
                ++depth;
            } else if (op == 0xb7) { // invokespecial
                uint256 refIndex = _unsigned16(c.data, selection.codeOffset + f.pc);
                f.pc += 2;
                bool interfaceSpecial = refIndex != 0 && refIndex < c.cp.length
                    && uint8(c.cp[refIndex]) == 11;
                if (interfaceSpecial) {
                    VirtualResolution memory interfaceResolved = _resolveInterfaceSpecial(
                        classes, f.classIndex, f.methodIndex, refIndex, opPC,
                        parentLinks, hierarchyState
                    );
                    if (interfaceResolved.javaFault != 0) {
                        nextHandle = _raiseJava(
                            interfaceResolved.javaFault, opPC, arena, classes, objectHeap,
                            heapKinds, heapClasses, arrayLeafTypes, parentLinks, hierarchyState, nextHandle
                        );
                        continue;
                    }
                    Selected memory interfaceSignature = _loadVirtualSignature(
                        classes[interfaceResolved.owner], interfaceResolved.method, opPC
                    );
                    if (f.sp < interfaceSignature.argumentCount + 1) {
                        revert BytecodeError(3, opPC);
                    }
                    uint256 interfaceBase = f.sp - interfaceSignature.argumentCount - 1;
                    uint256 interfaceReceiver = f.stack[interfaceBase];
                    _requireKind(interfaceReceiver, KIND_REF, opPC);
                    if (f.locals.length == 0 || !f.initialized[0]) revert CallError(4, opPC);
                    _requireKind(f.locals[0], KIND_REF, opPC);
                    for (uint256 i = 0; i < interfaceSignature.argumentCount; ++i) {
                        uint256 argument = f.stack[interfaceBase + 1 + i];
                        _requireKind(argument, interfaceSignature.argumentKinds[i], opPC);
                        if (interfaceSignature.argumentKinds[i] == KIND_REF) {
                            _requireAssignable(
                                classes, argument, classes[interfaceResolved.owner].data,
                                interfaceSignature.argumentTypeOffsets[i],
                                interfaceSignature.argumentTypeLengths[i], heapKinds, heapClasses,
                                arrayRanks, arrayLeafTypes, nextHandle, parentLinks, opPC
                            );
                        }
                    }
                    uint256 interfaceHandle = _payload(interfaceReceiver);
                    if (interfaceHandle == 0) nextHandle = _raiseJava(
                        6, opPC, arena, classes, objectHeap, heapKinds, heapClasses,
                        arrayLeafTypes, parentLinks, hierarchyState, nextHandle
                    );
                if (arena.pending.active) continue;
                    if (interfaceReceiver != f.locals[0]) revert CallError(4, opPC);
                    _requireHeapKind(
                        interfaceHandle, heapKinds, nextHandle, HEAP_OBJECT, opPC
                    );
                    uint256 interfaceClass = interfaceResolved.owner;
                    uint256 interfaceMethod = interfaceResolved.method;
                    if (selected[interfaceClass].length == 0) {
                        selected[interfaceClass] =
                            new Selected[][](classes[interfaceClass].methods.length);
                        referenceCaches[interfaceClass] = new uint256[](classes[interfaceClass].cp.length);
                        fieldCaches[interfaceClass] = new uint256[](classes[interfaceClass].cp.length);
                    }
                    if (!_selectionLoaded(selected, interfaceClass, interfaceMethod)) {
                        Selected memory loadedInterfaceTarget = _loadVirtualCallee(
                            classes[interfaceClass], interfaceMethod, opPC, interfaceClass
                        );
                        _predecode(classes[interfaceClass], loadedInterfaceTarget);
                        _putSelection(
                            selected, interfaceClass, interfaceMethod, loadedInterfaceTarget
                        );
                    }
                    Selected memory interfaceTarget =
                        selected[interfaceClass][interfaceMethod][0];
                    if (depth == MAX_FRAMES) {
                    nextHandle = _raiseJava(
                        2, opPC, arena, classes, objectHeap, heapKinds, heapClasses,
                        arrayLeafTypes, parentLinks, hierarchyState, nextHandle
                    );
                    continue;
                }
                    Frame memory interfaceChild = _newFrame(
                        interfaceClass, interfaceMethod, interfaceTarget, opPC
                    );
                    interfaceChild.locals[0] = interfaceReceiver;
                    interfaceChild.initialized[0] = true;
                    _copyArguments(
                        interfaceChild, interfaceTarget, f.stack, interfaceBase + 1, 1
                    );
                    f.sp = interfaceBase;
                    frames[depth] = interfaceChild;
                    ++depth;
                    continue;
                }
                (uint256 calleeClass, uint256 callee, uint256 symbolicClass, bool isConstructor) =
                    _resolveSpecial(
                        classes, f.classIndex, refIndex, opPC, referenceCaches[f.classIndex],
                        parentLinks, hierarchyState
                    );
                uint8 vfsBinding = _vfsNativeBinding(classes[calleeClass], callee);
                if (vfsBinding == 0) _validateSpecialCalleeMetadata(
                    classes[calleeClass], callee, opPC, isConstructor
                );
                if (selected[calleeClass].length == 0) {
                    selected[calleeClass] = new Selected[][](classes[calleeClass].methods.length);
                    referenceCaches[calleeClass] = new uint256[](classes[calleeClass].cp.length);
                    fieldCaches[calleeClass] = new uint256[](classes[calleeClass].cp.length);
                }
                if (!_selectionLoaded(selected, calleeClass, callee)) {
                    Selected memory loadedTarget = vfsBinding == 0
                        ? _loadSpecialCallee(
                            classes[calleeClass], callee, opPC, isConstructor, calleeClass
                        )
                        : _loadVFSNativeCallee(
                            classes[calleeClass], callee, opPC, calleeClass
                        );
                    if (vfsBinding == 0) _predecode(classes[calleeClass], loadedTarget);
                    _putSelection(selected, calleeClass, callee, loadedTarget);
                }
                Selected memory target = selected[calleeClass][callee][0];
                if (isConstructor && target.returnKind != 2) revert CallError(4, opPC);
                if (f.sp < target.argumentCount + 1) revert BytecodeError(3, opPC);
                uint256 base = f.sp - target.argumentCount - 1;
                uint256 receiver = f.stack[base];
                uint256 handle = _payload(receiver);
                if (isConstructor) {
                    _requireKind(receiver, KIND_UNINIT, opPC);
                    _requireHeapKind(handle, heapKinds, nextHandle, HEAP_OBJECT, opPC);
                    uint256 allocatedClass = heapClasses[handle];
                    bool constructingThis = f.isConstructor && f.thisHandle == handle;
                    if (constructingThis) {
                        uint256 directParent = parentLinks[f.classIndex];
                        bool validThisOrSuper = symbolicClass == f.classIndex
                            || (directParent != 0 && directParent != type(uint256).max
                                && symbolicClass == directParent - 1);
                        if (!validThisOrSuper) revert ObjectError(3, opPC);
                    } else if (symbolicClass != allocatedClass) {
                        revert ObjectError(3, opPC);
                    }
                    uint16 constructorAccess = uint16(classes[calleeClass].methods[callee]);
                    if ((constructorAccess & 0x0004) != 0
                        && !_samePackage(classes[f.classIndex], classes[calleeClass])
                        && !constructingThis) revert CallError(4, opPC);
                } else {
                    _requireKind(receiver, KIND_REF, opPC);
                    if (handle == 0) nextHandle = _raiseJava(
                        6, opPC, arena, classes, objectHeap, heapKinds, heapClasses,
                        arrayLeafTypes, parentLinks, hierarchyState, nextHandle
                    );
                if (arena.pending.active) continue;
                    _requireHeapKind(handle, heapKinds, nextHandle, HEAP_OBJECT, opPC);
                    if (!_objectIsClass(heapClasses[handle], symbolicClass, parentLinks)) {
                        revert ReferenceError(2, opPC);
                    }
                    uint16 methodAccess = uint16(classes[calleeClass].methods[callee]);
                    if ((methodAccess & 0x0004) != 0 && f.classIndex != calleeClass
                        && !_samePackage(classes[f.classIndex], classes[calleeClass])
                        && !_objectIsClass(heapClasses[handle], f.classIndex, parentLinks)) {
                        revert CallError(4, opPC);
                    }
                }
                bool stringConstructor = isConstructor && calleeClass == arena.stringClass;
                for (uint256 i = 0; i < target.argumentCount; ++i) {
                    uint256 argument = f.stack[base + 1 + i];
                    if (stringConstructor && i == 0) {
                        // SC0's two constructors require an initialized reference tag.
                        // Null is passed into genuine Code so arraylength/getfield raises NPE.
                        if (_valueKind(argument) != KIND_REF
                            || !_supportedStringSource(
                                classes[calleeClass], target, argument, heapKinds,
                                heapClasses, arrayRanks, arrayLeafTypes, nextHandle,
                                arena.stringClass
                            )) revert CallError(4, opPC);
                    } else {
                        _requireKind(argument, target.argumentKinds[i], opPC);
                        if (target.argumentKinds[i] == KIND_REF) {
                            _requireAssignable(
                                classes, argument, classes[calleeClass].data,
                                target.argumentTypeOffsets[i], target.argumentTypeLengths[i], heapKinds, heapClasses, arrayRanks, arrayLeafTypes,
                                nextHandle, parentLinks, opPC
                            );
                        }
                    }
                }
                if (!isConstructor) _guardCanonicalThrowableGetter(
                    classes, calleeClass, callee, handle, arena, opPC
                );
                if (vfsBinding != 0) {
                    f.stack[base] = _runVFSNative(
                        vfsBinding, f, base, handle, arena, classes, parentLinks,
                        state.vfs, depth, opPC
                    );
                    f.sp = base + 1;
                    continue;
                }
                if (depth == MAX_FRAMES) {
                    nextHandle = _raiseJava(
                        2, opPC, arena, classes, objectHeap, heapKinds, heapClasses,
                        arrayLeafTypes, parentLinks, hierarchyState, nextHandle
                    );
                    continue;
                }
                Frame memory child = _newFrame(calleeClass, callee, target, opPC);
                child.locals[0] = isConstructor && _isObjectClass(classes[calleeClass])
                    ? _packRef(uint32(handle)) : receiver;
                child.initialized[0] = true;
                child.isConstructor = isConstructor;
                child.isConstructorLinked = isConstructor && _isObjectClass(classes[calleeClass]);
                child.thisHandle = handle;
                _copyArguments(child, target, f.stack, base + 1, 1);
                f.sp = base;
                frames[depth] = child;
                ++depth;
            } else if (op == 0xb8) { // invokestatic
                uint256 refIndex = _unsigned16(c.data, selection.codeOffset + f.pc);
                f.pc += 2;
                (uint256 calleeClass, uint256 callee) = _resolveCall(
                    classes, f.classIndex, refIndex, opPC, referenceCaches[f.classIndex], bundleMode,
                    parentLinks, hierarchyState
                );
                uint8 nativeBinding = _nativeBinding(classes[calleeClass], callee);
                if (nativeBinding == 0) _validateStaticCalleeMetadata(
                    classes[calleeClass], callee, opPC
                );
                else _validateNativeBinding(classes[calleeClass], callee, opPC);
                if (selected[calleeClass].length == 0) {
                    selected[calleeClass] = new Selected[][](classes[calleeClass].methods.length);
                    referenceCaches[calleeClass] = new uint256[](classes[calleeClass].cp.length);
                    fieldCaches[calleeClass] = new uint256[](classes[calleeClass].cp.length);
                }
                // Finish selected-method descriptor/Code/native validation before an
                // active-use initialization can produce unrelated side effects.
                if (!_selectionLoaded(selected, calleeClass, callee)) {
                    Selected memory loadedTarget = nativeBinding == 0
                        ? _loadCallee(classes[calleeClass], callee, opPC, calleeClass)
                        : _loadNativeCallee(classes[calleeClass], callee, opPC);
                    if (nativeBinding == 0) _predecode(classes[calleeClass], loadedTarget);
                    _putSelection(selected, calleeClass, callee, loadedTarget);
                }
                if (initializationState[calleeClass] == 3) {
                    nextHandle = _raiseJava(
                        12, opPC, arena, classes, objectHeap, heapKinds, heapClasses,
                        arrayLeafTypes, parentLinks, hierarchyState, nextHandle
                    );
                    continue;
                }
                if (initializationState[calleeClass] == 0) {
                    uint256 oldDepth = depth;
                    arena.nextHandle = nextHandle;
                    depth = _initializeClass(
                        classes, staticValues, initializationState, frames, depth, calleeClass,
                        parentLinks, hierarchyState, arena, opPC, objectHeap, heapKinds,
                        heapClasses, arrayLeafTypes, nextHandle
                    );
                    nextHandle = arena.nextHandle;
                    if (arena.heap.metadata.length != 0) {
                        arrayHeap = arena.heap.arrayHeap;
                        objectHeap = arena.heap.objectHeap;
                        arrayLeafTypes = arena.heap.metadata;
                        heapKinds = arrayLeafTypes;
                        heapClasses = arena.heap.classes;
                        arrayRanks = arena.heap.ranks;
                    }
                    if (arena.pending.active) continue;
                    if (depth != oldDepth) {
                        f.pc = opPC;
                        continue;
                    }
                }
                Selected memory target = selected[calleeClass][callee][0];
                if (f.sp < target.argumentCount) revert BytecodeError(3, opPC);
                uint256 base = f.sp - target.argumentCount;
                for (uint256 i = 0; i < target.argumentCount; ++i) {
                    _requireKind(f.stack[base + i], target.argumentKinds[i], opPC);
                    if (target.argumentKinds[i] == KIND_REF) {
                        _requireAssignable(
                            classes, f.stack[base + i], classes[calleeClass].data,
                            target.argumentTypeOffsets[i], target.argumentTypeLengths[i],
                            heapKinds, heapClasses, arrayRanks, arrayLeafTypes, nextHandle, parentLinks, opPC
                        );
                    }
                }
                if (depth == MAX_FRAMES) {
                    nextHandle = _raiseJava(
                        2, opPC, arena, classes, objectHeap, heapKinds, heapClasses,
                        arrayLeafTypes, parentLinks, hierarchyState, nextHandle
                    );
                    continue;
                }
                if (nativeBinding != 0) {
                    if (nativeBinding == 5) {
                        nextHandle = _runSystemArraycopy(
                            f.stack, base, arrayHeap, arena, classes, objectHeap, heapKinds,
                            heapClasses, arrayRanks, arrayLeafTypes, parentLinks,
                            hierarchyState, nextHandle, opPC
                        );
                        f.sp = base;
                        continue;
                    }
                    uint64 raw = uint64(_payload(f.stack[base]));
                    if (nativeBinding == 1) f.stack[base] = _packFloat(uint32(raw));
                    else if (nativeBinding == 2) f.stack[base] = _packInt(uint32(raw));
                    else if (nativeBinding == 3) f.stack[base] = _packDouble(raw);
                    else f.stack[base] = _packLong(raw);
                    f.sp = base + 1;
                    continue;
                }
                Frame memory child = _newFrame(calleeClass, callee, target, opPC);
                _copyArguments(child, target, f.stack, base, 0);
                f.sp = base;
                frames[depth] = child;
                ++depth;
            } else if (op == 0xb9) { // invokeinterface
                uint256 refIndex = _unsigned16(c.data, selection.codeOffset + f.pc);
                uint8 count = uint8(c.data[selection.codeOffset + f.pc + 2]);
                uint8 trailing = uint8(c.data[selection.codeOffset + f.pc + 3]);
                f.pc += 4;
                VirtualResolution memory resolved = _resolveInterfaceCall(
                    classes, f.classIndex, refIndex, opPC, parentLinks, hierarchyState
                );
                if (resolved.javaFault != 0) {
                    nextHandle = _raiseJava(
                        resolved.javaFault, opPC, arena, classes, objectHeap, heapKinds,
                        heapClasses, arrayLeafTypes, parentLinks, hierarchyState, nextHandle
                    );
                    continue;
                }
                Selected memory signature = _loadVirtualSignature(
                    classes[resolved.owner], resolved.method, opPC
                );
                if (count == 0 || trailing != 0 || signature.argumentWords + 1 != count) {
                    revert CallError(1, opPC);
                }
                if (f.sp < signature.argumentCount + 1) revert BytecodeError(3, opPC);
                uint256 base = f.sp - signature.argumentCount - 1;
                uint256 receiver = f.stack[base];
                _requireKind(receiver, KIND_REF, opPC);
                for (uint256 i = 0; i < signature.argumentCount; ++i) {
                    uint256 argument = f.stack[base + 1 + i];
                    _requireKind(argument, signature.argumentKinds[i], opPC);
                    if (signature.argumentKinds[i] == KIND_REF) {
                        _requireAssignable(
                            classes, argument, classes[resolved.owner].data,
                            signature.argumentTypeOffsets[i], signature.argumentTypeLengths[i],
                            heapKinds, heapClasses, arrayRanks, arrayLeafTypes,
                            nextHandle, parentLinks, opPC
                        );
                    }
                }
                uint256 handle = _payload(receiver);
                if (handle == 0) nextHandle = _raiseJava(
                        6, opPC, arena, classes, objectHeap, heapKinds, heapClasses,
                        arrayLeafTypes, parentLinks, hierarchyState, nextHandle
                    );
                if (arena.pending.active) continue;
                _validatePackedRef(receiver, heapKinds, nextHandle, opPC);
                if (_heapKindAt(heapKinds[handle]) == HEAP_ARRAY) {
                    if (!_arrayImplementsClass(classes, resolved.symbolic)) {
                        revert ReferenceError(2, opPC);
                    }
                    revert CallError(4, opPC);
                }
                if (_heapKindAt(heapKinds[handle]) != HEAP_OBJECT) revert ReferenceError(1, opPC);
                uint256 dynamicClass = heapClasses[handle];
                if (!_classImplements(classes, dynamicClass, resolved.symbolic, parentLinks)) {
                    revert ReferenceError(2, opPC);
                }
                (uint256 calleeClass, uint256 callee) = _selectInterfaceImplementation(
                    classes, dynamicClass, c.data, resolved.nameOffset, resolved.nameLength,
                    resolved.descriptorOffset, resolved.descriptorLength, parentLinks, opPC
                );
                if (calleeClass == type(uint256).max) {
                    nextHandle = _raiseJava(
                        callee, opPC, arena, classes, objectHeap, heapKinds, heapClasses,
                        arrayLeafTypes, parentLinks, hierarchyState, nextHandle
                    );
                    continue;
                }
                if (selected[calleeClass].length == 0) {
                    selected[calleeClass] = new Selected[][](classes[calleeClass].methods.length);
                    referenceCaches[calleeClass] = new uint256[](classes[calleeClass].cp.length);
                    fieldCaches[calleeClass] = new uint256[](classes[calleeClass].cp.length);
                }
                uint8 interfaceStringBinding = _stringNativeBinding(classes[calleeClass], callee);
                if (!_selectionLoaded(selected, calleeClass, callee)) {
                    Selected memory loadedTarget = interfaceStringBinding == 0
                        ? _loadVirtualCallee(classes[calleeClass], callee, opPC, calleeClass)
                        : _loadStringNativeCallee(classes[calleeClass], callee, opPC, calleeClass);
                    if (interfaceStringBinding == 0) _predecode(classes[calleeClass], loadedTarget);
                    _putSelection(selected, calleeClass, callee, loadedTarget);
                }
                Selected memory target = selected[calleeClass][callee][0];
                if (!_sameMethodDescriptor(classes[resolved.owner], resolved.method,
                    classes[calleeClass], callee)) revert CallError(4, opPC);
                _guardCanonicalThrowableGetter(
                    classes, calleeClass, callee, handle, arena, opPC
                );
                if (interfaceStringBinding != 0) {
                    if (interfaceStringBinding == 9) revert StringProfileError(1, opPC);
                    if (interfaceStringBinding == 8) {
                        (uint256 interned, bool oom) = _internStringReceiver(arena, handle, opPC);
                        if (oom) {
                            nextHandle = _raiseJava(
                                7, opPC, arena, classes, objectHeap, heapKinds,
                                heapClasses, arrayLeafTypes, parentLinks,
                                hierarchyState, nextHandle
                            );
                            continue;
                        }
                        f.stack[base] = _packRef(uint32(interned));
                    } else {
                        f.stack[base] = _runStringNative(
                            interfaceStringBinding, f, base, handle, arena, opPC
                        );
                    }
                    f.sp = base + 1;
                    continue;
                }
                if (depth == MAX_FRAMES) {
                    nextHandle = _raiseJava(
                        2, opPC, arena, classes, objectHeap, heapKinds, heapClasses,
                        arrayLeafTypes, parentLinks, hierarchyState, nextHandle
                    );
                    continue;
                }
                Frame memory child = _newFrame(calleeClass, callee, target, opPC);
                child.locals[0] = receiver;
                child.initialized[0] = true;
                _copyArguments(child, target, f.stack, base + 1, 1);
                f.sp = base;
                frames[depth] = child;
                ++depth;
            } else if (op >= 0xac && op <= 0xb1) {
                // ireturn / lreturn / freturn / dreturn / areturn / return
                uint8 actualKind = op == 0xac ? uint8(KIND_INT)
                    : (op == 0xad ? uint8(KIND_LONG)
                        : (op == 0xae ? uint8(KIND_FLOAT)
                            : (op == 0xaf ? uint8(KIND_DOUBLE)
                                : (op == 0xb0 ? uint8(KIND_REF) : uint8(0)))));
                uint8 descriptorKind = actualKind == 0 ? 2
                    : (actualKind == KIND_REF ? 3
                        : (actualKind == KIND_LONG ? 4
                            : (actualKind == KIND_FLOAT ? 5
                                : (actualKind == KIND_DOUBLE ? 6 : 1))));
                if (descriptorKind != selection.returnKind) revert CallError(5, opPC);
                if ((actualKind != 0 && f.sp != 1) || (actualKind == 0 && f.sp != 0)) {
                    revert BytecodeError(4, opPC);
                }
                if (f.isConstructor && !_isObjectClass(c) && !f.isConstructorLinked) {
                    revert ObjectError(3, opPC);
                }
                uint256 value;
                if (actualKind != 0) {
                    _requireKind(f.stack[0], actualKind, opPC);
                    if (actualKind == KIND_REF) {
                        _requireAssignable(
                            classes, f.stack[0], c.data, selection.returnTypeOffset,
                            selection.returnTypeLength, heapKinds, heapClasses, arrayRanks, arrayLeafTypes, nextHandle,
                            parentLinks, opPC
                        );
                    }
                    value = actualKind == KIND_INT
                        ? _normalizePackedInt(f.stack[0], selection.returnSubtype)
                        : f.stack[0];
                }
                if (depth == 1) {
                    // MR0's only externally selected root returns actual Java void.
                    if (actualKind != 0) revert MethodError(11);
                    state.result = 0;
                    state.lifecycle = 2;
                    depth = 0;
                    continue;
                }
                uint256 callPC = f.callPC;
                bool completedConstructor = f.isConstructor;
                uint256 completedHandle = f.thisHandle;
                --depth;
                Frame memory caller = frames[depth - 1];
                if (completedConstructor) {
                    _initializeAliases(caller, completedHandle);
                    if (caller.isConstructor && caller.thisHandle == completedHandle) {
                        caller.isConstructorLinked = true;
                    }
                }
                if (actualKind != 0) {
                    caller.sp = _push(caller.stack, caller.sp, value, callPC);
                }
            } else if (op == 0xbc || op == 0xbd) { // newarray / anewarray
                if (f.sp == 0) revert BytecodeError(3, opPC);
                _requireKind(f.stack[f.sp - 1], KIND_INT, opPC);
                ArrayType memory allocatedType;
                if (op == 0xbc) {
                    uint8 atype = uint8(c.data[selection.codeOffset + f.pc]);
                    ++f.pc;
                    allocatedType.rank = 1;
                    allocatedType.leafType = _newArrayPrimitive(atype);
                    if (allocatedType.leafType == 0) revert ArrayError(1, opPC);
                } else {
                    uint256 refIndex = _unsigned16(c.data, selection.codeOffset + f.pc);
                    f.pc += 2;
                    allocatedType = _resolveANewArrayType(
                        classes, f.classIndex, refIndex, opPC, parentLinks, hierarchyState
                    );
                }
                int32 signedLength = int32(uint32(_payload(f.stack[f.sp - 1])));
                if (signedLength < 0) nextHandle = _raiseJava(
                        4, opPC, arena, classes, objectHeap, heapKinds, heapClasses,
                        arrayLeafTypes, parentLinks, hierarchyState, nextHandle
                    );
                if (arena.pending.active) continue;
                uint256 length = uint256(uint32(signedLength));
                if (
                    arena.ordinaryArrayCount == MAX_ARRAYS || length > MAX_ARRAY_LENGTH
                        || length > MAX_ARRAY_ELEMENTS - arena.ordinaryArrayElements
                ) nextHandle = _raiseJava(
                        7, opPC, arena, classes, objectHeap, heapKinds, heapClasses,
                        arrayLeafTypes, parentLinks, hierarchyState, nextHandle
                    );
                if (arena.pending.active) continue;
                _ensureExceptionRegistry(arena, classes, parentLinks, hierarchyState);
                if (arena.heap.arrayHeap.length == 0) {
                    arena.heap.arrayHeap = new uint64[][](MAX_HANDLES + 1);
                    arena.heap.ranks = new uint8[](MAX_HANDLES + 1);
                }
                arrayHeap = arena.heap.arrayHeap;
                objectHeap = arena.heap.objectHeap;
                arrayLeafTypes = arena.heap.metadata;
                heapKinds = arrayLeafTypes;
                heapClasses = arena.heap.classes;
                arrayRanks = arena.heap.ranks;
                nextHandle = arena.nextHandle;
                ++arena.ordinaryArrayCount;
                ++nextHandle;
                arena.nextHandle = nextHandle;
                arena.ordinaryArrayElements += length;
                arrayRanks[nextHandle] = allocatedType.rank;
                arrayLeafTypes[nextHandle] = allocatedType.leafType;
                arrayHeap[nextHandle] = new uint64[](length);
                f.stack[f.sp - 1] = _packRef(uint32(nextHandle));
            } else if (op == 0xc5) { // multianewarray
                uint256 refIndex = _unsigned16(c.data, selection.codeOffset + f.pc);
                uint8 dimensions = uint8(c.data[selection.codeOffset + f.pc + 2]);
                f.pc += 3;
                ArrayType memory allocatedType = _resolveMultiArrayType(
                    classes, f.classIndex, refIndex, dimensions, opPC,
                    parentLinks, hierarchyState
                );
                if (f.sp < dimensions) revert BytecodeError(3, opPC);
                uint256 base = f.sp - dimensions;
                MultiArrayPlan memory plan;
                plan.counts = new uint256[](dimensions);
                bool negative;
                for (uint256 i = 0; i < dimensions; ++i) {
                    _requireKind(f.stack[base + i], KIND_INT, opPC);
                    int32 signedCount = int32(uint32(_payload(f.stack[base + i])));
                    if (signedCount < 0) negative = true;
                    else plan.counts[i] = uint256(uint32(signedCount));
                }
                // Every count is type-checked and inspected before either quota planning or
                // allocation. In particular, a zero outer dimension does not hide a later
                // negative dimension, and an over-cap positive count does not win over NASE.
                if (negative) nextHandle = _raiseJava(
                        4, opPC, arena, classes, objectHeap, heapKinds, heapClasses,
                        arrayLeafTypes, parentLinks, hierarchyState, nextHandle
                    );
                if (arena.pending.active) continue;
                (plan.arrays, plan.elements) = _planMultiArray(
                    plan.counts, arena.ordinaryArrayCount, arena.ordinaryArrayElements
                );
                if (plan.arrays == 0) nextHandle = _raiseJava(
                        7, opPC, arena, classes, objectHeap, heapKinds, heapClasses,
                        arrayLeafTypes, parentLinks, hierarchyState, nextHandle
                    );
                if (arena.pending.active) continue;
                _ensureExceptionRegistry(arena, classes, parentLinks, hierarchyState);
                if (arena.heap.arrayHeap.length == 0) {
                    arena.heap.arrayHeap = new uint64[][](MAX_HANDLES + 1);
                    arena.heap.ranks = new uint8[](MAX_HANDLES + 1);
                }
                arrayHeap = arena.heap.arrayHeap;
                objectHeap = arena.heap.objectHeap;
                arrayLeafTypes = arena.heap.metadata;
                heapKinds = arrayLeafTypes;
                heapClasses = arena.heap.classes;
                arrayRanks = arena.heap.ranks;
                nextHandle = arena.nextHandle;
                uint256 rootHandle = nextHandle + 1;
                nextHandle = _allocateMultiArray(
                    arrayHeap, heapKinds, arrayRanks, arrayLeafTypes,
                    nextHandle, allocatedType, plan.counts
                );
                arena.nextHandle = nextHandle;
                arena.ordinaryArrayCount += plan.arrays;
                arena.ordinaryArrayElements += plan.elements;
                f.sp = base + 1;
                f.stack[base] = _packRef(uint32(rootHandle));
            } else if (op == 0xbe) { // arraylength
                if (f.sp == 0) revert BytecodeError(3, opPC);
                _requireKind(f.stack[f.sp - 1], KIND_REF, opPC);
                uint256 handle = _payload(f.stack[f.sp - 1]);
                if (handle == 0) nextHandle = _raiseJava(
                        6, opPC, arena, classes, objectHeap, heapKinds, heapClasses,
                        arrayLeafTypes, parentLinks, hierarchyState, nextHandle
                    );
                if (arena.pending.active) continue;
                _requireHeapKind(handle, heapKinds, nextHandle, HEAP_ARRAY, opPC);
                f.stack[f.sp - 1] = _packInt(uint32(arrayHeap[handle].length));
            } else if (op == 0xbf) { // athrow
                if (f.sp == 0) revert BytecodeError(3, opPC);
                uint256 thrown = f.stack[f.sp - 1];
                _requireKind(thrown, KIND_REF, opPC);
                uint256 thrownHandle = _payload(thrown);
                --f.sp; // Consume every REF operand, including null, before raising.
                if (thrownHandle == 0) {
                    nextHandle = _raiseJava(
                        6, opPC, arena, classes, objectHeap, heapKinds, heapClasses,
                        arrayLeafTypes, parentLinks, hierarchyState, nextHandle
                    );
                    continue;
                }
                _validatePackedRef(thrown, heapKinds, nextHandle, opPC);
                if (_heapKindAt(arrayLeafTypes[thrownHandle]) != HEAP_OBJECT
                    || !_typeAssignable(
                        classes, heapClasses[thrownHandle], arena.throwableClass, parentLinks
                    )) revert BytecodeError(14, opPC);
                uint256 rethrownKind = _exactKnownKind(
                    arena, heapClasses[thrownHandle]
                );
                arena.pending = PendingException(true, rethrownKind, thrownHandle, opPC);
                continue;
            } else if (op == 0xc0 || op == 0xc1) { // checkcast / instanceof
                uint256 refIndex = _unsigned16(c.data, selection.codeOffset + f.pc);
                f.pc += 2;
                (uint8 targetKind, uint256 targetOffset, uint256 targetLength) =
                    _validateCastTarget(c, refIndex, opPC);
                if (f.sp == 0) revert BytecodeError(3, opPC);
                uint256 value = f.stack[f.sp - 1];
                _requireKind(value, KIND_REF, opPC);
                uint256 handle = _payload(value);
                if (handle == 0) {
                    if (op == 0xc1) f.stack[f.sp - 1] = _packInt(0);
                    continue;
                }
                _validatePackedRef(value, heapKinds, nextHandle, opPC);
                bool assignable;
                if (targetKind == 2) {
                    ArrayType memory wantedArray = _resolveArrayClassType(
                        classes, f.classIndex, c.data, targetOffset, targetLength, opPC,
                        parentLinks, hierarchyState
                    );
                    assignable = _heapKindAt(heapKinds[handle]) == HEAP_ARRAY && _arrayTypeAssignable(
                        classes, arrayRanks[handle], arrayLeafTypes[handle],
                        wantedArray.rank, wantedArray.leafType, parentLinks
                    );
                } else {
                    if (targetKind != 1) revert TypeError(2, opPC);
                    (bool foundTarget, uint256 targetClass) = _findClass(
                        classes, c.data, targetOffset, targetLength
                    );
                    if (!foundTarget) _missingClass(0x1001, opPC, c.data, targetOffset, targetLength);
                    ClassInfo memory castClass = classes[targetClass];
                    if (targetClass != f.classIndex && !_classAccessible(c, castClass)) {
                        revert TypeError(2, opPC);
                    }
                    _validateHierarchy(classes, targetClass, parentLinks, hierarchyState);
                    if (_heapKindAt(heapKinds[handle]) == HEAP_ARRAY) {
                        assignable = _arrayImplementsClass(classes, targetClass);
                    } else if (_heapKindAt(heapKinds[handle]) == HEAP_OBJECT) {
                        assignable = _typeAssignable(
                            classes, heapClasses[handle], targetClass, parentLinks
                        );
                    }
                }
                if (op == 0xc1) {
                    f.stack[f.sp - 1] = _packInt(assignable ? 1 : 0);
                } else if (!assignable) {
                    nextHandle = _raiseJava(
                        8, opPC, arena, classes, objectHeap, heapKinds, heapClasses,
                        arrayLeafTypes, parentLinks, hierarchyState, nextHandle
                    );
                if (arena.pending.active) continue;
                }
            } else if (op == 0xc6 || op == 0xc7) { // ifnull / ifnonnull
                if (f.sp == 0) revert BytecodeError(3, opPC);
                _requireKind(f.stack[f.sp - 1], KIND_REF, opPC);
                _validatePackedRef(f.stack[f.sp - 1], heapKinds, nextHandle, opPC);
                bool isNull = _payload(f.stack[f.sp - 1]) == 0;
                --f.sp;
                f.pc = ((op == 0xc6) == isNull)
                    ? _decodedTarget(c.data, selection.codeOffset, opPC) : f.pc + 2;
            } else if (op == 0x76 || op == 0x77) { // fneg / dneg: sign flip only
                if (f.sp == 0) revert BytecodeError(3, opPC);
                uint256 wanted = op == 0x76 ? KIND_FLOAT : KIND_DOUBLE;
                _requireKind(f.stack[f.sp - 1], wanted, opPC);
                uint64 sign = op == 0x76 ? uint64(0x80000000) : uint64(0x8000000000000000);
                uint64 bits = uint64(_payload(f.stack[f.sp - 1])) ^ sign;
                f.stack[f.sp - 1] = op == 0x76 ? _packFloat(uint32(bits)) : _packDouble(bits);
            } else if (op == 0x86 || op == 0x87) { // i2f / i2d
                if (f.sp == 0) revert BytecodeError(3, opPC);
                _requireKind(f.stack[f.sp - 1], KIND_INT, opPC);
                uint32 raw = uint32(_payload(f.stack[f.sp - 1]));
                f.stack[f.sp - 1] = op == 0x86
                    ? _packFloat(uint32(_signedIntegerToIEEE(uint64(raw), 32, 24, 127, 23)))
                    : _packDouble(_signedIntegerToIEEE(uint64(raw), 32, 53, 1023, 52));
                if (op == 0x87 && _stackWords(f.stack, f.sp) > f.stack.length) {
                    revert BytecodeError(9, opPC);
                }
            } else if (op == 0x89 || op == 0x8a) { // l2f / l2d
                if (f.sp == 0) revert BytecodeError(3, opPC);
                _requireKind(f.stack[f.sp - 1], KIND_LONG, opPC);
                uint64 raw = uint64(_payload(f.stack[f.sp - 1]));
                f.stack[f.sp - 1] = op == 0x89
                    ? _packFloat(uint32(_signedIntegerToIEEE(raw, 64, 24, 127, 23)))
                    : _packDouble(_signedIntegerToIEEE(raw, 64, 53, 1023, 52));
            } else if (op == 0x8b || op == 0x8c) { // f2i / f2l
                if (f.sp == 0) revert BytecodeError(3, opPC);
                _requireKind(f.stack[f.sp - 1], KIND_FLOAT, opPC);
                uint64 converted = _ieeeToSignedInteger(
                    uint64(uint32(_payload(f.stack[f.sp - 1]))), 8, 23, op == 0x8b ? 32 : 64
                );
                f.stack[f.sp - 1] = op == 0x8b
                    ? _packInt(uint32(converted)) : _packLong(converted);
                if (op == 0x8c && _stackWords(f.stack, f.sp) > f.stack.length) {
                    revert BytecodeError(9, opPC);
                }
            } else if (op == 0x8d) { // f2d
                if (f.sp == 0) revert BytecodeError(3, opPC);
                _requireKind(f.stack[f.sp - 1], KIND_FLOAT, opPC);
                f.stack[f.sp - 1] = _packDouble(_floatToDoubleBits(
                    uint32(_payload(f.stack[f.sp - 1]))
                ));
                if (_stackWords(f.stack, f.sp) > f.stack.length) revert BytecodeError(9, opPC);
            } else if (op == 0x8e || op == 0x8f) { // d2i / d2l
                if (f.sp == 0) revert BytecodeError(3, opPC);
                _requireKind(f.stack[f.sp - 1], KIND_DOUBLE, opPC);
                uint64 converted = _ieeeToSignedInteger(
                    uint64(_payload(f.stack[f.sp - 1])), 11, 52, op == 0x8e ? 32 : 64
                );
                f.stack[f.sp - 1] = op == 0x8e
                    ? _packInt(uint32(converted)) : _packLong(converted);
            } else if (op == 0x90) { // d2f
                if (f.sp == 0) revert BytecodeError(3, opPC);
                _requireKind(f.stack[f.sp - 1], KIND_DOUBLE, opPC);
                f.stack[f.sp - 1] = _packFloat(_doubleToFloatBits(
                    uint64(_payload(f.stack[f.sp - 1]))
                ));
            } else if (op >= 0x95 && op <= 0x98) { // fcmp*/dcmp*
                if (f.sp < 2) revert BytecodeError(3, opPC);
                bool doubles = op >= 0x97;
                uint256 wanted = doubles ? KIND_DOUBLE : KIND_FLOAT;
                _requireKind(f.stack[f.sp - 2], wanted, opPC);
                _requireKind(f.stack[f.sp - 1], wanted, opPC);
                int8 compared = _compareIEEE(
                    uint64(_payload(f.stack[f.sp - 2])),
                    uint64(_payload(f.stack[f.sp - 1])), doubles ? 11 : 8,
                    doubles ? 52 : 23, op == 0x95 || op == 0x97
                );
                f.stack[f.sp - 2] = _packInt(uint32(int32(compared)));
                --f.sp;
            } else if (op >= 0x0b && op <= 0x0d) { // fconst_0..2
                uint32 value = op == 0x0b ? 0 : (op == 0x0c ? 0x3f800000 : 0x40000000);
                f.sp = _push(f.stack, f.sp, _packFloat(value), opPC);
            } else if (op == 0x0e || op == 0x0f) { // dconst_0, dconst_1
                f.sp = _push(f.stack, f.sp,
                    _packDouble(op == 0x0e ? uint64(0) : uint64(0x3ff0000000000000)), opPC);
            } else if (op >= 0x22 && op <= 0x25) { // fload_0..3
                f.sp = _loadKind(
                    f.stack, f.sp, f.locals, f.initialized, op - 0x22, KIND_FLOAT, opPC
                );
            } else if (op >= 0x26 && op <= 0x29) { // dload_0..3
                f.sp = _loadDouble(
                    f.stack, f.sp, f.locals, f.initialized, op - 0x26, opPC
                );
            } else if (op >= 0x43 && op <= 0x46) { // fstore_0..3
                f.sp = _storeKind(
                    f.stack, f.sp, f.locals, f.initialized, op - 0x43, KIND_FLOAT, opPC
                );
            } else if (op >= 0x47 && op <= 0x4a) { // dstore_0..3
                f.sp = _storeDouble(
                    f.stack, f.sp, f.locals, f.initialized, op - 0x47, opPC
                );
            } else {
                revert BytecodeError(6, opPC);
            }
        }
        state.depth = depth;
        state.nextHandle = nextHandle;
        arena.nextHandle = nextHandle;
        state.arena = arena;
        if (state.lifecycle == 3) {
            // Retain the exact propagated pending exception but no active Java frames.
            state.frames = new Frame[](MAX_FRAMES);
            state.depth = 0;
        } else if (state.lifecycle == 2) {
            state.frames = new Frame[](MAX_FRAMES);
            state.depth = 0;
            state.arena.pending = PendingException(false, 0, 0, 0);
        }
    }

    function _newFrame(uint256 classIndex, uint256 method, Selected memory s, uint256 callPC)
        private
        pure
        returns (Frame memory f)
    {
        f.classIndex = classIndex;
        f.methodIndex = method;
        f.callPC = callPC;
        f.stack = new uint256[](s.maxStack);
        f.locals = new uint256[](s.maxLocals);
        f.initialized = new bool[](s.maxLocals);
        f.entered = true;
    }

    function _loadInitializer(ClassInfo memory c, uint256 method, uint256 classIndex)
        private
        pure
        returns (Selected memory s)
    {
        s.declaringClass = classIndex;
        s.methodIndex = method;
        if (c.invalidInitializer) revert InitError(1, classIndex);
        uint256 meta = c.methods[method];
        uint16 access = uint16(meta);
        if (
            (access & 0x0008) == 0 || (access & (0x0020 | 0x0100 | 0x0400)) != 0
                || _methodCodeCount(meta) != 1
        ) revert InitError(1, classIndex);
        uint256 descriptorIndex = (meta >> 32) & 0xffff;
        if (descriptorIndex == 0 || descriptorIndex >= c.cp.length || uint8(c.cp[descriptorIndex]) != 1) {
            revert InitError(1, classIndex);
        }
        (s.descriptorOffset, s.descriptorLength) = _utf(c.cp[descriptorIndex]);
        if (!_descriptor(c.data, s.descriptorOffset, s.descriptorLength, s)
            || s.argumentKinds.length != 0 || s.returnKind != 2) revert InitError(1, classIndex);
        s.argumentCount = 0;
        uint256 start = (meta >> 48) & 0xffffffffffffffff;
        uint256 length = (meta >> 112) & 0xffffffff;
        if (!_readCallCode(c, start, length, s)) revert InitError(1, classIndex);
        if (s.maxStack > MAX_STACK || s.maxLocals > MAX_LOCALS) revert InitError(1, classIndex);
        s.loaded = true;
    }

    function _initializeClass(
        ClassInfo[] memory classes, uint256[][] memory staticValues,
        uint8[] memory initializationState, Frame[] memory frames, uint256 depth,
        uint256 classIndex, uint256[] memory parentLinks, uint8[] memory hierarchyState,
        ExceptionArena memory arena, uint256 requestPC, uint256[][] memory objectHeap,
        uint256[] memory heapKinds, uint256[] memory heapClasses,
        uint256[] memory exceptionKinds, uint256 ignoredNextHandle
    ) private pure returns (uint256) {
        ignoredNextHandle; // nextHandle is carried in arena across initializer scheduling.
        _validateHierarchy(classes, classIndex, parentLinks, hierarchyState);
        uint256 current = classIndex;
        while (true) {
            uint8 state = initializationState[current];
            if (state == 1 || state == 2) return depth;
            if (state == 3) {
                arena.nextHandle = _raiseJava(
                    12, requestPC, arena, classes, objectHeap, heapKinds, heapClasses,
                    exceptionKinds, parentLinks, hierarchyState, arena.nextHandle
                );
                return depth;
            }
            ClassInfo memory c = classes[current];
            uint256 link = parentLinks[current];
            bool parentReady = _isInterface(c) || link == type(uint256).max
                || (link != 0 && initializationState[link - 1] == 2);
            (bool hasDefaultPrerequisite,) = _isInterface(c)
                ? (false, uint256(0))
                : _nextDefaultInterface(classes, current, initializationState);
            bool needsFrame = c.initializerPlusOne != 0 || !parentReady
                || hasDefaultPrerequisite;
            // Capacity is checked before preparation or state 1 is installed.
            if (needsFrame && depth == MAX_FRAMES) {
                arena.nextHandle = _raiseJava(
                    2, requestPC, arena, classes, objectHeap, heapKinds, heapClasses,
                    exceptionKinds, parentLinks, hierarchyState, arena.nextHandle
                );
                return depth;
            }
            initializationState[current] = 1;
            for (uint256 i = 0; i < c.fields.length; ++i) {
                if ((c.fields[i].accessFlags & 0x0008) != 0 && c.fields[i].hasConstant) {
                    uint8 constantKind = _fieldKind(c, c.fields[i]);
                    if (constantKind == KIND_REF) {
                        (uint256 stringRef, bool oom) = _internStringConstant(
                            arena, classes, current, c.fields[i].constantValue,
                            parentLinks, hierarchyState
                        );
                        if (oom) {
                            initializationState[current] = 3;
                            arena.nextHandle = _raiseJava(
                                7, requestPC, arena, classes, objectHeap, heapKinds,
                                heapClasses, exceptionKinds, parentLinks, hierarchyState,
                                arena.nextHandle
                            );
                            return depth;
                        }
                        staticValues[current][i] = _packRef(uint32(stringRef));
                    } else {
                        staticValues[current][i] = constantKind == KIND_LONG
                            ? _packLong(uint64(c.fields[i].constantValue))
                            : (constantKind == KIND_DOUBLE
                                ? _packDouble(uint64(c.fields[i].constantValue))
                                : (constantKind == KIND_FLOAT
                                    ? _packFloat(uint32(c.fields[i].constantValue))
                                    : _packInt(uint32(c.fields[i].constantValue))));
                    }
                }
            }
            if (!needsFrame) {
                initializationState[current] = 2;
                return depth;
            }
            Frame memory continuation;
            continuation.classIndex = current;
            continuation.callPC = requestPC;
            continuation.isInitContinuation = true;
            frames[depth] = continuation;
            ++depth;
            if (_isInterface(c) || link == type(uint256).max || link == 0) return depth;
            current = link - 1;
        }
    }

    function _declaresDefault(ClassInfo memory c) private pure returns (bool) {
        for (uint256 i = 0; i < c.methods.length; ++i) {
            uint256 meta = c.methods[i];
            uint16 access = uint16(meta);
            if ((access & (0x0008 | 0x0400)) == 0 && _methodCodeCount(meta) == 1) return true;
        }
        return false;
    }

    function _nextDefaultInterface(
        ClassInfo[] memory classes, uint256 classIndex, uint8[] memory initializationState
    ) private pure returns (bool found, uint256 target) {
        bool[] memory seen = new bool[](classes.length);
        uint256[] memory nodes = new uint256[](classes.length);
        uint256[] memory edges = new uint256[](classes.length);
        ClassInfo memory c = classes[classIndex];
        for (uint256 root = 0; root < c.interfaces.length; ++root) {
            uint256 direct = _resolveInterfaceEdge(classes, classIndex, root);
            if (seen[direct]) continue;
            uint256 size = 1;
            nodes[0] = direct;
            seen[direct] = true;
            while (size != 0) {
                uint256 at = size - 1;
                uint256 node = nodes[at];
                if (edges[at] < classes[node].interfaces.length) {
                    uint256 edge = edges[at]++;
                    uint256 parent = _resolveInterfaceEdge(classes, node, edge);
                    if (!seen[parent]) {
                        seen[parent] = true;
                        nodes[size] = parent;
                        edges[size] = 0;
                        ++size;
                    }
                    continue;
                }
                --size; // postorder: parents before the declaring descendant
                // An already-erroneous default prerequisite is still required:
                // scheduling it raises NCDFE and fails the new dependent class.
                // Only initialized or same-execution reentrant interfaces skip.
                if ((initializationState[node] == 0 || initializationState[node] == 3)
                    && _declaresDefault(classes[node])) {
                    return (true, node);
                }
            }
        }
    }

    function _validateHierarchy(
        ClassInfo[] memory classes,
        uint256 classIndex,
        uint256[] memory parentLinks,
        uint8[] memory hierarchyState
    ) private pure {
        if (_isInterface(classes[classIndex])) {
            _validateInterfaceClosure(classes, classIndex, parentLinks);
            return;
        }
        if (hierarchyState[classIndex] != 2) {
            bool[] memory seen = new bool[](classes.length);
            uint256 current = classIndex;
            while (hierarchyState[current] != 2) {
                if (seen[current]) revert HierarchyError(2, current);
                seen[current] = true;
                ClassInfo memory child = classes[current];
                _requireSupportedClass(child, current);
                bool isObject = _isObjectClass(child);
                if (isObject) {
                    if (child.hasSuperclass) revert HierarchyError(4, current);
                    parentLinks[current] = type(uint256).max;
                    break;
                }
                if (!child.hasSuperclass) revert HierarchyError(4, current);

                (bool found, uint256 parent) = _findClass(
                    classes, child.data, child.superNameOffset, child.superNameLength
                );
                if (!found) revert HierarchyError(1, current);
                ClassInfo memory parentClass = classes[parent];
                if (_isInterface(parentClass)) revert HierarchyError(4, current);
                if ((parentClass.accessFlags & 0x0010) != 0) revert HierarchyError(3, current);
                if ((parentClass.accessFlags & 0x0001) == 0 && !_samePackage(child, parentClass)) {
                    revert HierarchyError(5, current);
                }
                parentLinks[current] = parent + 1;
                current = parent;
            }
            for (uint256 i = 0; i < classes.length; ++i) {
                if (seen[i]) hierarchyState[i] = 2;
            }
        }
        _validateInterfaceClosure(classes, classIndex, parentLinks);
    }

    function _validateInterfaceClosure(
        ClassInfo[] memory classes, uint256 start, uint256[] memory parentLinks
    ) private pure {
        bool[] memory reachable = new bool[](classes.length);
        uint256[] memory queue = new uint256[](classes.length);
        uint256 head;
        uint256 tail;
        if (_isInterface(classes[start])) {
            queue[tail++] = start;
            reachable[start] = true;
        } else {
            uint256 current = start;
            while (true) {
                ClassInfo memory owner = classes[current];
                for (uint256 i = 0; i < owner.interfaces.length; ++i) {
                    uint256 target = _resolveInterfaceEdge(classes, current, i);
                    for (uint256 j = 0; j < i; ++j) {
                        if (_resolveInterfaceEdge(classes, current, j) == target) {
                            revert InterfaceError(1, current);
                        }
                    }
                    if (!reachable[target]) {
                        reachable[target] = true;
                        queue[tail++] = target;
                    }
                }
                uint256 link = parentLinks[current];
                if (link == 0 || link == type(uint256).max) break;
                current = link - 1;
            }
        }
        while (head < tail) {
            uint256 ownerIndex = queue[head++];
            _validateInterfaceHeaderAndMethods(classes[ownerIndex], ownerIndex);
            ClassInfo memory owner = classes[ownerIndex];
            for (uint256 i = 0; i < owner.interfaces.length; ++i) {
                uint256 target = _resolveInterfaceEdge(classes, ownerIndex, i);
                for (uint256 j = 0; j < i; ++j) {
                    if (_resolveInterfaceEdge(classes, ownerIndex, j) == target) {
                        revert InterfaceError(1, ownerIndex);
                    }
                }
                if (!reachable[target]) {
                    reachable[target] = true;
                    queue[tail++] = target;
                }
            }
        }
        if (tail == 0) return;
        uint256[] memory indegree = new uint256[](classes.length);
        for (uint256 i = 0; i < classes.length; ++i) {
            if (!reachable[i]) continue;
            for (uint256 j = 0; j < classes[i].interfaces.length; ++j) {
                uint256 target = _resolveInterfaceEdge(classes, i, j);
                ++indegree[target];
            }
        }
        head = 0;
        uint256 processed;
        for (uint256 i = 0; i < classes.length; ++i) {
            if (reachable[i] && indegree[i] == 0) queue[head++] = i;
        }
        uint256 at;
        while (at < head) {
            uint256 owner = queue[at++];
            ++processed;
            for (uint256 j = 0; j < classes[owner].interfaces.length; ++j) {
                uint256 target = _resolveInterfaceEdge(classes, owner, j);
                if (--indegree[target] == 0) queue[head++] = target;
            }
        }
        if (processed != tail) {
            for (uint256 i = 0; i < classes.length; ++i) {
                if (reachable[i] && indegree[i] != 0) revert InterfaceError(2, i);
            }
        }
    }

    function _validateInterfaceHeaderAndMethods(ClassInfo memory c, uint256 classIndex)
        private pure
    {
        if (!_isInterface(c) || (c.accessFlags & 0x0400) == 0
            || (c.accessFlags & 0xe010) != 0 || !c.hasSuperclass
            || !_equalsLiteral(c.data, c.superNameOffset, c.superNameLength, bytes("java/lang/Object"))) {
            revert InterfaceError(1, classIndex);
        }
        for (uint256 i = 0; i < c.fields.length; ++i) {
            if ((c.fields[i].accessFlags & 0x0019) != 0x0019) {
                revert InterfaceError(1, classIndex);
            }
        }
        for (uint256 i = 0; i < c.methods.length; ++i) {
            uint256 meta = c.methods[i];
            uint16 access = uint16(meta);
            if ((access & 0x0008) != 0) continue; // static metadata is deferred to M4f-c
            uint256 codeCount = _methodCodeCount(meta);
            bool isAbstract = (access & 0x0400) != 0;
            // Java 8 public defaults, including ACC_BRIDGE|ACC_SYNTHETIC
            // compiler bridges, are admitted. Private/native/synchronized forms
            // and abstract/Code inconsistencies remain unsupported shapes.
            if ((access & 0x0001) == 0
                || (access & ~(uint16(0x0001 | 0x0040 | 0x0080 | 0x0400 | 0x0800 | 0x1000))) != 0
                || (isAbstract ? codeCount != 0 : codeCount != 1)) {
                revert InterfaceError(4, classIndex);
            }
            if (!isAbstract) {
                uint256 descriptorIndex = (meta >> 32) & 0xffff;
                if (descriptorIndex == 0 || descriptorIndex >= c.cp.length
                    || uint8(c.cp[descriptorIndex]) != 1) revert InterfaceError(4, classIndex);
                (uint256 descriptorOffset, uint256 descriptorLength) = _utf(c.cp[descriptorIndex]);
                Selected memory signature;
                if (!_descriptor(c.data, descriptorOffset, descriptorLength, signature)) {
                    revert InterfaceError(4, classIndex);
                }
            }
        }
    }

    function _resolveInterfaceEdge(
        ClassInfo[] memory classes, uint256 ownerIndex, uint256 edge
    ) private pure returns (uint256 target) {
        ClassInfo memory owner = classes[ownerIndex];
        uint256 cpIndex = owner.interfaces[edge];
        if (cpIndex == 0 || cpIndex >= owner.cp.length || uint8(owner.cp[cpIndex]) != 7) {
            revert InterfaceError(1, ownerIndex);
        }
        uint256 nameIndex = (owner.cp[cpIndex] >> 8) & 0xffff;
        if (nameIndex == 0 || nameIndex >= owner.cp.length || uint8(owner.cp[nameIndex]) != 1) {
            revert InterfaceError(1, ownerIndex);
        }
        (uint256 off, uint256 n) = _utf(owner.cp[nameIndex]);
        if (!_validInternalName(owner.data, off, n)) revert InterfaceError(1, ownerIndex);
        (bool found, uint256 resolved) = _findClass(classes, owner.data, off, n);
        if (!found) _missingClass(0x1002, ownerIndex, owner.data, off, n);
        if (!_isInterface(classes[resolved])) revert InterfaceError(1, ownerIndex);
        if (resolved != ownerIndex && !_classAccessible(owner, classes[resolved])) {
            revert InterfaceError(3, ownerIndex);
        }
        return resolved;
    }

    function _validateStaticCalleeMetadata(
        ClassInfo memory c, uint256 method, uint256 callPC
    ) private pure {
        uint256 meta = c.methods[method];
        uint16 access = uint16(meta);
        if ((access & 0x0008) == 0 || (access & (0x0020 | 0x0100 | 0x0400)) != 0
            || _methodCodeCount(meta) != 1) revert CallError(4, callPC);
        // Java 8 interface static methods are public. Keep the accepted
        // compiler metadata flags aligned with the existing descriptor/code
        // subset, while rejecting private and malformed interface members at
        // the call site rather than treating them as inherited defaults.
        if (_isInterface(c)
            && ((access & 0x0001) == 0
                || (access & ~(uint16(0x0001 | 0x0008 | 0x0040 | 0x0080 | 0x0800 | 0x1000))) != 0)) {
            revert CallError(4, callPC);
        }
    }

    function _validateSpecialCalleeMetadata(
        ClassInfo memory c, uint256 method, uint256 callPC, bool isConstructor
    ) private pure {
        uint256 meta = c.methods[method];
        uint16 access = uint16(meta);
        if ((access & 0x0008) != 0 || (access & (0x0020 | 0x0100 | 0x0400)) != 0
            || _methodCodeCount(meta) != 1) revert CallError(4, callPC);
        if (isConstructor) {
            (uint256 off, uint256 n) = _utf(c.cp[(meta >> 32) & 0xffff]);
            Selected memory signature;
            if (!_descriptor(c.data, off, n, signature) || signature.returnKind != 2) {
                revert CallError(4, callPC);
            }
        }
    }

    function _requireStringObjectProfile(
        ClassInfo[] memory classes, uint256 stringClass, uint256 pc,
        uint256[] memory parentLinks, uint8[] memory hierarchyState, bool stateValidation
    ) private pure {
        _validateHierarchy(classes, stringClass, parentLinks, hierarchyState);
        uint256 link = parentLinks[stringClass];
        if (link == 0 || link == type(uint256).max) revert CallError(3, pc);
        uint256 objectClass = link - 1;
        if (!_isObjectClass(classes[objectClass])) revert CallError(3, pc);
        uint256 foundPlusOne;
        for (uint256 i; i < classes[objectClass].methods.length; ++i) {
            uint256 meta = classes[objectClass].methods[i];
            (uint256 no, uint256 nn) = _utf(classes[objectClass].cp[(meta >> 16) & 0xffff]);
            (uint256 doff, uint256 dn) = _utf(classes[objectClass].cp[(meta >> 32) & 0xffff]);
            if (!_equalsLiteral(classes[objectClass].data, no, nn, bytes("<init>"))
                || !_equalsLiteral(classes[objectClass].data, doff, dn, bytes("()V"))) continue;
            if (foundPlusOne != 0) revert CallError(3, pc);
            foundPlusOne = i + 1;
        }
        if (foundPlusOne == 0) revert CallError(3, pc);
        uint256 method = foundPlusOne - 1;
        if (!_canAccessMember(
            classes, stringClass, objectClass,
            uint16(classes[objectClass].methods[method]), parentLinks, hierarchyState
        )) revert CallError(4, pc);
        _validateSpecialCalleeMetadata(classes[objectClass], method, pc, true);
        Selected memory selected = _loadSpecialCallee(
            classes[objectClass], method, pc, true, objectClass
        );
        bool canonical = selected.maxStack == 0 && selected.maxLocals == 1
            && selected.codeLength == 1 && selected.handlerStarts.length == 0
            && uint8(classes[objectClass].data[selected.codeOffset]) == 0xb1;
        if (!canonical) {
            if (stateValidation) revert LC0StateError(7, 0);
            revert StringProfileError(4, pc);
        }
    }

    function _supportedStringSource(
        ClassInfo memory stringClassInfo, Selected memory target, uint256 argument,
        uint256[] memory heapKinds, uint256[] memory heapClasses,
        uint8[] memory arrayRanks, uint256[] memory arrayLeafTypes,
        uint256 nextHandle, uint256 stringClass
    ) private pure returns (bool) {
        if (_valueKind(argument) != KIND_REF) return false;
        uint256 handle = _payload(argument);
        if (handle == 0) return true;
        if (handle > nextHandle) return false;
        bool chars = _equalsLiteral(
            stringClassInfo.data, target.argumentTypeOffsets[0],
            target.argumentTypeLengths[0], bytes("[C")
        );
        if (chars) return _heapKindAt(heapKinds[handle]) == HEAP_ARRAY
            && arrayRanks[handle] == 1 && arrayLeafTypes[handle] == PRIMITIVE_CHAR;
        return _equalsLiteral(
                stringClassInfo.data, target.argumentTypeOffsets[0],
                target.argumentTypeLengths[0], bytes("Ljava/lang/String;")
            ) && _heapKindAt(heapKinds[handle]) == HEAP_OBJECT
            && heapClasses[handle] == stringClass;
    }

    function _loadSpecialCallee(
        ClassInfo memory c, uint256 method, uint256 callPC, bool isConstructor,
        uint256 classIndex
    ) private pure returns (Selected memory s) {
        s.declaringClass = classIndex;
        s.methodIndex = method;
        _validateSpecialCalleeMetadata(c, method, callPC, isConstructor);
        uint256 meta = c.methods[method];
        (s.descriptorOffset, s.descriptorLength) = _utf(c.cp[(meta >> 32) & 0xffff]);
        if (!_descriptor(c.data, s.descriptorOffset, s.descriptorLength, s)) {
            revert CallError(4, callPC);
        }
        if (isConstructor && s.returnKind != 2) revert CallError(4, callPC);
        s.argumentCount = s.argumentKinds.length;
        uint256 start = (meta >> 48) & 0xffffffffffffffff;
        uint256 length = (meta >> 112) & 0xffffffff;
        if (!_readCallCode(c, start, length, s)) revert CallError(4, callPC);
        if (s.maxStack > MAX_STACK || s.maxLocals > MAX_LOCALS
            || s.maxLocals < s.argumentWords + 1) revert CallError(4, callPC);
        s.loaded = true;
    }

    function _lookupExactMethod(
        ClassInfo[] memory classes, uint256 targetClass, bytes memory nameData,
        uint256 nameOffset, uint256 nameLength, uint256 descriptorOffset,
        uint256 descriptorLength, uint256 pc
    ) private pure returns (bool found, uint256 method) {
        ClassInfo memory target = classes[targetClass];
        uint256 foundPlusOne;
        for (uint256 i = 0; i < target.methods.length; ++i) {
            uint256 candidate = target.methods[i];
            (uint256 candidateNameOffset, uint256 candidateNameLength) =
                _utf(target.cp[(candidate >> 16) & 0xffff]);
            if (!_equalsCross(target.data, candidateNameOffset, candidateNameLength,
                nameData, nameOffset, nameLength)) continue;
            (uint256 candidateDescriptorOffset, uint256 candidateDescriptorLength) =
                _utf(target.cp[(candidate >> 32) & 0xffff]);
            if (!_equalsCross(target.data, candidateDescriptorOffset, candidateDescriptorLength,
                nameData, descriptorOffset, descriptorLength)) continue;
            if (foundPlusOne != 0) revert CallError(3, pc);
            foundPlusOne = i + 1;
        }
        if (foundPlusOne != 0) return (true, foundPlusOne - 1);
    }

    function _findExactMethod(
        ClassInfo[] memory classes, uint256 targetClass, bytes memory nameData,
        uint256 nameOffset, uint256 nameLength, uint256 descriptorOffset,
        uint256 descriptorLength, uint256 pc
    ) private pure returns (uint256 method) {
        (bool found, uint256 result) = _lookupExactMethod(
            classes, targetClass, nameData, nameOffset, nameLength,
            descriptorOffset, descriptorLength, pc
        );
        if (!found) revert CallError(3, pc);
        return result;
    }

    function _findInterfaceMethod(
        ClassInfo[] memory classes, uint256 start, bool startIsInterface,
        bytes memory nameData, uint256 nameOffset, uint256 nameLength,
        uint256 descriptorOffset, uint256 descriptorLength,
        uint256[] memory parentLinks, uint256 pc
    ) private pure returns (bool found, uint256 owner, uint256 method) {
        bool[] memory reachable = new bool[](classes.length);
        uint256[] memory queue = new uint256[](classes.length);
        uint256 head;
        uint256 tail;
        if (startIsInterface) {
            for (uint256 i = 0; i < classes[start].interfaces.length; ++i) {
                uint256 direct = _resolveInterfaceEdge(classes, start, i);
                if (!reachable[direct]) { reachable[direct] = true; queue[tail++] = direct; }
            }
        } else {
            uint256 current = start;
            while (true) {
                for (uint256 i = 0; i < classes[current].interfaces.length; ++i) {
                    uint256 direct = _resolveInterfaceEdge(classes, current, i);
                    if (!reachable[direct]) { reachable[direct] = true; queue[tail++] = direct; }
                }
                uint256 link = parentLinks[current];
                if (link == 0 || link == type(uint256).max) break;
                current = link - 1;
            }
        }
        while (head < tail) {
            uint256 iface = queue[head++];
            for (uint256 i = 0; i < classes[iface].interfaces.length; ++i) {
                uint256 parent = _resolveInterfaceEdge(classes, iface, i);
                if (!reachable[parent]) { reachable[parent] = true; queue[tail++] = parent; }
            }
        }
        bool[] memory declares = new bool[](classes.length);
        uint256[] memory methods = new uint256[](classes.length);
        for (uint256 i = 0; i < classes.length; ++i) {
            if (!reachable[i]) continue;
            (bool has, uint256 candidate) = _lookupExactMethod(
                classes, i, nameData, nameOffset, nameLength,
                descriptorOffset, descriptorLength, pc
            );
            if (has && (uint16(classes[i].methods[candidate]) & (0x0002 | 0x0008)) == 0) {
                declares[i] = true;
                methods[i] = candidate;
            }
        }
        uint256 concreteCount;
        uint256 concreteOwner;
        uint256 concreteMethod;
        uint256 abstractOwner;
        uint256 abstractMethod;
        bool hasAbstract;
        for (uint256 i = 0; i < classes.length; ++i) {
            if (!declares[i]) continue;
            bool shadowed;
            for (uint256 j = 0; j < classes.length; ++j) {
                // Any matching declaration in a strict subinterface suppresses
                // this one, including an abstract re-declaration.
                if (i != j && declares[j] && _interfaceExtends(classes, j, i)) {
                    shadowed = true;
                    break;
                }
            }
            if (shadowed) continue;
            uint256 meta = classes[i].methods[methods[i]];
            if ((uint16(meta) & 0x0400) == 0 && _methodCodeCount(meta) == 1) {
                ++concreteCount;
                concreteOwner = i;
                concreteMethod = methods[i];
            } else if (!hasAbstract) {
                hasAbstract = true;
                abstractOwner = i;
                abstractMethod = methods[i];
            }
        }
        if (concreteCount > 1) return (false, type(uint256).max, 10);
        if (concreteCount == 1) return (true, concreteOwner, concreteMethod);
        if (hasAbstract) return (true, abstractOwner, abstractMethod);
    }

    function _selectInterfaceImplementation(
        ClassInfo[] memory classes, uint256 dynamicClass, bytes memory nameData,
        uint256 nameOffset, uint256 nameLength, uint256 descriptorOffset,
        uint256 descriptorLength, uint256[] memory parentLinks, uint256 pc
    ) private pure returns (uint256 owner, uint256 method) {
        uint256 current = dynamicClass;
        while (true) {
            (bool found, uint256 candidate) = _lookupExactMethod(
                classes, current, nameData, nameOffset, nameLength,
                descriptorOffset, descriptorLength, pc
            );
            if (found) {
                uint256 meta = classes[current].methods[candidate];
                uint16 access = uint16(meta);
                // A private declaration is never a public implementation; retain
                // the unsupported-access guard rather than executing it as one.
                if ((access & 0x0002) != 0) revert CallError(4, pc);
                uint8 stringBinding = _stringNativeBinding(classes[current], candidate);
                if ((access & 0x0001) == 0 || (access & (0x0008 | 0x0020)) != 0
                    || ((access & 0x0100) != 0 && stringBinding == 0)) {
                    revert CallError(4, pc);
                }
                if ((access & 0x0400) != 0) {
                    if (_methodCodeCount(meta) != 0) revert CallError(4, pc);
                    return (type(uint256).max, 11);
                }
                if (stringBinding != 0) {
                    if (_methodCodeCount(meta) != 0) revert CallError(4, pc);
                } else if (_methodCodeCount(meta) != 1) revert CallError(4, pc);
                    uint256 ancestor = current;
                    while (parentLinks[ancestor] != 0
                        && parentLinks[ancestor] != type(uint256).max) {
                        ancestor = parentLinks[ancestor] - 1;
                        (bool inherited, uint256 inheritedMethod) = _lookupExactMethod(
                            classes, ancestor, nameData, nameOffset, nameLength,
                            descriptorOffset, descriptorLength, pc
                        );
                        if (!inherited) continue;
                        uint16 inheritedAccess = uint16(classes[ancestor].methods[inheritedMethod]);
                        bool overrides = (inheritedAccess & (0x0001 | 0x0004)) != 0
                            || ((inheritedAccess & 0x0002) == 0
                                && _samePackage(classes[current], classes[ancestor]));
                        if (overrides && (inheritedAccess & 0x0010) != 0) {
                            revert CallError(4, pc);
                        }
                    }
                return (current, candidate);
            }
            uint256 link = parentLinks[current];
            if (link == 0 || link == type(uint256).max) break;
            current = link - 1;
        }
        (bool inheritedDefault, uint256 interfaceOwner, uint256 interfaceMethod) =
            _findInterfaceMethod(
                classes, dynamicClass, false, nameData, nameOffset, nameLength,
                descriptorOffset, descriptorLength, parentLinks, pc
            );
        if (interfaceOwner == type(uint256).max) return (interfaceOwner, interfaceMethod);
        if (!inheritedDefault) return (type(uint256).max, 11);
        uint256 selectedMeta = classes[interfaceOwner].methods[interfaceMethod];
        if ((uint16(selectedMeta) & 0x0400) != 0 || _methodCodeCount(selectedMeta) == 0) {
            return (type(uint256).max, 11);
        }
        return (interfaceOwner, interfaceMethod);
    }

    function _loadVirtualSignature(ClassInfo memory c, uint256 method, uint256 callPC)
        private
        pure
        returns (Selected memory s)
    {
        uint256 meta = c.methods[method];
        uint256 descriptorIndex = (meta >> 32) & 0xffff;
        if (descriptorIndex == 0 || descriptorIndex >= c.cp.length
            || uint8(c.cp[descriptorIndex]) != 1) revert CallError(1, callPC);
        (s.descriptorOffset, s.descriptorLength) = _utf(c.cp[descriptorIndex]);
        if (!_descriptor(c.data, s.descriptorOffset, s.descriptorLength, s)) {
            revert CallError(4, callPC);
        }
        s.argumentCount = s.argumentKinds.length;
    }

    function _loadVirtualCallee(
        ClassInfo memory c, uint256 method, uint256 callPC, uint256 classIndex
    ) private pure returns (Selected memory s) {
        uint256 meta = c.methods[method];
        uint16 access = uint16(meta);
        if ((access & (0x0002 | 0x0008 | 0x0020 | 0x0100 | 0x0400)) != 0
            || _methodCodeCount(meta) != 1) revert CallError(4, callPC);
        s = _loadVirtualSignature(c, method, callPC);
        s.declaringClass = classIndex;
        s.methodIndex = method;
        uint256 start = (meta >> 48) & 0xffffffffffffffff;
        uint256 length = (meta >> 112) & 0xffffffff;
        if (!_readCallCode(c, start, length, s)) revert CallError(4, callPC);
        if (s.maxStack > MAX_STACK || s.maxLocals > MAX_LOCALS
            || s.maxLocals < s.argumentWords + 1) revert CallError(4, callPC);
        s.loaded = true;
    }

    function _resolveVirtual(
        ClassInfo[] memory classes, uint256 callerClass, uint256 refIndex, uint256 pc,
        uint256[] memory parentLinks, uint8[] memory hierarchyState
    ) private pure returns (VirtualResolution memory out) {
        ClassInfo memory caller = classes[callerClass];
        if (refIndex == 0 || refIndex >= caller.cp.length || uint8(caller.cp[refIndex]) != 10) {
            revert CallError(1, pc);
        }
        uint256 ref = caller.cp[refIndex];
        uint256 ownerClassIndex = (ref >> 8) & 0xffff;
        uint256 natIndex = (ref >> 24) & 0xffff;
        if (ownerClassIndex == 0 || ownerClassIndex >= caller.cp.length
            || uint8(caller.cp[ownerClassIndex]) != 7 || natIndex == 0
            || natIndex >= caller.cp.length || uint8(caller.cp[natIndex]) != 12) {
            revert CallError(1, pc);
        }
        uint256 ownerNameIndex = (caller.cp[ownerClassIndex] >> 8) & 0xffff;
        if (ownerNameIndex == 0 || ownerNameIndex >= caller.cp.length
            || uint8(caller.cp[ownerNameIndex]) != 1) revert CallError(1, pc);
        (uint256 ownerOff, uint256 ownerLen) = _utf(caller.cp[ownerNameIndex]);
        if (!_validInternalName(caller.data, ownerOff, ownerLen)) revert CallError(1, pc);
        (bool foundOwner, uint256 symbolic) = _findClass(
            classes, caller.data, ownerOff, ownerLen
        );
        if (!foundOwner) _missingClass(0x1003, pc, caller.data, ownerOff, ownerLen);
        _validateHierarchy(classes, symbolic, parentLinks, hierarchyState);
        if (_isInterface(classes[symbolic])) revert CallError(4, pc);
        if (symbolic != callerClass && !_classAccessible(caller, classes[symbolic])) {
            revert CallError(4, pc);
        }

        uint256 nat = caller.cp[natIndex];
        uint256 nameIndex = (nat >> 8) & 0xffff;
        uint256 descriptorIndex = (nat >> 24) & 0xffff;
        if (nameIndex == 0 || nameIndex >= caller.cp.length || uint8(caller.cp[nameIndex]) != 1
            || descriptorIndex == 0 || descriptorIndex >= caller.cp.length
            || uint8(caller.cp[descriptorIndex]) != 1) revert CallError(1, pc);
        (out.nameOffset, out.nameLength) = _utf(caller.cp[nameIndex]);
        (out.descriptorOffset, out.descriptorLength) = _utf(caller.cp[descriptorIndex]);
        bool isCtor = _equalsLiteral(
            caller.data, out.nameOffset, out.nameLength, bytes("<init>")
        );
        bool isInitializer = _equalsLiteral(
            caller.data, out.nameOffset, out.nameLength, bytes("<clinit>")
        );
        if (isCtor || isInitializer) revert CallError(4, pc);
        if (!_validOrdinaryMethodName(caller.data, out.nameOffset, out.nameLength)) {
            revert CallError(1, pc);
        }

        out.symbolic = symbolic;
        out.referenceClass = callerClass;
        out.owner = symbolic;
        bool resolvedDeclaration;
        while (true) {
            (bool found, uint256 method) = _lookupExactMethod(
                classes, out.owner, caller.data, out.nameOffset, out.nameLength,
                out.descriptorOffset, out.descriptorLength, pc
            );
            if (found) { out.method = method; resolvedDeclaration = true; break; }
            uint256 link = parentLinks[out.owner];
            if (link == 0 || link == type(uint256).max) break;
            out.owner = link - 1;
        }
        if (!resolvedDeclaration) {
            if (_isStringProfileSymbolic(classes[symbolic])) {
                _rejectStringProfileCall(caller.data, out.descriptorOffset, out.descriptorLength, pc);
            }
            (bool foundInterface, uint256 interfaceOwner, uint256 interfaceMethod) =
                _findInterfaceMethod(
                    classes, symbolic, false, caller.data, out.nameOffset, out.nameLength,
                    out.descriptorOffset, out.descriptorLength, parentLinks, pc
                );
            if (interfaceOwner == type(uint256).max) {
                out.javaFault = interfaceMethod;
                return out;
            }
            if (!foundInterface) revert CallError(3, pc);
            out.owner = interfaceOwner;
            out.method = interfaceMethod;
        }
        uint16 access = uint16(classes[out.owner].methods[out.method]);
        if ((access & (0x0002 | 0x0008)) != 0) revert CallError(4, pc);
        if (!_canAccessMember(
            classes, callerClass, out.owner, access, parentLinks, hierarchyState
        )) revert CallError(4, pc);
    }

    function _resolveInterfaceCall(
        ClassInfo[] memory classes, uint256 callerClass, uint256 refIndex, uint256 pc,
        uint256[] memory parentLinks, uint8[] memory hierarchyState
    ) private pure returns (VirtualResolution memory out) {
        ClassInfo memory caller = classes[callerClass];
        if (refIndex == 0 || refIndex >= caller.cp.length || uint8(caller.cp[refIndex]) != 11) {
            revert CallError(1, pc);
        }
        uint256 ref = caller.cp[refIndex];
        uint256 ownerClassIndex = (ref >> 8) & 0xffff;
        uint256 natIndex = (ref >> 24) & 0xffff;
        if (ownerClassIndex == 0 || ownerClassIndex >= caller.cp.length
            || uint8(caller.cp[ownerClassIndex]) != 7 || natIndex == 0
            || natIndex >= caller.cp.length || uint8(caller.cp[natIndex]) != 12) {
            revert CallError(1, pc);
        }
        uint256 ownerNameIndex = (caller.cp[ownerClassIndex] >> 8) & 0xffff;
        if (ownerNameIndex == 0 || ownerNameIndex >= caller.cp.length
            || uint8(caller.cp[ownerNameIndex]) != 1) revert CallError(1, pc);
        (uint256 ownerOff, uint256 ownerLen) = _utf(caller.cp[ownerNameIndex]);
        if (!_validInternalName(caller.data, ownerOff, ownerLen)) revert CallError(1, pc);
        (bool foundOwner, uint256 symbolic) = _findClass(classes, caller.data, ownerOff, ownerLen);
        if (!foundOwner) _missingClass(0x1004, pc, caller.data, ownerOff, ownerLen);
        if (!_isInterface(classes[symbolic])) revert InterfaceError(1, pc);
        _validateHierarchy(classes, symbolic, parentLinks, hierarchyState);
        if (symbolic != callerClass && !_classAccessible(caller, classes[symbolic])) {
            revert CallError(4, pc);
        }
        uint256 nat = caller.cp[natIndex];
        uint256 nameIndex = (nat >> 8) & 0xffff;
        uint256 descriptorIndex = (nat >> 24) & 0xffff;
        if (nameIndex == 0 || nameIndex >= caller.cp.length || uint8(caller.cp[nameIndex]) != 1
            || descriptorIndex == 0 || descriptorIndex >= caller.cp.length
            || uint8(caller.cp[descriptorIndex]) != 1) revert CallError(1, pc);
        (out.nameOffset, out.nameLength) = _utf(caller.cp[nameIndex]);
        (out.descriptorOffset, out.descriptorLength) = _utf(caller.cp[descriptorIndex]);
        if (_equalsLiteral(caller.data, out.nameOffset, out.nameLength, bytes("<init>"))
            || _equalsLiteral(caller.data, out.nameOffset, out.nameLength, bytes("<clinit>"))) {
            revert CallError(4, pc);
        }
        if (!_validOrdinaryMethodName(caller.data, out.nameOffset, out.nameLength)) {
            revert CallError(1, pc);
        }
        out.symbolic = symbolic;
        out.referenceClass = callerClass;
        (bool own, uint256 ownMethod) = _lookupExactMethod(
            classes, symbolic, caller.data, out.nameOffset, out.nameLength,
            out.descriptorOffset, out.descriptorLength, pc
        );
        if (own) {
            out.owner = symbolic;
            out.method = ownMethod;
        } else {
            bool objectFallback;
            for (uint256 i = 0; i < classes.length; ++i) {
                if (!_isObjectClass(classes[i])) continue;
                (bool hasObject, uint256 objectMethod) = _lookupExactMethod(
                    classes, i, caller.data, out.nameOffset, out.nameLength,
                    out.descriptorOffset, out.descriptorLength, pc
                );
                if (hasObject) {
                    uint16 access = uint16(classes[i].methods[objectMethod]);
                    if ((access & 0x0001) != 0 && (access & 0x0008) == 0) {
                        out.owner = i;
                        out.method = objectMethod;
                        objectFallback = true;
                    }
                }
                break;
            }
            if (!objectFallback) {
                if (_isStringProfileSymbolic(classes[symbolic])) {
                    _rejectStringProfileCall(caller.data, out.descriptorOffset, out.descriptorLength, pc);
                }
                (bool inherited, uint256 interfaceOwner, uint256 interfaceMethod) =
                    _findInterfaceMethod(
                        classes, symbolic, true, caller.data, out.nameOffset, out.nameLength,
                        out.descriptorOffset, out.descriptorLength, parentLinks, pc
                    );
                if (interfaceOwner == type(uint256).max) {
                    out.javaFault = interfaceMethod;
                    return out;
                }
                if (!inherited) revert CallError(3, pc);
                out.owner = interfaceOwner;
                out.method = interfaceMethod;
            }
        }
        uint16 resolvedAccess = uint16(classes[out.owner].methods[out.method]);
        if ((resolvedAccess & 0x0001) == 0
            || (resolvedAccess & (0x0002 | 0x0008 | 0x0100)) != 0) revert CallError(4, pc);
    }

    function _selectVirtual(
        ClassInfo[] memory classes, uint256 dynamicClass, VirtualResolution memory resolved,
        uint256[] memory parentLinks, uint256 pc
    ) private pure returns (uint256 owner, uint256 method) {
        if (_isInterface(classes[resolved.owner])) {
            ClassInfo memory referenceClass = classes[resolved.referenceClass];
            return _selectInterfaceImplementation(
                classes, dynamicClass, referenceClass.data, resolved.nameOffset,
                resolved.nameLength, resolved.descriptorOffset, resolved.descriptorLength,
                parentLinks, pc
            );
        }
        uint256[] memory path = new uint256[](classes.length);
        uint256 count;
        uint256 current = dynamicClass;
        while (current != resolved.owner) {
            if (count == classes.length) revert ReferenceError(2, pc);
            path[count++] = current;
            uint256 link = parentLinks[current];
            if (link == 0 || link == type(uint256).max) revert ReferenceError(2, pc);
            current = link - 1;
        }
        owner = resolved.owner;
        method = resolved.method;
        ClassInfo memory referenceClass = classes[resolved.referenceClass];
        while (count != 0) {
            uint256 candidateClass = path[--count];
            (bool found, uint256 candidate) = _lookupExactMethod(
                classes, candidateClass, referenceClass.data, resolved.nameOffset,
                resolved.nameLength, resolved.descriptorOffset, resolved.descriptorLength, pc
            );
            if (!found) continue;
            uint16 candidateAccess = uint16(classes[candidateClass].methods[candidate]);
            if ((candidateAccess & 0x0002) != 0) continue; // private never overrides
            uint16 selectedAccess = uint16(classes[owner].methods[method]);
            bool overrides = (selectedAccess & (0x0001 | 0x0004)) != 0
                || ((selectedAccess & 0x0002) == 0
                    && _samePackage(classes[candidateClass], classes[owner]));
            if (!overrides) continue;
            if ((selectedAccess & 0x0010) != 0 || (candidateAccess & 0x0008) != 0) {
                revert CallError(4, pc);
            }
            owner = candidateClass;
            method = candidate;
        }
        uint256 selectedMeta = classes[owner].methods[method];
        if ((uint16(selectedMeta) & 0x0400) != 0) {
            if (_methodCodeCount(selectedMeta) != 0) revert CallError(4, pc);
            return (type(uint256).max, 11);
        }
    }

    function _sameMethodDescriptor(
        ClassInfo memory first, uint256 firstMethod, ClassInfo memory second, uint256 secondMethod
    ) private pure returns (bool) {
        (uint256 firstOff, uint256 firstLen) =
            _utf(first.cp[(first.methods[firstMethod] >> 32) & 0xffff]);
        (uint256 secondOff, uint256 secondLen) =
            _utf(second.cp[(second.methods[secondMethod] >> 32) & 0xffff]);
        return _equalsCross(first.data, firstOff, firstLen, second.data, secondOff, secondLen);
    }

    function _validOrdinaryMethodName(bytes memory data, uint256 off, uint256 n)
        private
        pure
        returns (bool)
    {
        if (n == 0) return false;
        for (uint256 i = 0; i < n; ++i) {
            bytes1 ch = data[off + i];
            if (ch == bytes1(".") || ch == bytes1(";") || ch == bytes1("[")
                || ch == bytes1("/") || ch == bytes1("<") || ch == bytes1(">")
                || uint8(ch) == 0) return false;
        }
        return true;
    }

    function _resolveInterfaceSpecial(
        ClassInfo[] memory classes, uint256 callerClass, uint256 callerMethod,
        uint256 refIndex, uint256 pc, uint256[] memory parentLinks,
        uint8[] memory hierarchyState
    ) private pure returns (VirtualResolution memory out) {
        ClassInfo memory caller = classes[callerClass];
        if (refIndex == 0 || refIndex >= caller.cp.length || uint8(caller.cp[refIndex]) != 11) {
            revert CallError(1, pc);
        }
        uint256 ref = caller.cp[refIndex];
        uint256 ownerClassIndex = (ref >> 8) & 0xffff;
        uint256 natIndex = (ref >> 24) & 0xffff;
        if (ownerClassIndex == 0 || ownerClassIndex >= caller.cp.length
            || uint8(caller.cp[ownerClassIndex]) != 7 || natIndex == 0
            || natIndex >= caller.cp.length || uint8(caller.cp[natIndex]) != 12) {
            revert CallError(1, pc);
        }
        uint256 ownerNameIndex = (caller.cp[ownerClassIndex] >> 8) & 0xffff;
        if (ownerNameIndex == 0 || ownerNameIndex >= caller.cp.length
            || uint8(caller.cp[ownerNameIndex]) != 1) revert CallError(1, pc);
        (uint256 ownerOff, uint256 ownerLen) = _utf(caller.cp[ownerNameIndex]);
        if (!_validInternalName(caller.data, ownerOff, ownerLen)) revert CallError(1, pc);
        (bool foundOwner, uint256 symbolic) = _findClass(
            classes, caller.data, ownerOff, ownerLen
        );
        if (!foundOwner) _missingClass(0x1006, pc, caller.data, ownerOff, ownerLen);
        if (!_isInterface(classes[symbolic])) revert InterfaceError(1, pc);
        _validateHierarchy(classes, callerClass, parentLinks, hierarchyState);
        _validateHierarchy(classes, symbolic, parentLinks, hierarchyState);
        if (symbolic != callerClass && !_classAccessible(caller, classes[symbolic])) {
            revert CallError(4, pc);
        }
        bool direct;
        for (uint256 i = 0; i < caller.interfaces.length; ++i) {
            if (_resolveInterfaceEdge(classes, callerClass, i) == symbolic) direct = true;
        }
        if (!direct || (uint16(caller.methods[callerMethod]) & 0x0008) != 0) {
            revert CallError(4, pc);
        }

        uint256 nat = caller.cp[natIndex];
        uint256 nameIndex = (nat >> 8) & 0xffff;
        uint256 descriptorIndex = (nat >> 24) & 0xffff;
        if (nameIndex == 0 || nameIndex >= caller.cp.length || uint8(caller.cp[nameIndex]) != 1
            || descriptorIndex == 0 || descriptorIndex >= caller.cp.length
            || uint8(caller.cp[descriptorIndex]) != 1) revert CallError(1, pc);
        (out.nameOffset, out.nameLength) = _utf(caller.cp[nameIndex]);
        (out.descriptorOffset, out.descriptorLength) = _utf(caller.cp[descriptorIndex]);
        if (_equalsLiteral(caller.data, out.nameOffset, out.nameLength, bytes("<init>"))
            || _equalsLiteral(caller.data, out.nameOffset, out.nameLength, bytes("<clinit>"))) {
            revert CallError(4, pc);
        }
        if (!_validOrdinaryMethodName(caller.data, out.nameOffset, out.nameLength)) {
            revert CallError(1, pc);
        }
        out.symbolic = symbolic;
        out.referenceClass = callerClass;
        (bool own, uint256 ownMethod) = _lookupExactMethod(
            classes, symbolic, caller.data, out.nameOffset, out.nameLength,
            out.descriptorOffset, out.descriptorLength, pc
        );
        if (own) {
            out.owner = symbolic;
            out.method = ownMethod;
        } else {
            (bool inherited, uint256 inheritedOwner, uint256 inheritedMethod) =
                _findInterfaceMethod(
                    classes, symbolic, true, caller.data, out.nameOffset, out.nameLength,
                    out.descriptorOffset, out.descriptorLength, parentLinks, pc
                );
            if (inheritedOwner == type(uint256).max) {
                out.javaFault = inheritedMethod;
                return out;
            }
            if (!inherited) revert CallError(3, pc);
            out.owner = inheritedOwner;
            out.method = inheritedMethod;
        }
        uint256 meta = classes[out.owner].methods[out.method];
        uint16 access = uint16(meta);
        if ((access & 0x0001) == 0 || (access & (0x0002 | 0x0008 | 0x0020 | 0x0100)) != 0) {
            revert CallError(4, pc);
        }
        if ((access & 0x0400) != 0 || _methodCodeCount(meta) == 0) {
            if ((access & 0x0400) != 0 && _methodCodeCount(meta) != 0) {
                revert CallError(4, pc);
            }
            out.javaFault = 11;
            return out;
        }
        if (_methodCodeCount(meta) != 1) revert CallError(4, pc);
    }

    function _resolveSpecial(
        ClassInfo[] memory classes, uint256 callerClass, uint256 refIndex, uint256 pc,
        uint256[] memory cache, uint256[] memory parentLinks, uint8[] memory hierarchyState
    ) private pure returns (uint256 owner, uint256 method, uint256 symbolic, bool isConstructor) {
        if (refIndex < cache.length && cache[refIndex] != 0) {
            uint256 packed = cache[refIndex];
            return (
                uint32(packed) - 1, uint32(packed >> 32) - 1,
                uint32(packed >> 64) - 1, ((packed >> 96) & 1) != 0
            );
        }
        ClassInfo memory caller = classes[callerClass];
        if (refIndex == 0 || refIndex >= caller.cp.length || uint8(caller.cp[refIndex]) != 10) {
            revert CallError(1, pc);
        }
        uint256 ref = caller.cp[refIndex];
        uint256 ownerClassIndex = (ref >> 8) & 0xffff;
        uint256 natIndex = (ref >> 24) & 0xffff;
        if (ownerClassIndex == 0 || ownerClassIndex >= caller.cp.length
            || uint8(caller.cp[ownerClassIndex]) != 7 || natIndex == 0
            || natIndex >= caller.cp.length || uint8(caller.cp[natIndex]) != 12) {
            revert CallError(1, pc);
        }
        uint256 ownerNameIndex = (caller.cp[ownerClassIndex] >> 8) & 0xffff;
        if (ownerNameIndex == 0 || ownerNameIndex >= caller.cp.length
            || uint8(caller.cp[ownerNameIndex]) != 1) revert CallError(1, pc);
        (uint256 ownerOff, uint256 ownerLen) = _utf(caller.cp[ownerNameIndex]);
        (bool foundOwner, uint256 resolvedOwner) = _findClass(classes, caller.data, ownerOff, ownerLen);
        if (!foundOwner) _missingClass(0x100a, pc, caller.data, ownerOff, ownerLen);
        symbolic = resolvedOwner;
        _validateHierarchy(classes, symbolic, parentLinks, hierarchyState);
        if (_isInterface(classes[symbolic])) revert CallError(4, pc);
        if (symbolic != callerClass && !_classAccessible(caller, classes[symbolic])) {
            revert CallError(4, pc);
        }
        uint256 nat = caller.cp[natIndex];
        uint256 nameIndex = (nat >> 8) & 0xffff;
        uint256 descriptorIndex = (nat >> 24) & 0xffff;
        if (nameIndex == 0 || nameIndex >= caller.cp.length || uint8(caller.cp[nameIndex]) != 1
            || descriptorIndex == 0 || descriptorIndex >= caller.cp.length
            || uint8(caller.cp[descriptorIndex]) != 1) revert CallError(1, pc);
        (uint256 nameOff, uint256 nameLen) = _utf(caller.cp[nameIndex]);
        (uint256 descriptorOff, uint256 descriptorLen) = _utf(caller.cp[descriptorIndex]);
        isConstructor = _equalsLiteral(caller.data, nameOff, nameLen, bytes("<init>"));
        if (_equalsLiteral(caller.data, nameOff, nameLen, bytes("<clinit>"))) {
            revert CallError(4, pc);
        }
        if (isConstructor && _isNamedClass(classes[symbolic], bytes("java/lang/String"))) {
            Selected memory constructorSignature;
            if (!_descriptor(caller.data, descriptorOff, descriptorLen, constructorSignature)
                || constructorSignature.returnKind != 2) revert CallError(4, pc);
            bool supported = constructorSignature.argumentKinds.length == 1
                && constructorSignature.argumentKinds[0] == KIND_REF
                && (_equalsLiteral(
                        caller.data, constructorSignature.argumentTypeOffsets[0],
                        constructorSignature.argumentTypeLengths[0], bytes("[C")
                    ) || _equalsLiteral(
                        caller.data, constructorSignature.argumentTypeOffsets[0],
                        constructorSignature.argumentTypeLengths[0],
                        bytes("Ljava/lang/String;")
                    ));
            if (!supported) revert StringProfileError(1, pc);
        }
        owner = symbolic;
        if (isConstructor) {
            method = _findExactMethod(
                classes, owner, caller.data, nameOff, nameLen, descriptorOff, descriptorLen, pc
            );
        } else {
            while (true) {
                (bool found, uint256 resolvedMethod) = _lookupExactMethod(
                    classes, owner, caller.data, nameOff, nameLen,
                    descriptorOff, descriptorLen, pc
                );
                if (found) { method = resolvedMethod; break; }
                uint256 resolutionLink = parentLinks[owner];
                if (resolutionLink == 0 || resolutionLink == type(uint256).max) {
                    revert CallError(3, pc);
                }
                owner = resolutionLink - 1;
            }
            uint16 initiallyResolvedAccess = uint16(classes[owner].methods[method]);
            if ((initiallyResolvedAccess & 0x0002) == 0) {
                // Non-private invokespecial must name a superclass. ACC_SUPER selection begins
                // at the caller's direct superclass and cannot bypass an override there.
                if (!_objectIsClass(callerClass, symbolic, parentLinks) || callerClass == symbolic) {
                    revert ObjectError(3, pc);
                }
                if ((caller.accessFlags & 0x0020) != 0) {
                    uint256 direct = parentLinks[callerClass];
                    if (direct == 0 || direct == type(uint256).max) revert ObjectError(3, pc);
                    owner = direct - 1;
                    while (true) {
                        (bool found, uint256 selectedMethod) = _lookupExactMethod(
                            classes, owner, caller.data, nameOff, nameLen,
                            descriptorOff, descriptorLen, pc
                        );
                        if (found) { method = selectedMethod; break; }
                        uint256 link = parentLinks[owner];
                        if (link == 0 || link == type(uint256).max) revert CallError(3, pc);
                        owner = link - 1;
                    }
                }
            } else if (owner != callerClass) revert CallError(4, pc);
        }
        if (!_canAccessMember(classes, callerClass, owner,
            uint16(classes[owner].methods[method]), parentLinks, hierarchyState)) {
            revert CallError(4, pc);
        }
        cache[refIndex] = (owner + 1) | ((method + 1) << 32)
            | ((symbolic + 1) << 64) | (isConstructor ? uint256(1) << 96 : 0);
    }

    function _resolveCall(
        ClassInfo[] memory classes,
        uint256 callerClass,
        uint256 refIndex,
        uint256 pc,
        uint256[] memory cache,
        bool bundleMode,
        uint256[] memory parentLinks,
        uint8[] memory hierarchyState
    ) private pure returns (uint256 owner, uint256 method) {
        ClassInfo memory caller = classes[callerClass];
        if (refIndex == 0 || refIndex >= caller.cp.length) revert CallError(1, pc);
        uint8 referenceTag = uint8(caller.cp[refIndex]);
        if (referenceTag != 10 && referenceTag != 11) revert CallError(1, pc);
        bool interfaceReference = referenceTag == 11;
        if (cache[refIndex] != 0) {
            owner = (cache[refIndex] >> 128) - 1;
            method = uint128(cache[refIndex]) - 1;
            return (owner, method);
        }
        uint256 ref = caller.cp[refIndex];
        uint256 ownerClassIndex = (ref >> 8) & 0xffff;
        uint256 nameAndTypeIndex = (ref >> 24) & 0xffff;
        if (
            ownerClassIndex == 0 || ownerClassIndex >= caller.cp.length
                || uint8(caller.cp[ownerClassIndex]) != 7 || nameAndTypeIndex == 0
                || nameAndTypeIndex >= caller.cp.length
                || uint8(caller.cp[nameAndTypeIndex]) != 12
        ) revert CallError(1, pc);
        uint256 ownerNameIndex = (caller.cp[ownerClassIndex] >> 8) & 0xffff;
        if (
            ownerNameIndex == 0 || ownerNameIndex >= caller.cp.length
                || uint8(caller.cp[ownerNameIndex]) != 1
        ) revert CallError(1, pc);
        (uint256 ownerOffset, uint256 ownerLength) = _utf(caller.cp[ownerNameIndex]);
        if (!_validInternalName(caller.data, ownerOffset, ownerLength)) revert CallError(1, pc);
        bool sameOwner = _equalsSlice(
            caller.data, ownerOffset, ownerLength, caller.thisNameOffset, caller.thisNameLength
        );
        if (sameOwner) {
            owner = callerClass;
        } else {
            if (!bundleMode
                && !_equalsLiteral(caller.data, ownerOffset, ownerLength, bytes("java/lang/Float"))
                && !_equalsLiteral(caller.data, ownerOffset, ownerLength, bytes("java/lang/Double"))
                && !_equalsLiteral(caller.data, ownerOffset, ownerLength, bytes("java/lang/String"))
                && !_equalsLiteral(caller.data, ownerOffset, ownerLength, bytes("java/lang/Comparable"))
                && !_equalsLiteral(caller.data, ownerOffset, ownerLength, bytes("java/lang/CharSequence"))) {
                revert CallError(2, pc);
            }
            (bool foundOwner, uint256 resolvedOwner) = _findClass(
                classes, caller.data, ownerOffset, ownerLength
            );
            if (!foundOwner) _missingClass(0x100b, pc, caller.data, ownerOffset, ownerLength);
            owner = resolvedOwner;
        }
        _validateHierarchy(classes, owner, parentLinks, hierarchyState);
        if (interfaceReference) {
            if (!_isInterface(classes[owner])) revert InterfaceError(1, pc);
        } else if (_isInterface(classes[owner])) {
            revert CallError(4, pc);
        }
        if (owner != callerClass && !_classAccessible(caller, classes[owner])) {
            revert CallError(4, pc);
        }

        uint256 nat = caller.cp[nameAndTypeIndex];
        uint256 nameIndex = (nat >> 8) & 0xffff;
        uint256 descriptorIndex = (nat >> 24) & 0xffff;
        if (
            nameIndex == 0 || nameIndex >= caller.cp.length || uint8(caller.cp[nameIndex]) != 1
                || descriptorIndex == 0 || descriptorIndex >= caller.cp.length
                || uint8(caller.cp[descriptorIndex]) != 1
        ) revert CallError(1, pc);
        (uint256 nameOffset, uint256 nameLength) = _utf(caller.cp[nameIndex]);
        (uint256 descriptorOffset, uint256 descriptorLength) = _utf(caller.cp[descriptorIndex]);
        if (
            _equalsLiteral(caller.data, nameOffset, nameLength, bytes("<clinit>"))
                || _equalsLiteral(caller.data, nameOffset, nameLength, bytes("<init>"))
        ) revert CallError(4, pc);
        if (!_validOrdinaryMethodName(caller.data, nameOffset, nameLength)) {
            revert CallError(1, pc);
        }
        // LB0 exposes no static API on any of its three reserved String-profile types.
        if (_isStringProfileSymbolic(classes[owner])) {
            _rejectStringProfileCall(caller.data, descriptorOffset, descriptorLength, pc);
        }

        if (interfaceReference) {
            // Interface static methods are never inherited: resolution is exact
            // in the symbolic interface named by CONSTANT_InterfaceMethodref.
            method = _findExactMethod(
                classes, owner, caller.data, nameOffset, nameLength,
                descriptorOffset, descriptorLength, pc
            );
        } else {
            uint256 declaring = owner;
            uint256 foundPlusOne;
            while (true) {
                ClassInfo memory target = classes[declaring];
                for (uint256 i = 0; i < target.methods.length; ++i) {
                    uint256 candidate = target.methods[i];
                    (uint256 candidateNameOffset, uint256 candidateNameLength) =
                        _utf(target.cp[(candidate >> 16) & 0xffff]);
                    if (!_equalsCross(
                        target.data, candidateNameOffset, candidateNameLength,
                        caller.data, nameOffset, nameLength
                    )) continue;
                    (uint256 candidateDescriptorOffset, uint256 candidateDescriptorLength) =
                        _utf(target.cp[(candidate >> 32) & 0xffff]);
                    if (!_equalsCross(
                        target.data, candidateDescriptorOffset, candidateDescriptorLength,
                        caller.data, descriptorOffset, descriptorLength
                    )) continue;
                    if (foundPlusOne != 0) revert CallError(3, pc);
                    foundPlusOne = i + 1;
                }
                if (foundPlusOne != 0) break; // first declaring class with an exact match wins
                uint256 link = parentLinks[declaring];
                if (link == 0 || link == type(uint256).max) revert CallError(3, pc);
                declaring = link - 1;
            }
            owner = declaring;
            method = foundPlusOne - 1;
        }
        if (!_canAccessMember(
            classes, callerClass, owner, uint16(classes[owner].methods[method]),
            parentLinks, hierarchyState
        )) revert CallError(4, pc);
        cache[refIndex] = ((owner + 1) << 128) | (method + 1);
    }

    function _resolveField(
        ClassInfo[] memory classes,
        uint256 callerClass,
        uint256 refIndex,
        uint256 pc,
        uint256[] memory cache,
        bool writeAccess,
        bool staticAccess,
        bool privilegedWrite,
        uint256[] memory parentLinks,
        uint8[] memory hierarchyState
    ) private pure returns (uint256 owner, uint256 field, uint8 valueKind, uint256 symbolic) {
        ClassInfo memory caller = classes[callerClass];
        if (refIndex == 0 || refIndex >= caller.cp.length || uint8(caller.cp[refIndex]) != 9) {
            revert FieldError(1, pc);
        }
        uint256 ref = caller.cp[refIndex];
        uint256 ownerClassIndex = (ref >> 8) & 0xffff;
        uint256 nameAndTypeIndex = (ref >> 24) & 0xffff;
        if (
            ownerClassIndex == 0 || ownerClassIndex >= caller.cp.length
                || uint8(caller.cp[ownerClassIndex]) != 7 || nameAndTypeIndex == 0
                || nameAndTypeIndex >= caller.cp.length
                || uint8(caller.cp[nameAndTypeIndex]) != 12
        ) revert FieldError(1, pc);
        uint256 ownerNameIndex = (caller.cp[ownerClassIndex] >> 8) & 0xffff;
        if (ownerNameIndex == 0 || ownerNameIndex >= caller.cp.length
            || uint8(caller.cp[ownerNameIndex]) != 1) revert FieldError(1, pc);
        (uint256 ownerOffset, uint256 ownerLength) = _utf(caller.cp[ownerNameIndex]);
        if (!_validInternalName(caller.data, ownerOffset, ownerLength)) revert FieldError(1, pc);
        (bool ownerFound, uint256 symbolicOwner) = _findClass(
            classes, caller.data, ownerOffset, ownerLength
        );
        if (!ownerFound) _missingClass(0x1007, pc, caller.data, ownerOffset, ownerLength);
        symbolic = symbolicOwner;
        _validateHierarchy(classes, symbolic, parentLinks, hierarchyState);
        if (symbolic != callerClass && !_classAccessible(caller, classes[symbolic])) {
            revert FieldError(4, pc);
        }

        if (cache[refIndex] != 0) {
            owner = (cache[refIndex] >> 128) - 1;
            field = uint128(cache[refIndex]) - 1;
        } else {
            uint256 nat = caller.cp[nameAndTypeIndex];
            uint256 nameIndex = (nat >> 8) & 0xffff;
            uint256 descriptorIndex = (nat >> 24) & 0xffff;
            if (
                nameIndex == 0 || nameIndex >= caller.cp.length || uint8(caller.cp[nameIndex]) != 1
                    || descriptorIndex == 0 || descriptorIndex >= caller.cp.length
                    || uint8(caller.cp[descriptorIndex]) != 1
            ) revert FieldError(1, pc);
            (uint256 nameOffset, uint256 nameLength) = _utf(caller.cp[nameIndex]);
            (uint256 descriptorOffset, uint256 descriptorLength) = _utf(caller.cp[descriptorIndex]);
            bool found;
            (found, owner, field) = _findResolvedField(
                classes, symbolic, caller.data, nameOffset, nameLength,
                descriptorOffset, descriptorLength, parentLinks, pc
            );
            if (!found) revert FieldError(2, pc);
            cache[refIndex] = ((owner + 1) << 128) | (field + 1);
        }

        FieldInfo memory resolved = classes[owner].fields[field];
        valueKind = _fieldKind(classes[owner], resolved);
        bool isStatic = (resolved.accessFlags & 0x0008) != 0;
        if (isStatic != staticAccess || valueKind == 0) revert FieldError(3, pc);
        if (!_canAccessMember(classes, callerClass, owner, resolved.accessFlags,
            parentLinks, hierarchyState)) revert FieldError(4, pc);
        if (writeAccess && (resolved.accessFlags & 0x0010) != 0 && !(privilegedWrite && callerClass == owner)) {
            revert FieldError(4, pc);
        }
    }

    function _findResolvedField(
        ClassInfo[] memory classes,
        uint256 symbolic,
        bytes memory nameData,
        uint256 nameOffset,
        uint256 nameLength,
        uint256 descriptorOffset,
        uint256 descriptorLength,
        uint256[] memory parentLinks,
        uint256 pc
    ) private pure returns (bool found, uint256 owner, uint256 field) {
        bool[] memory seenInterfaces = new bool[](classes.length);
        uint256 current = symbolic;
        while (true) {
            (found, field) = _fieldDeclaredHere(
                classes[current], nameData, nameOffset, nameLength,
                descriptorOffset, descriptorLength, pc
            );
            if (found) return (true, current, field);

            if (_isInterface(classes[current])) {
                seenInterfaces[current] = true;
            }
            for (uint256 i = 0; i < classes[current].interfaces.length; ++i) {
                uint256 direct = _resolveInterfaceEdge(classes, current, i);
                (found, owner, field) = _findInterfaceField(
                    classes, direct, nameData, nameOffset, nameLength,
                    descriptorOffset, descriptorLength, seenInterfaces, pc
                );
                if (found) return (true, owner, field);
            }
            // Interfaces have no ordinary superclass field-search path through Object.
            if (_isInterface(classes[current])) return (false, 0, 0);
            uint256 link = parentLinks[current];
            if (link == 0 || link == type(uint256).max) return (false, 0, 0);
            current = link - 1;
        }
    }

    function _findInterfaceField(
        ClassInfo[] memory classes,
        uint256 interfaceClass,
        bytes memory nameData,
        uint256 nameOffset,
        uint256 nameLength,
        uint256 descriptorOffset,
        uint256 descriptorLength,
        bool[] memory seen,
        uint256 pc
    ) private pure returns (bool found, uint256 owner, uint256 field) {
        if (seen[interfaceClass]) return (false, 0, 0);
        seen[interfaceClass] = true;
        (found, field) = _fieldDeclaredHere(
            classes[interfaceClass], nameData, nameOffset, nameLength,
            descriptorOffset, descriptorLength, pc
        );
        if (found) return (true, interfaceClass, field);
        for (uint256 i = 0; i < classes[interfaceClass].interfaces.length; ++i) {
            uint256 parent = _resolveInterfaceEdge(classes, interfaceClass, i);
            (found, owner, field) = _findInterfaceField(
                classes, parent, nameData, nameOffset, nameLength,
                descriptorOffset, descriptorLength, seen, pc
            );
            if (found) return (true, owner, field);
        }
        return (false, 0, 0);
    }

    function _fieldDeclaredHere(
        ClassInfo memory target,
        bytes memory nameData,
        uint256 nameOffset,
        uint256 nameLength,
        uint256 descriptorOffset,
        uint256 descriptorLength,
        uint256 pc
    ) private pure returns (bool found, uint256 field) {
        uint256 foundPlusOne;
        for (uint256 i = 0; i < target.fields.length; ++i) {
            FieldInfo memory candidate = target.fields[i];
            if (candidate.nameIndex == 0 || candidate.nameIndex >= target.cp.length
                || uint8(target.cp[candidate.nameIndex]) != 1
                || candidate.descriptorIndex == 0
                || candidate.descriptorIndex >= target.cp.length
                || uint8(target.cp[candidate.descriptorIndex]) != 1) continue;
            (uint256 candidateNameOffset, uint256 candidateNameLength) =
                _utf(target.cp[candidate.nameIndex]);
            if (!_equalsCross(target.data, candidateNameOffset, candidateNameLength,
                nameData, nameOffset, nameLength)) continue;
            (uint256 candidateDescriptorOffset, uint256 candidateDescriptorLength) =
                _utf(target.cp[candidate.descriptorIndex]);
            if (!_equalsCross(target.data, candidateDescriptorOffset, candidateDescriptorLength,
                nameData, descriptorOffset, descriptorLength)) continue;
            if (foundPlusOne != 0) revert FieldError(2, pc);
            foundPlusOne = i + 1;
        }
        if (foundPlusOne != 0) return (true, foundPlusOne - 1);
    }

    function _fieldKind(ClassInfo memory c, FieldInfo memory field)
        private
        pure
        returns (uint8)
    {
        if (
            field.descriptorIndex == 0 || field.descriptorIndex >= c.cp.length
                || uint8(c.cp[field.descriptorIndex]) != 1
        ) return 0;
        (uint256 off, uint256 n) = _utf(c.cp[field.descriptorIndex]);
        (bool valid, uint256 width, uint8 kind) = _descriptorType(c.data, off, off + n, false);
        return valid && width == n ? kind : 0;
    }

    function _fieldSubtype(ClassInfo memory c, FieldInfo memory field)
        private pure returns (uint8)
    {
        if (field.descriptorIndex == 0 || field.descriptorIndex >= c.cp.length
            || uint8(c.cp[field.descriptorIndex]) != 1) return 0;
        (uint256 off, uint256 n) = _utf(c.cp[field.descriptorIndex]);
        if (n != 1) return 0;
        uint8 subtype = uint8(c.data[off]);
        return _isIntLike(subtype) ? subtype : 0;
    }

    function _classAccessible(ClassInfo memory caller, ClassInfo memory symbolic)
        private
        pure
        returns (bool)
    {
        return (symbolic.accessFlags & 0x0001) != 0 || _samePackage(caller, symbolic);
    }

    function _canAccessMember(
        ClassInfo[] memory classes,
        uint256 callerClass,
        uint256 declaringClass,
        uint16 memberAccess,
        uint256[] memory parentLinks,
        uint8[] memory hierarchyState
    ) private pure returns (bool) {
        if (callerClass == declaringClass) return true;
        if ((memberAccess & 0x0002) != 0) return false;
        if ((memberAccess & 0x0001) != 0) return true;
        if (_samePackage(classes[callerClass], classes[declaringClass])) return true;
        if ((memberAccess & 0x0004) == 0) return false;
        _validateHierarchy(classes, callerClass, parentLinks, hierarchyState);
        uint256 current = callerClass;
        while (parentLinks[current] != 0 && parentLinks[current] != type(uint256).max) {
            current = parentLinks[current] - 1;
            if (current == declaringClass) return true;
        }
        return false;
    }

    function _requireProtectedReceiver(
        ClassInfo[] memory classes, uint256 callerClass, uint256 declaringClass, uint16 access,
        uint256 dynamicReceiverClass, uint256[] memory parentLinks, uint256 pc
    ) private pure {
        if ((access & 0x0004) == 0 || callerClass == declaringClass
            || _samePackage(classes[callerClass], classes[declaringClass])) return;
        if (!_objectIsClass(dynamicReceiverClass, callerClass, parentLinks)) {
            revert FieldError(4, pc);
        }
    }

    function _requireProtectedMethodReceiver(
        ClassInfo[] memory classes, uint256 callerClass, uint256 declaringClass, uint16 access,
        uint256 dynamicReceiverClass, uint256[] memory parentLinks, uint256 pc
    ) private pure {
        if ((access & 0x0004) == 0 || callerClass == declaringClass
            || _samePackage(classes[callerClass], classes[declaringClass])) return;
        if (!_objectIsClass(dynamicReceiverClass, callerClass, parentLinks)) {
            revert CallError(4, pc);
        }
    }

    function _samePackage(ClassInfo memory a, ClassInfo memory b) private pure returns (bool) {
        uint256 aSlash;
        uint256 bSlash;
        for (uint256 i = 0; i < a.thisNameLength; ++i) {
            if (a.data[a.thisNameOffset + i] == bytes1("/")) aSlash = i + 1;
        }
        for (uint256 i = 0; i < b.thisNameLength; ++i) {
            if (b.data[b.thisNameOffset + i] == bytes1("/")) bSlash = i + 1;
        }
        if (aSlash != bSlash) return false;
        for (uint256 i = 0; i < aSlash; ++i) {
            if (a.data[a.thisNameOffset + i] != b.data[b.thisNameOffset + i]) return false;
        }
        return true;
    }

    function _equalsCross(
        bytes memory first,
        uint256 firstOffset,
        uint256 firstLength,
        bytes memory second,
        uint256 secondOffset,
        uint256 secondLength
    ) private pure returns (bool) {
        if (firstLength != secondLength) return false;
        for (uint256 i = 0; i < firstLength; ++i) {
            if (first[firstOffset + i] != second[secondOffset + i]) return false;
        }
        return true;
    }

    function _rejectThrowableFillOverride(
        ClassInfo[] memory classes, uint256 dynamicClass, uint256 throwableClass,
        uint256[] memory parentLinks
    ) private pure {
        if (!_objectIsClass(dynamicClass, throwableClass, parentLinks)) return;
        uint256 current = dynamicClass;
        while (current != throwableClass) {
            ClassInfo memory c = classes[current];
            for (uint256 m; m < c.methods.length; ++m) {
                uint256 meta = c.methods[m];
                uint16 access = uint16(meta);
                // Private/static declarations do not participate in virtual dispatch.
                if ((access & (0x0002 | 0x0008)) != 0) continue;
                (uint256 nameOff, uint256 nameLen) = _utf(c.cp[(meta >> 16) & 0xffff]);
                if (!_equalsLiteral(c.data, nameOff, nameLen, bytes("fillInStackTrace"))) {
                    continue;
                }
                (uint256 descOff, uint256 descLen) = _utf(c.cp[(meta >> 32) & 0xffff]);
                if (_equalsLiteral(
                    c.data, descOff, descLen, bytes("()Ljava/lang/Throwable;")
                )) revert ThrowableProfileError(1, current, m);
            }
            uint256 link = parentLinks[current];
            if (link == 0 || link == type(uint256).max) return;
            current = link - 1;
        }
    }

    function _resolveNewClass(
        ClassInfo[] memory classes, uint256 callerClass, uint256 refIndex, uint256 pc,
        uint256[] memory cache, uint256[] memory parentLinks, uint8[] memory hierarchyState
    ) private pure returns (uint256 target) {
        if (refIndex < cache.length && cache[refIndex] != 0) return cache[refIndex] - 1;
        ClassInfo memory caller = classes[callerClass];
        if (refIndex == 0 || refIndex >= caller.cp.length || uint8(caller.cp[refIndex]) != 7) {
            revert ObjectError(1, pc);
        }
        uint256 nameIndex = (caller.cp[refIndex] >> 8) & 0xffff;
        if (nameIndex == 0 || nameIndex >= caller.cp.length || uint8(caller.cp[nameIndex]) != 1) {
            revert ObjectError(1, pc);
        }
        (uint256 off, uint256 n) = _utf(caller.cp[nameIndex]);
        if (!_validInternalName(caller.data, off, n)) revert ObjectError(1, pc);
        (bool found, uint256 resolved) = _findClass(classes, caller.data, off, n);
        if (!found) _missingClass(0x1008, pc, caller.data, off, n);
        target = resolved;
        _validateHierarchy(classes, target, parentLinks, hierarchyState);
        ClassInfo memory targetClass = classes[target];
        if (!_classAccessible(caller, targetClass) || (targetClass.accessFlags & 0x0400) != 0
            || (targetClass.accessFlags & 0x0200) != 0) {
            revert ObjectError(2, pc);
        }
        cache[refIndex] = target + 1;
    }

    function _validInternalName(bytes memory data, uint256 off, uint256 n)
        private pure returns (bool)
    {
        if (n == 0 || uint8(data[off]) == 0x5b || data[off] == bytes1("/")
            || data[off + n - 1] == bytes1("/")) return false;
        bool slash;
        for (uint256 i = 0; i < n; ++i) {
            bytes1 ch = data[off + i];
            if (ch == bytes1(".") || ch == bytes1(";") || ch == bytes1("[")
                || uint8(ch) == 0) return false;
            if (ch == bytes1("/")) {
                if (slash) return false;
                slash = true;
            } else slash = false;
        }
        return true;
    }

    function _validateCastTarget(ClassInfo memory caller, uint256 refIndex, uint256 pc)
        private
        pure
        returns (uint8 kind, uint256 off, uint256 n)
    {
        if (refIndex == 0 || refIndex >= caller.cp.length || uint8(caller.cp[refIndex]) != 7) {
            revert TypeError(1, pc);
        }
        uint256 nameIndex = (caller.cp[refIndex] >> 8) & 0xffff;
        if (nameIndex == 0 || nameIndex >= caller.cp.length
            || uint8(caller.cp[nameIndex]) != 1) revert TypeError(1, pc);
        (off, n) = _utf(caller.cp[nameIndex]);
        if (n != 0 && uint8(caller.data[off]) == 0x5b) {
            (bool structural, bool supported,,,,) = _arrayClassShape(caller.data, off, n);
            if (!structural) revert TypeError(1, pc);
            // Deferred primitive arrays retain the null shortcut and fail only for non-null.
            return (supported ? 2 : 3, off, n);
        }
        if (!_validInternalName(caller.data, off, n)) revert TypeError(1, pc);
        return (1, off, n);
    }

    function _arrayClassShape(bytes memory data, uint256 off, uint256 n)
        private
        pure
        returns (
            bool structural, bool supported, uint8 rank,
            uint8 primitiveLeaf, uint256 leafOffset, uint256 leafLength
        )
    {
        uint256 dimensions;
        while (dimensions < n && uint8(data[off + dimensions]) == 0x5b) {
            ++dimensions;
            if (dimensions > 255) return (false, false, 0, 0, 0, 0);
        }
        if (dimensions == 0 || dimensions >= n) return (false, false, 0, 0, 0, 0);
        rank = uint8(dimensions);
        uint8 component = uint8(data[off + dimensions]);
        if ((_isIntLike(component) || component == PRIMITIVE_LONG
            || component == PRIMITIVE_FLOAT || component == PRIMITIVE_DOUBLE)
            && dimensions + 1 == n) {
            return (true, true, rank, component, 0, 0);
        }
        if (component == 0x4c) {
            if (dimensions + 2 >= n || uint8(data[off + n - 1]) != 0x3b) {
                return (false, false, 0, 0, 0, 0);
            }
            leafOffset = off + dimensions + 1;
            leafLength = n - dimensions - 2;
            if (!_validInternalName(data, leafOffset, leafLength)) {
                return (false, false, 0, 0, 0, 0);
            }
            return (true, true, rank, 0, leafOffset, leafLength);
        }
        return (false, false, 0, 0, 0, 0);
    }

    function _resolveArrayClassType(
        ClassInfo[] memory classes, uint256 callerClass, bytes memory data,
        uint256 off, uint256 n, uint256 pc, uint256[] memory parentLinks,
        uint8[] memory hierarchyState
    ) private pure returns (ArrayType memory out) {
        (bool structural, bool supported, uint8 rank, uint8 primitiveLeaf,
            uint256 leafOffset, uint256 leafLength) = _arrayClassShape(data, off, n);
        if (!structural) revert TypeError(1, pc);
        if (!supported) revert TypeError(2, pc);
        out.rank = rank;
        if (primitiveLeaf != 0) {
            out.leafType = primitiveLeaf;
            return out;
        }
        (bool found, uint256 leafClass) = _findClass(classes, data, leafOffset, leafLength);
        if (!found) revert LinkError(4, pc);
        ClassInfo memory leaf = classes[leafClass];
        if (leafClass != callerClass && !_classAccessible(classes[callerClass], leaf)) {
            revert TypeError(2, pc);
        }
        _validateHierarchy(classes, leafClass, parentLinks, hierarchyState);
        out.leafType = ARRAY_CLASS_BASE + leafClass;
    }

    function _resolveMultiArrayType(
        ClassInfo[] memory classes, uint256 callerClass, uint256 refIndex, uint8 dimensions,
        uint256 pc, uint256[] memory parentLinks, uint8[] memory hierarchyState
    ) private pure returns (ArrayType memory out) {
        ClassInfo memory caller = classes[callerClass];
        if (refIndex == 0 || refIndex >= caller.cp.length || uint8(caller.cp[refIndex]) != 7) {
            revert TypeError(1, pc);
        }
        uint256 nameIndex = (caller.cp[refIndex] >> 8) & 0xffff;
        if (nameIndex == 0 || nameIndex >= caller.cp.length
            || uint8(caller.cp[nameIndex]) != 1) revert TypeError(1, pc);
        (uint256 off, uint256 n) = _utf(caller.cp[nameIndex]);
        if (n == 0 || uint8(caller.data[off]) != 0x5b) {
            if (!_validInternalName(caller.data, off, n)) revert TypeError(1, pc);
            revert ArrayError(3, pc);
        }
        (bool structural,, uint8 rank,,,) = _arrayClassShape(caller.data, off, n);
        if (!structural) revert TypeError(1, pc);
        if (dimensions == 0 || dimensions > rank) revert ArrayError(3, pc);
        return _resolveArrayClassType(
            classes, callerClass, caller.data, off, n, pc, parentLinks, hierarchyState
        );
    }

    function _planMultiArray(
        uint256[] memory counts, uint256 arrayCount, uint256 totalElements
    ) private pure returns (uint256 arrays, uint256 elements) {
        uint256 multiplicity = 1;
        for (uint256 level = 0; level < counts.length && multiplicity != 0; ++level) {
            // A zero return is an unambiguous OOM sentinel: every legal plan contains its root.
            if (multiplicity > MAX_ARRAYS - arrayCount - arrays) return (0, 0);
            uint256 length = counts[level];
            if (length > MAX_ARRAY_LENGTH) return (0, 0);
            uint256 remainingElements = MAX_ARRAY_ELEMENTS - totalElements - elements;
            if (length != 0 && multiplicity > remainingElements / length) return (0, 0);
            uint256 levelElements = multiplicity * length;
            arrays += multiplicity;
            elements += levelElements;
            // Only arrays reachable through actually materialized parent slots are planned.
            // Thus [0][huge] has one legal empty root while all counts were still validated.
            multiplicity = levelElements;
        }
    }

    function _allocateMultiArray(
        uint64[][] memory arrayHeap, uint256[] memory heapKinds,
        uint8[] memory arrayRanks, uint256[] memory arrayLeafTypes,
        uint256 nextHandle, ArrayType memory allocatedType, uint256[] memory counts
    ) private pure returns (uint256) {
        uint256 multiplicity = 1;
        uint256 previousStart;
        for (uint256 level = 0; level < counts.length && multiplicity != 0; ++level) {
            uint256 currentStart = nextHandle + 1;
            uint256 length = counts[level];
            for (uint256 i = 0; i < multiplicity; ++i) {
                ++nextHandle;
                arrayRanks[nextHandle] = allocatedType.rank - uint8(level);
                arrayLeafTypes[nextHandle] = allocatedType.leafType;
                arrayHeap[nextHandle] = new uint64[](length);
                if (level != 0) {
                    uint256 parentLength = counts[level - 1];
                    uint256 parent = previousStart + i / parentLength;
                    arrayHeap[parent][i % parentLength] = uint32(nextHandle);
                }
            }
            previousStart = currentStart;
            multiplicity *= length; // bounded by the successful quota preflight
        }
        return nextHandle;
    }

    function _resolveANewArrayType(
        ClassInfo[] memory classes, uint256 callerClass, uint256 refIndex, uint256 pc,
        uint256[] memory parentLinks, uint8[] memory hierarchyState
    ) private pure returns (ArrayType memory out) {
        ClassInfo memory caller = classes[callerClass];
        if (refIndex == 0 || refIndex >= caller.cp.length || uint8(caller.cp[refIndex]) != 7) {
            revert TypeError(1, pc);
        }
        uint256 nameIndex = (caller.cp[refIndex] >> 8) & 0xffff;
        if (nameIndex == 0 || nameIndex >= caller.cp.length
            || uint8(caller.cp[nameIndex]) != 1) revert TypeError(1, pc);
        (uint256 off, uint256 n) = _utf(caller.cp[nameIndex]);
        if (n != 0 && uint8(caller.data[off]) == 0x5b) {
            ArrayType memory component = _resolveArrayClassType(
                classes, callerClass, caller.data, off, n, pc, parentLinks, hierarchyState
            );
            if (component.rank == 255) revert ArrayError(2, pc);
            out.rank = component.rank + 1;
            out.leafType = component.leafType;
            return out;
        }
        if (!_validInternalName(caller.data, off, n)) revert TypeError(1, pc);
        (bool found, uint256 componentClass) = _findClass(classes, caller.data, off, n);
        if (!found) _missingClass(0x1009, pc, caller.data, off, n);
        ClassInfo memory componentClassInfo = classes[componentClass];
        if (componentClass != callerClass && !_classAccessible(caller, componentClassInfo)) {
            revert TypeError(2, pc);
        }
        _validateHierarchy(classes, componentClass, parentLinks, hierarchyState);
        out.rank = 1;
        out.leafType = ARRAY_CLASS_BASE + componentClass;
    }

    function _instanceFieldCount(
        ClassInfo[] memory classes, uint256 classIndex, uint256[] memory parentLinks, uint256 pc
    ) private pure returns (uint256 count) {
        uint256 current = classIndex;
        while (true) {
            ClassInfo memory c = classes[current];
            for (uint256 i = 0; i < c.fields.length; ++i) {
                if ((c.fields[i].accessFlags & 0x0008) == 0) {
                    if (_fieldKind(c, c.fields[i]) == 0) revert ObjectError(2, pc);
                    ++count;
                }
            }
            uint256 link = parentLinks[current];
            if (link == 0 || link == type(uint256).max) break;
            current = link - 1;
        }
    }

    function _instanceFieldOffset(
        ClassInfo[] memory classes, uint256 dynamicClass, uint256 declaringClass, uint256 field,
        uint256[] memory parentLinks, uint256 pc
    ) private pure returns (uint256 offset) {
        // Count declarations base-first by counting every ancestor declaration that precedes owner.
        uint256 current = dynamicClass;
        bool found;
        while (true) {
            if (current == declaringClass) { found = true; break; }
            uint256 link = parentLinks[current];
            if (link == 0 || link == type(uint256).max) break;
            current = link - 1;
        }
        if (!found) revert ReferenceError(2, pc);
        current = dynamicClass;
        while (current != declaringClass) {
            uint256 link = parentLinks[current];
            current = link - 1;
        }
        // Fields of all ancestors of declaring class precede its own fields.
        uint256 ancestor = declaringClass;
        while (parentLinks[ancestor] != 0 && parentLinks[ancestor] != type(uint256).max) {
            ancestor = parentLinks[ancestor] - 1;
            ClassInfo memory a = classes[ancestor];
            for (uint256 i = 0; i < a.fields.length; ++i) {
                if ((a.fields[i].accessFlags & 0x0008) == 0) ++offset;
            }
        }
        // The loop above counts nearest-to-root in any order; only the count matters.
        ClassInfo memory declaring = classes[declaringClass];
        for (uint256 i = 0; i < field; ++i) {
            if ((declaring.fields[i].accessFlags & 0x0008) == 0) ++offset;
        }
    }

    function _objectFieldDefaults(
        ClassInfo[] memory classes, uint256 dynamicClass, uint256 fieldCount,
        uint256[] memory parentLinks
    ) private pure returns (uint256[] memory values) {
        values = new uint256[](fieldCount);
        // Layout is base-first. Walking child-to-root and each declaration in reverse lets a
        // single descending cursor fill those offsets without an O(fields^2) offset lookup.
        uint256 cursor = values.length;
        uint256 current = dynamicClass;
        while (true) {
            ClassInfo memory c = classes[current];
            for (uint256 i = c.fields.length; i != 0; --i) {
                FieldInfo memory field = c.fields[i - 1];
                if ((field.accessFlags & 0x0008) == 0) {
                    --cursor;
                    uint8 kind = _fieldKind(c, field);
                    // _instanceFieldCount already rejected unsupported instance descriptors.
                    values[cursor] = kind == KIND_INT ? _packInt(0)
                        : (kind == KIND_LONG ? _packLong(0)
                            : (kind == KIND_FLOAT ? _packFloat(0)
                                : (kind == KIND_DOUBLE ? _packDouble(0) : _packRef(0))));
                }
            }
            uint256 link = parentLinks[current];
            if (link == 0 || link == type(uint256).max) break;
            current = link - 1;
        }
    }

    function _objectIsClass(
        uint256 dynamicClass, uint256 wantedClass, uint256[] memory parentLinks
    ) private pure returns (bool) {
        uint256 current = dynamicClass;
        while (true) {
            if (current == wantedClass) return true;
            uint256 link = parentLinks[current];
            if (link == 0 || link == type(uint256).max) return false;
            current = link - 1;
        }
    }

    function _interfaceExtends(
        ClassInfo[] memory classes, uint256 child, uint256 wanted
    ) private pure returns (bool) {
        bool[] memory seen = new bool[](classes.length);
        uint256[] memory queue = new uint256[](classes.length);
        uint256 head;
        uint256 tail;
        seen[child] = true;
        queue[tail++] = child;
        while (head < tail) {
            uint256 current = queue[head++];
            if (current == wanted) return true;
            for (uint256 i = 0; i < classes[current].interfaces.length; ++i) {
                uint256 parent = _resolveInterfaceEdge(classes, current, i);
                if (!seen[parent]) {
                    seen[parent] = true;
                    queue[tail++] = parent;
                }
            }
        }
        return false;
    }

    function _classImplements(
        ClassInfo[] memory classes, uint256 dynamicClass, uint256 wanted,
        uint256[] memory parentLinks
    ) private pure returns (bool) {
        uint256 current = dynamicClass;
        while (true) {
            for (uint256 i = 0; i < classes[current].interfaces.length; ++i) {
                uint256 direct = _resolveInterfaceEdge(classes, current, i);
                if (_interfaceExtends(classes, direct, wanted)) return true;
            }
            uint256 link = parentLinks[current];
            if (link == 0 || link == type(uint256).max) return false;
            current = link - 1;
        }
    }

    function _typeAssignable(
        ClassInfo[] memory classes, uint256 actual, uint256 wanted,
        uint256[] memory parentLinks
    ) private pure returns (bool) {
        if (_isInterface(classes[wanted])) {
            return _isInterface(classes[actual])
                ? _interfaceExtends(classes, actual, wanted)
                : _classImplements(classes, actual, wanted, parentLinks);
        }
        if (_isInterface(classes[actual])) return _isObjectClass(classes[wanted]);
        return _objectIsClass(actual, wanted, parentLinks);
    }

    function _arrayImplementsClass(ClassInfo[] memory classes, uint256 wanted)
        private pure returns (bool)
    {
        if (_isObjectClass(classes[wanted])) return true;
        bool wantedMarker = _isNamedClass(classes[wanted], bytes("java/lang/Cloneable"))
            || _isNamedClass(classes[wanted], bytes("java/io/Serializable"));
        if (!_isInterface(classes[wanted])) {
            if (wantedMarker) revert InterfaceError(1, wanted);
            return false;
        }

        // Array classes directly implement the two canonical marker interfaces. Their
        // ordinary superinterface closure applies too when a supplied marker extends
        // another interface; checking only the two marker names loses that assignability.
        bool assignable;
        for (uint256 i = 0; i < classes.length; ++i) {
            if (!_isNamedClass(classes[i], bytes("java/lang/Cloneable"))
                && !_isNamedClass(classes[i], bytes("java/io/Serializable"))) continue;
            if (!_isInterface(classes[i])) revert InterfaceError(1, i);
            _validateInterfaceClosure(classes, i, new uint256[](classes.length));
            if (_interfaceExtends(classes, i, wanted)) assignable = true;
        }
        return assignable;
    }

    function _arrayHasReferenceComponents(uint8 rank, uint256 leafType)
        private pure returns (bool)
    {
        return rank > 1 || leafType >= ARRAY_CLASS_BASE;
    }

    function _arrayTypeAssignable(
        ClassInfo[] memory classes, uint8 actualRank, uint256 actualLeafType,
        uint8 wantedRank, uint256 wantedLeafType, uint256[] memory parentLinks
    ) private pure returns (bool) {
        if (wantedLeafType < ARRAY_CLASS_BASE) {
            return actualLeafType == wantedLeafType && actualRank == wantedRank;
        }
        if (actualRank < wantedRank) return false;
        uint256 wantedClass = wantedLeafType - ARRAY_CLASS_BASE;
        if (actualRank > wantedRank) return _arrayImplementsClass(classes, wantedClass);
        return actualLeafType >= ARRAY_CLASS_BASE
            && _typeAssignable(
                classes, actualLeafType - ARRAY_CLASS_BASE, wantedClass, parentLinks
            );
    }

    function _valueFitsArrayComponent(
        ClassInfo[] memory classes, uint256 value, uint8 arrayRank,
        uint256 arrayLeafType, uint256[] memory heapKinds,
        uint256[] memory heapClasses, uint8[] memory arrayRanks,
        uint256[] memory arrayLeafTypes, uint256[] memory parentLinks
    ) private pure returns (bool) {
        uint256 handle = _payload(value);
        if (handle == 0) return true;
        if (arrayRank > 1) {
            return _heapKindAt(heapKinds[handle]) == HEAP_ARRAY && _arrayTypeAssignable(
                classes, arrayRanks[handle], arrayLeafTypes[handle],
                arrayRank - 1, arrayLeafType, parentLinks
            );
        }
        // A rank-one reference array has a class or interface component.
        uint256 wantedClass = arrayLeafType - ARRAY_CLASS_BASE;
        if (_heapKindAt(heapKinds[handle]) == HEAP_ARRAY) return _arrayImplementsClass(classes, wantedClass);
        return _heapKindAt(heapKinds[handle]) == HEAP_OBJECT
            && _typeAssignable(classes, heapClasses[handle], wantedClass, parentLinks);
    }

    function _requireAssignable(
        ClassInfo[] memory classes, uint256 value, bytes memory descriptorData,
        uint256 descriptorOffset, uint256 descriptorLength, uint256[] memory heapKinds,
        uint256[] memory heapClasses, uint8[] memory arrayRanks,
        uint256[] memory arrayLeafTypes, uint256 nextHandle,
        uint256[] memory parentLinks, uint256 pc
    ) private pure {
        _requireKind(value, KIND_REF, pc);
        uint256 handle = _payload(value);
        if (handle == 0) return;
        if (handle > nextHandle || _heapKindAt(heapKinds[handle]) == 0) revert ReferenceError(1, pc);
        if (descriptorLength != 0 && uint8(descriptorData[descriptorOffset]) == 0x5b) {
            (bool structural, bool supported, uint8 wantedRank, uint8 primitiveLeaf,
                uint256 leafOffset, uint256 leafLength) = _arrayClassShape(
                    descriptorData, descriptorOffset, descriptorLength
                );
            if (!structural || !supported) revert ReferenceError(2, pc);
            if (_heapKindAt(heapKinds[handle]) != HEAP_ARRAY) revert ReferenceError(1, pc);
            uint256 wantedLeafType = primitiveLeaf;
            if (primitiveLeaf == 0) {
                (bool found, uint256 wantedLeafClass) = _findClass(
                    classes, descriptorData, leafOffset, leafLength
                );
                if (!found) revert LinkError(4, pc);
                _validateHierarchy(
                    classes, wantedLeafClass, parentLinks, new uint8[](classes.length)
                );
                wantedLeafType = ARRAY_CLASS_BASE + wantedLeafClass;
            }
            if (!_arrayTypeAssignable(
                classes, arrayRanks[handle], arrayLeafTypes[handle],
                wantedRank, wantedLeafType, parentLinks
            )) revert ReferenceError(2, pc);
            return;
        }
        if (descriptorLength < 3 || uint8(descriptorData[descriptorOffset]) != 0x4c
            || uint8(descriptorData[descriptorOffset + descriptorLength - 1]) != 0x3b) {
            revert ReferenceError(2, pc);
        }
        uint256 nameOffset = descriptorOffset + 1;
        uint256 nameLength = descriptorLength - 2;
        (bool found, uint256 wantedClass) = _findClass(classes, descriptorData, nameOffset, nameLength);
        if (!found) revert LinkError(4, pc);
        _validateHierarchy(classes, wantedClass, parentLinks, new uint8[](classes.length));
        if (_heapKindAt(heapKinds[handle]) == HEAP_ARRAY) {
            if (_isObjectClass(classes[wantedClass])) return;
            if (!_isInterface(classes[wantedClass])) revert ReferenceError(1, pc);
            if (!_arrayImplementsClass(classes, wantedClass)) revert ReferenceError(2, pc);
            return;
        }
        if (_heapKindAt(heapKinds[handle]) != HEAP_OBJECT) revert ReferenceError(1, pc);
        if (!_typeAssignable(classes, heapClasses[handle], wantedClass, parentLinks)) {
            revert ReferenceError(2, pc);
        }
    }

    function _predecode(ClassInfo memory c, Selected memory s)
        private
        pure
        returns (bool[] memory starts)
    {
        starts = new bool[](s.codeLength);
        uint256 pc;
        while (pc < s.codeLength) {
            starts[pc] = true;
            uint8 op = uint8(c.data[s.codeOffset + pc]);
            uint256 width = _instructionWidth(c.data, s.codeOffset, s.codeLength, op, pc);
            if (width > s.codeLength - pc) revert BytecodeError(2, pc);
            if (
                (op == 0xac && s.returnKind != 1) || (op == 0xad && s.returnKind != 4)
                    || (op == 0xae && s.returnKind != 5) || (op == 0xaf && s.returnKind != 6)
                    || (op == 0xb1 && s.returnKind != 2) || (op == 0xb0 && s.returnKind != 3)
            ) revert CallError(5, pc);
            if (op == 0xbc && _newArrayPrimitive(uint8(c.data[s.codeOffset + pc + 1])) == 0) {
                revert ArrayError(1, pc);
            }
            if (op == 0x12 || op == 0x13 || op == 0x14) {
                uint256 index = op == 0x12
                    ? uint8(c.data[s.codeOffset + pc + 1])
                    : _unsigned16(c.data, s.codeOffset + pc + 1);
                uint8 tag = index < c.cp.length ? uint8(c.cp[index]) : 0;
                bool validTag = op == 0x14 ? (tag == 5 || tag == 6)
                    : (tag == 3 || tag == 4 || tag == 8 || tag == 7);
                if (index == 0 || !validTag) revert BytecodeError(13, pc);
                if (tag == 8) _validateStringConstant(c, s.declaringClass, index);
                // A Class operand is validated but intentionally not linked here:
                // an untaken ldc must neither load nor initialize its target.
                if (tag == 7) _validateClassLiteralOperand(c, index, pc);
            }
            pc += width;
        }
        // The first pass has already decoded and validated every instruction's
        // width. Walk its start map directly for edge validation rather than
        // decoding every instruction a second time. Operand and switch-payload
        // bytes remain untrusted, but are ignored unless the first pass marked
        // them as actual instruction starts.
        for (pc = 0; pc < s.codeLength; ++pc) {
            if (!starts[pc]) continue;
            uint8 op = uint8(c.data[s.codeOffset + pc]);
            if ((op >= 0x99 && op <= 0xa7) || op == 0xc6 || op == 0xc7) {
                _requireDecodedTarget(
                    _decodedTarget(c.data, s.codeOffset, pc), starts, s.codeLength, pc
                );
            } else if (op == 0xc8) {
                _requireDecodedTarget(
                    _decodedWideTarget(c.data, s.codeOffset, pc, pc + 1),
                    starts, s.codeLength, pc
                );
            } else if (op == 0xaa || op == 0xab) {
                _validateSwitchTargets(c.data, s.codeOffset, s.codeLength, pc, starts, op == 0xab);
            }
        }
        uint256 whole = type(uint256).max;
        if (s.handlerStarts.length != 0 && s.maxStack < 1) {
            revert HandlerError(7, s.declaringClass, s.methodIndex, whole);
        }
        for (uint256 i = 0; i < s.handlerStarts.length; ++i) {
            uint256 startPC = s.handlerStarts[i];
            uint256 endPC = s.handlerEnds[i];
            uint256 targetPC = s.handlerPCs[i];
            if (startPC >= endPC || endPC > s.codeLength || targetPC >= s.codeLength) {
                revert HandlerError(2, s.declaringClass, s.methodIndex, i);
            }
            if (!starts[startPC] || !starts[targetPC]
                || (endPC != s.codeLength && !starts[endPC])) {
                revert HandlerError(3, s.declaringClass, s.methodIndex, i);
            }
        }
    }

    function _instructionWidth(
        bytes memory data, uint256 codeOffset, uint256 codeLength, uint8 op, uint256 pc
    ) private pure returns (uint256) {
        if (op == 0xaa || op == 0xab) {
            return _switchInstructionWidth(data, codeOffset, codeLength, pc, op == 0xab);
        }
        if (op == 0xc4) return _wideInstructionWidth(data, codeOffset, codeLength, pc);
        if (
            op <= 0x01 || (op >= 0x02 && op <= 0x0f) || (op >= 0x1a && op <= 0x35)
                || (op >= 0x3b && op <= 0x56)
                || (op >= 0x57 && op <= 0x77)
                || (op >= 0x78 && op <= 0x83) || (op >= 0x85 && op <= 0x98)
                || (op >= 0xac && op <= 0xb1) || op == 0xbe || op == 0xbf
        ) return 1;
        if (op == 0x10 || op == 0x12 || (op >= 0x15 && op <= 0x19)
            || (op >= 0x36 && op <= 0x3a) || op == 0xbc) return 2;
        if (
            op == 0x11 || op == 0x13 || op == 0x14 || op == 0x84 || (op >= 0x99 && op <= 0xa7)
                || op == 0xb2 || op == 0xb3 || op == 0xb4 || op == 0xb5
                || op == 0xb6 || op == 0xb7 || op == 0xb8 || op == 0xbb || op == 0xbd
                || op == 0xc0 || op == 0xc1 || op == 0xc6 || op == 0xc7
        ) return 3;
        if (op == 0xc5) return 4;
        if (op == 0xb9 || op == 0xc8) return 5;
        revert BytecodeError(6, pc);
    }

    function _switchInstructionWidth(
        bytes memory data, uint256 codeOffset, uint256 codeLength, uint256 pc, bool lookup
    ) private pure returns (uint256) {
        uint256 padding = (4 - ((pc + 1) % 4)) % 4;
        uint256 header = 1 + padding;
        uint256 fixedSize = lookup ? 8 : 12;
        uint256 remaining = codeLength - pc;
        if (header > remaining || fixedSize > remaining - header) revert BytecodeError(2, pc);
        uint256 at = codeOffset + pc + header;
        if (lookup) {
            int32 signedPairs = _signed32(data, at + 4);
            if (signedPairs < 0) revert BytecodeError(15, pc);
            uint256 pairs = uint256(uint32(signedPairs));
            uint256 payloadRemaining = remaining - header - fixedSize;
            if (pairs > payloadRemaining / 8) revert BytecodeError(2, pc);
            if (pairs != 0) {
                int32 prior = _signed32(data, at + 8);
                for (uint256 i = 1; i < pairs; ++i) {
                    int32 key = _signed32(data, at + 8 + i * 8);
                    if (key <= prior) revert BytecodeError(15, pc);
                    prior = key;
                }
            }
            return header + fixedSize + pairs * 8;
        }
        int32 low = _signed32(data, at + 4);
        int32 high = _signed32(data, at + 8);
        if (low > high) revert BytecodeError(15, pc);
        uint256 count = uint256(int256(high) - int256(low) + 1);
        uint256 payloadRemaining = remaining - header - fixedSize;
        if (count > payloadRemaining / 4) revert BytecodeError(2, pc);
        return header + fixedSize + count * 4;
    }

    function _wideInstructionWidth(
        bytes memory data, uint256 codeOffset, uint256 codeLength, uint256 pc
    ) private pure returns (uint256) {
        uint256 remaining = codeLength - pc;
        if (remaining < 2) revert BytecodeError(2, pc);
        uint8 embedded = uint8(data[codeOffset + pc + 1]);
        bool supported = (embedded >= 0x15 && embedded <= 0x19)
            || (embedded >= 0x36 && embedded <= 0x3a) || embedded == 0x84;
        bool recognizedUnsupported = embedded == 0xa9;
        if (!supported && !recognizedUnsupported) revert BytecodeError(15, pc);
        uint256 width = embedded == 0x84 ? 6 : 4;
        if (width > remaining) revert BytecodeError(2, pc);
        if (recognizedUnsupported) revert BytecodeError(6, pc);
        return width;
    }

    function _validateSwitchTargets(
        bytes memory data, uint256 codeOffset, uint256 codeLength, uint256 pc,
        bool[] memory starts, bool lookup
    ) private pure {
        uint256 padding = (4 - ((pc + 1) % 4)) % 4;
        uint256 at = pc + 1 + padding;
        _requireDecodedTarget(
            _decodedWideTarget(data, codeOffset, pc, at), starts, codeLength, pc
        );
        if (lookup) {
            uint256 pairs = uint256(uint32(_signed32(data, codeOffset + at + 4)));
            for (uint256 i = 0; i < pairs; ++i) {
                _requireDecodedTarget(
                    _decodedWideTarget(data, codeOffset, pc, at + 12 + i * 8),
                    starts, codeLength, pc
                );
            }
        } else {
            int32 low = _signed32(data, codeOffset + at + 4);
            int32 high = _signed32(data, codeOffset + at + 8);
            uint256 count = uint256(int256(high) - int256(low) + 1);
            for (uint256 i = 0; i < count; ++i) {
                _requireDecodedTarget(
                    _decodedWideTarget(data, codeOffset, pc, at + 12 + i * 4),
                    starts, codeLength, pc
                );
            }
        }
    }

    function _requireDecodedTarget(
        uint256 target, bool[] memory starts, uint256 codeLength, uint256 pc
    ) private pure {
        if (target >= codeLength || !starts[target]) revert BytecodeError(12, pc);
    }

    function _readCode(ClassInfo memory c, uint256 start, uint256 length, Selected memory s)
        private pure
    {
        bytes memory data = c.data;
        if (start > type(uint256).max - length || start + length > data.length) {
            revert ClassError(6, start);
        }
        Reader memory r = Reader(data, start);
        uint256 end = start + length;
        s.maxStack = _u2Bounded(r, end);
        s.maxLocals = _u2Bounded(r, end);
        uint256 codeLength = _u4Bounded(r, end);
        if (codeLength == 0 || codeLength > MAX_CODE || codeLength > end - r.pos) {
            revert ClassError(7, r.pos);
        }
        s.codeOffset = r.pos;
        s.codeLength = codeLength;
        r.pos += codeLength;
        if (end - r.pos < 2) {
            revert HandlerError(1, s.declaringClass, s.methodIndex, type(uint256).max);
        }
        uint256 count = _u2Bounded(r, end);
        _readHandlers(c, r, end, count, s);
        uint256 nestedCount = _u2Bounded(r, end);
        for (uint256 i = 0; i < nestedCount; ++i) {
            _u2Bounded(r, end);
            uint256 n = _u4Bounded(r, end);
            if (n > end - r.pos) revert ClassError(8, r.pos);
            r.pos += n;
        }
        if (r.pos != end) revert ClassError(9, r.pos);
    }

    function _readCallCode(ClassInfo memory c, uint256 start, uint256 length, Selected memory s)
        private pure returns (bool)
    {
        bytes memory data = c.data;
        if (start > data.length || length > data.length - start || length < 8) return false;
        uint256 end = start + length;
        uint256 p = start;
        s.maxStack = _unsigned16(data, p); p += 2;
        s.maxLocals = _unsigned16(data, p); p += 2;
        uint256 codeLength = _unsigned32(data, p); p += 4;
        if (codeLength == 0 || codeLength > MAX_CODE || codeLength > end - p) return false;
        s.codeOffset = p;
        s.codeLength = codeLength;
        p += codeLength;
        if (end - p < 2) {
            revert HandlerError(1, s.declaringClass, s.methodIndex, type(uint256).max);
        }
        uint256 count = _unsigned16(data, p); p += 2;
        Reader memory r = Reader(data, p);
        _readHandlers(c, r, end, count, s);
        p = r.pos;
        if (end - p < 2) {
            revert HandlerError(1, s.declaringClass, s.methodIndex, type(uint256).max);
        }
        uint256 nestedCount = _unsigned16(data, p); p += 2;
        for (uint256 i = 0; i < nestedCount; ++i) {
            if (end - p < 6) return false;
            p += 2;
            uint256 n = _unsigned32(data, p); p += 4;
            if (n > end - p) return false;
            p += n;
        }
        return p == end;
    }

    function _readHandlers(
        ClassInfo memory c, Reader memory r, uint256 end, uint256 count, Selected memory s
    ) private pure {
        uint256 whole = type(uint256).max;
        if (count > MAX_EXCEPTION_HANDLERS || count > (end - r.pos) / 8
            || end - r.pos - count * 8 < 2) {
            revert HandlerError(1, s.declaringClass, s.methodIndex, whole);
        }
        s.handlerStarts = new uint16[](count);
        s.handlerEnds = new uint16[](count);
        s.handlerPCs = new uint16[](count);
        s.handlerCatchTypes = new uint16[](count);
        s.handlerClassesPlusOne = new uint256[](count);
        for (uint256 i = 0; i < count; ++i) {
            s.handlerStarts[i] = _u2Bounded(r, end);
            s.handlerEnds[i] = _u2Bounded(r, end);
            s.handlerPCs[i] = _u2Bounded(r, end);
            uint256 catchType = _u2Bounded(r, end);
            s.handlerCatchTypes[i] = uint16(catchType);
            if (catchType == 0) continue;
            if (catchType >= c.cp.length || uint8(c.cp[catchType]) != 7) {
                revert HandlerError(4, s.declaringClass, s.methodIndex, i);
            }
            uint256 nameIndex = (c.cp[catchType] >> 8) & 0xffff;
            if (nameIndex == 0 || nameIndex >= c.cp.length || uint8(c.cp[nameIndex]) != 1) {
                revert HandlerError(4, s.declaringClass, s.methodIndex, i);
            }
            (uint256 off, uint256 n) = _utf(c.cp[nameIndex]);
            if (!_validInternalName(c.data, off, n)) {
                revert HandlerError(4, s.declaringClass, s.methodIndex, i);
            }
        }
    }

    function _descriptor(bytes memory data, uint256 off, uint256 n, Selected memory s)
        private
        pure
        returns (bool)
    {
        if (n < 3 || off > data.length || n > data.length - off || uint8(data[off]) != 0x28) {
            return false;
        }
        uint256 i = 1;
        uint256 count;
        while (i < n && uint8(data[off + i]) != 0x29) {
            (bool ok, uint256 width,) = _descriptorType(data, off + i, off + n, false);
            if (!ok) return false;
            i += width;
            ++count;
        }
        if (i >= n || uint8(data[off + i]) != 0x29) return false;
        uint256 close = i;
        s.argumentKinds = new uint8[](count);
        s.argumentTypeOffsets = new uint256[](count);
        s.argumentTypeLengths = new uint256[](count);
        i = 1;
        uint256 at;
        while (i < close) {
            (bool ok, uint256 width, uint8 kind) = _descriptorType(data, off + i, off + close, false);
            if (!ok) return false;
            s.argumentKinds[at] = kind;
            s.argumentTypeOffsets[at] = off + i;
            s.argumentTypeLengths[at] = width;
            s.argumentWords += _isCategory2Kind(kind) ? 2 : 1;
            i += width;
            ++at;
        }
        uint256 resultOff = off + close + 1;
        if (resultOff >= off + n) return false;
        uint8 result = uint8(data[resultOff]);
        if (resultOff + 1 == off + n && _isIntLike(result)) {
            s.returnKind = 1;
            s.returnSubtype = result;
        } else if (resultOff + 1 == off + n && result == PRIMITIVE_LONG) s.returnKind = 4;
        else if (resultOff + 1 == off + n && result == PRIMITIVE_FLOAT) s.returnKind = 5;
        else if (resultOff + 1 == off + n && result == PRIMITIVE_DOUBLE) s.returnKind = 6;
        else if (resultOff + 1 == off + n && result == 0x56) s.returnKind = 2;
        else {
            (bool ok, uint256 width, uint8 kind) = _descriptorType(data, resultOff, off + n, false);
            if (!ok || kind != KIND_REF || resultOff + width != off + n) return false;
            s.returnKind = 3;
            s.returnTypeOffset = resultOff;
            s.returnTypeLength = width;
        }
        return true;
    }


    function _isMainEmptyStringArrayRoot(ClassInfo memory c, Selected memory s)
        private pure returns (bool)
    {
        return s.returnKind == 2 && s.argumentKinds.length == 1 && s.argumentWords == 1
            && s.argumentKinds[0] == KIND_REF
            && _equalsLiteral(c.data, s.descriptorOffset, s.descriptorLength, bytes("([Ljava/lang/String;)V"));
    }

    function _isIntLike(uint8 descriptor) private pure returns (bool) {
        return descriptor == PRIMITIVE_INT || descriptor == PRIMITIVE_BOOLEAN
            || descriptor == PRIMITIVE_BYTE || descriptor == PRIMITIVE_CHAR
            || descriptor == PRIMITIVE_SHORT;
    }

    function _descriptorType(bytes memory data, uint256 off, uint256 end, bool allowVoid)
        private
        pure
        returns (bool ok, uint256 width, uint8 kind)
    {
        if (off >= end) return (false, 0, 0);
        uint8 b = uint8(data[off]);
        if (_isIntLike(b)) return (true, 1, uint8(KIND_INT));
        if (b == PRIMITIVE_LONG) return (true, 1, uint8(KIND_LONG));
        if (b == PRIMITIVE_FLOAT) return (true, 1, uint8(KIND_FLOAT));
        if (b == PRIMITIVE_DOUBLE) return (true, 1, uint8(KIND_DOUBLE));
        if (allowVoid && b == 0x56) return (true, 1, 0);
        if (b == 0x5b) {
            uint256 dimensions;
            while (off + dimensions < end && uint8(data[off + dimensions]) == 0x5b) {
                ++dimensions;
                if (dimensions > 255) return (false, 0, 0);
            }
            if (off + dimensions >= end) return (false, 0, 0);
            uint8 leaf = uint8(data[off + dimensions]);
            if (_isIntLike(leaf) || leaf == PRIMITIVE_LONG
                || leaf == PRIMITIVE_FLOAT || leaf == PRIMITIVE_DOUBLE) {
                return (true, dimensions + 1, uint8(KIND_REF));
            }
            if (leaf != 0x4c) return (false, 0, 0);
            uint256 i = off + dimensions + 1;
            while (i < end && uint8(data[i]) != 0x3b) ++i;
            if (i == off + dimensions + 1 || i >= end
                || !_validInternalName(data, off + dimensions + 1, i - off - dimensions - 1)) {
                return (false, 0, 0);
            }
            return (true, i - off + 1, uint8(KIND_REF));
        }
        if (b == 0x4c) {
            uint256 i = off + 1;
            while (i < end && uint8(data[i]) != 0x3b) {
                uint8 ch = uint8(data[i]);
                if (ch == 0x2e || ch == 0x5b || ch == 0x3b || ch == 0) return (false, 0, 0);
                ++i;
            }
            if (i == off + 1 || i >= end) return (false, 0, 0);
            return (true, i - off + 1, uint8(KIND_REF));
        }
        return (false, 0, 0);
    }

    function _className(ClassInfo memory c, uint256 classIndex, uint256 at)
        private
        pure
        returns (uint256, uint256)
    {
        if (classIndex == 0 || classIndex >= c.cp.length || uint8(c.cp[classIndex]) != 7) {
            revert ClassError(10, at);
        }
        uint256 nameIndex = (c.cp[classIndex] >> 8) & 0xffff;
        _validUtf8(nameIndex, c.cp, at);
        return _utf(c.cp[nameIndex]);
    }

    function _methodCodeCount(uint256 meta) private pure returns (uint256) {
        return meta >> 144;
    }

    function _utf(uint256 packed) private pure returns (uint256 off, uint256 n) {
        off = (packed >> 8) & 0xffffffffffffffff;
        n = (packed >> 72) & 0xffffffffffffffff;
    }

    function _validUtf8(uint256 index, uint256[] memory cp, uint256 at) private pure {
        if (index == 0 || index >= cp.length || uint8(cp[index]) != 1) revert ClassError(10, at);
    }

    function _validateStringConstant(
        ClassInfo memory c, uint256 classIndex, uint256 cpIndex
    ) private pure returns (uint256 units) {
        if (cpIndex == 0 || cpIndex >= c.cp.length || uint8(c.cp[cpIndex]) != 8) {
            revert StringConstantError(1, classIndex, cpIndex, 0);
        }
        uint256 utfIndex = (c.cp[cpIndex] >> 8) & 0xffff;
        if (utfIndex == 0 || utfIndex >= c.cp.length || uint8(c.cp[utfIndex]) != 1) {
            revert StringConstantError(1, classIndex, cpIndex, 0);
        }
        (uint256 off, uint256 n) = _utf(c.cp[utfIndex]);
        uint256 end = off + n;
        uint256 at = off;
        while (at < end) {
            uint8 first = uint8(c.data[at]);
            if (first >= 1 && first <= 0x7f) {
                ++at;
            } else if (first >= 0xc0 && first <= 0xdf) {
                if (end - at < 2) revert StringConstantError(3, classIndex, cpIndex, at);
                uint8 second = uint8(c.data[at + 1]);
                if ((second & 0xc0) != 0x80) {
                    revert StringConstantError(4, classIndex, cpIndex, at + 1);
                }
                uint256 value = (uint256(first & 0x1f) << 6) | uint256(second & 0x3f);
                if (value < 0x80 && !(first == 0xc0 && second == 0x80)) {
                    revert StringConstantError(5, classIndex, cpIndex, at);
                }
                at += 2;
            } else if (first >= 0xe0 && first <= 0xef) {
                // Payload completion wins before inspecting any continuation byte.
                if (end - at < 3) revert StringConstantError(3, classIndex, cpIndex, at);
                uint8 second = uint8(c.data[at + 1]);
                uint8 third = uint8(c.data[at + 2]);
                if ((second & 0xc0) != 0x80) {
                    revert StringConstantError(4, classIndex, cpIndex, at + 1);
                }
                if ((third & 0xc0) != 0x80) {
                    revert StringConstantError(4, classIndex, cpIndex, at + 2);
                }
                uint256 value = (uint256(first & 0x0f) << 12)
                    | (uint256(second & 0x3f) << 6) | uint256(third & 0x3f);
                if (value < 0x800) revert StringConstantError(5, classIndex, cpIndex, at);
                at += 3;
            } else {
                // Includes raw NUL, continuation bytes, invalid leads, and four-byte leads.
                revert StringConstantError(2, classIndex, cpIndex, at);
            }
            ++units;
        }
    }

    function _decodeStringConstant(
        ClassInfo memory c, uint256 classIndex, uint256 cpIndex
    ) private pure returns (uint64[] memory decoded) {
        uint256 count = _validateStringConstant(c, classIndex, cpIndex);
        decoded = new uint64[](count);
        uint256 utfIndex = (c.cp[cpIndex] >> 8) & 0xffff;
        (uint256 at, uint256 n) = _utf(c.cp[utfIndex]);
        uint256 end = at + n;
        uint256 out;
        while (at < end) {
            uint8 first = uint8(c.data[at]);
            if (first <= 0x7f) {
                decoded[out++] = first;
                ++at;
            } else if (first <= 0xdf) {
                uint8 second = uint8(c.data[at + 1]);
                decoded[out++] = uint64((uint256(first & 0x1f) << 6) | uint256(second & 0x3f));
                at += 2;
            } else {
                uint8 second = uint8(c.data[at + 1]);
                uint8 third = uint8(c.data[at + 2]);
                decoded[out++] = uint64((uint256(first & 0x0f) << 12)
                    | (uint256(second & 0x3f) << 6) | uint256(third & 0x3f));
                at += 3;
            }
        }
    }

    function _decodedTarget(bytes memory data, uint256 codeOffset, uint256 pc)
        private
        pure
        returns (uint256)
    {
        int256 target = int256(pc) + int256(_signed16(data, codeOffset + pc + 1));
        if (target < 0 || target > int256(MAX_CODE)) revert BytecodeError(12, pc);
        return uint256(target);
    }

    function _decodedWideTarget(
        bytes memory data, uint256 codeOffset, uint256 pc, uint256 offsetPC
    ) private pure returns (uint256) {
        int256 target = int256(pc) + int256(_signed32(data, codeOffset + offsetPC));
        if (target < 0 || target > int256(MAX_CODE)) revert BytecodeError(12, pc);
        return uint256(target);
    }

    function _decodedSwitchTarget(
        bytes memory data, uint256 codeOffset, uint256 pc, int32 key, bool lookup
    ) private pure returns (uint256) {
        uint256 padding = (4 - ((pc + 1) % 4)) % 4;
        uint256 at = pc + 1 + padding;
        uint256 offsetPC = at;
        if (lookup) {
            uint256 pairs = uint256(uint32(_signed32(data, codeOffset + at + 4)));
            for (uint256 i = 0; i < pairs; ++i) {
                int32 candidate = _signed32(data, codeOffset + at + 8 + i * 8);
                if (candidate == key) {
                    offsetPC = at + 12 + i * 8;
                    break;
                }
                if (candidate > key) break;
            }
        } else {
            int32 low = _signed32(data, codeOffset + at + 4);
            int32 high = _signed32(data, codeOffset + at + 8);
            if (key >= low && key <= high) {
                offsetPC = at + 12 + uint256(int256(key) - int256(low)) * 4;
            }
        }
        return _decodedWideTarget(data, codeOffset, pc, offsetPC);
    }

    function _signed16(bytes memory data, uint256 off) private pure returns (int16) {
        return int16(_unsigned16(data, off));
    }

    function _signed32(bytes memory data, uint256 off) private pure returns (int32) {
        return int32(_unsigned32(data, off));
    }

    function _unsigned16(bytes memory data, uint256 off) private pure returns (uint16) {
        return (uint16(uint8(data[off])) << 8) | uint16(uint8(data[off + 1]));
    }

    function _unsigned32(bytes memory data, uint256 off) private pure returns (uint32) {
        return (uint32(uint8(data[off])) << 24) | (uint32(uint8(data[off + 1])) << 16)
            | (uint32(uint8(data[off + 2])) << 8) | uint32(uint8(data[off + 3]));
    }

    function _ieeeArithmetic(uint64 leftRaw, uint64 rightRaw, uint8 op, bool doubles)
        private pure returns (uint64)
    {
        IEEEValue memory left = _decodeIEEE(leftRaw, doubles);
        IEEEValue memory right = _decodeIEEE(rightRaw, doubles);
        if (op == 0x66 || op == 0x67) { // subtraction is addition after an exact sign flip
            right.sign = !right.sign;
            rightRaw ^= doubles ? uint64(0x8000000000000000) : uint64(0x80000000);
        }
        if (op == 0x62 || op == 0x63 || op == 0x66 || op == 0x67) {
            return _ieeeAdd(left, right, leftRaw, rightRaw, doubles);
        }
        if (op == 0x6a || op == 0x6b) return _ieeeMultiply(left, right, doubles);
        if (op == 0x6e || op == 0x6f) return _ieeeDivide(left, right, doubles);
        return _ieeeRemainder(left, right, leftRaw, rightRaw, doubles);
    }

    function _decodeIEEE(uint64 raw, bool doubles) private pure returns (IEEEValue memory out) {
        uint256 fractionBits = doubles ? 52 : 23;
        uint256 exponentBits = doubles ? 11 : 8;
        uint256 bias = doubles ? 1023 : 127;
        uint256 exponentMask = (uint256(1) << exponentBits) - 1;
        uint256 fractionMask = (uint256(1) << fractionBits) - 1;
        out.sign = ((uint256(raw) >> (fractionBits + exponentBits)) & 1) != 0;
        uint256 encodedExponent = (uint256(raw) >> fractionBits) & exponentMask;
        uint256 fraction = uint256(raw) & fractionMask;
        if (encodedExponent == exponentMask) {
            out.classKind = fraction == 0 ? 2 : 3; // infinity / NaN
            return out;
        }
        if (encodedExponent == 0) {
            if (fraction == 0) return out; // signed zero
            out.classKind = 1;
            out.significand = fraction;
            out.scale = int256(1) - int256(bias) - int256(fractionBits);
            return out;
        }
        out.classKind = 1;
        out.significand = (uint256(1) << fractionBits) | fraction;
        out.scale = int256(encodedExponent) - int256(bias) - int256(fractionBits);
    }

    function _ieeeAdd(
        IEEEValue memory left, IEEEValue memory right, uint64 leftRaw, uint64 rightRaw,
        bool doubles
    ) private pure returns (uint64) {
        if (left.classKind == 3 || right.classKind == 3) return _canonicalNaN(doubles);
        if (left.classKind == 2 || right.classKind == 2) {
            if (left.classKind == 2 && right.classKind == 2 && left.sign != right.sign) {
                return _canonicalNaN(doubles);
            }
            return _signedInfinity(left.classKind == 2 ? left.sign : right.sign, doubles);
        }
        if (left.classKind == 0 && right.classKind == 0) {
            return _signedZero(left.sign && right.sign, doubles);
        }
        if (left.classKind == 0) return rightRaw;
        if (right.classKind == 0) return leftRaw;
        uint64 magnitudeMask = doubles
            ? uint64(0x7fffffffffffffff) : uint64(0x7fffffff);
        uint64 leftMagnitude = leftRaw & magnitudeMask;
        uint64 rightMagnitude = rightRaw & magnitudeMask;
        if (left.sign != right.sign && leftMagnitude == rightMagnitude) return 0;
        return _ieeeAddFinite(
            left, right, leftMagnitude > rightMagnitude, doubles
        );
    }

    function _ieeeAddFinite(
        IEEEValue memory left, IEEEValue memory right, bool leftLarger, bool doubles
    ) private pure returns (uint64) {
        uint256 fractionBits = doubles ? 52 : 23;
        uint256 extra = fractionBits + 4; // precision plus guard, round, and sticky room
        int256 commonScale = left.scale >= right.scale ? left.scale : right.scale;
        (uint256 leftAligned, bool leftLost) = _alignedSignificand(
            left.significand, extra, commonScale - left.scale
        );
        (uint256 rightAligned, bool rightLost) = _alignedSignificand(
            right.significand, extra, commonScale - right.scale
        );
        uint256 magnitude;
        bool sticky;
        bool sign;
        if (left.sign == right.sign) {
            magnitude = leftAligned + rightAligned;
            sticky = leftLost || rightLost;
            sign = left.sign;
        } else if (leftLarger) {
            magnitude = leftAligned - rightAligned;
            sign = left.sign;
            if (rightLost) --magnitude; // floor(D-tail)=(D-1)+(1-tail)
            sticky = leftLost || rightLost;
        } else {
            magnitude = rightAligned - leftAligned;
            sign = right.sign;
            if (leftLost) --magnitude;
            sticky = leftLost || rightLost;
        }
        return _packFiniteIEEE(
            sign, magnitude, commonScale - int256(extra), sticky, doubles
        );
    }

    function _alignedSignificand(uint256 significand, uint256 extra, int256 gap)
        private pure returns (uint256 aligned, bool lost)
    {
        uint256 extended = significand << extra; // at most 109 bits
        if (gap == 0) return (extended, false);
        uint256 shift = uint256(gap);
        if (shift >= 256) return (0, extended != 0);
        aligned = extended >> shift;
        lost = (extended & ((uint256(1) << shift) - 1)) != 0;
    }

    function _ieeeMultiply(IEEEValue memory left, IEEEValue memory right, bool doubles)
        private pure returns (uint64)
    {
        if (left.classKind == 3 || right.classKind == 3) return _canonicalNaN(doubles);
        bool sign = left.sign != right.sign;
        if ((left.classKind == 2 && right.classKind == 0)
            || (left.classKind == 0 && right.classKind == 2)) return _canonicalNaN(doubles);
        if (left.classKind == 2 || right.classKind == 2) return _signedInfinity(sign, doubles);
        if (left.classKind == 0 || right.classKind == 0) return _signedZero(sign, doubles);
        // The exact product is at most 48/106 bits and is rounded only by the packer.
        return _packFiniteIEEE(
            sign, left.significand * right.significand, left.scale + right.scale,
            false, doubles
        );
    }

    function _ieeeDivide(IEEEValue memory left, IEEEValue memory right, bool doubles)
        private pure returns (uint64)
    {
        if (left.classKind == 3 || right.classKind == 3) return _canonicalNaN(doubles);
        bool sign = left.sign != right.sign;
        if ((left.classKind == 2 && right.classKind == 2)
            || (left.classKind == 0 && right.classKind == 0)) return _canonicalNaN(doubles);
        if (left.classKind == 2 || right.classKind == 0) return _signedInfinity(sign, doubles);
        if (right.classKind == 2 || left.classKind == 0) return _signedZero(sign, doubles);
        uint256 precision = doubles ? 53 : 24;
        uint256 generated = precision + 4;
        // 53+57=110 bits. The remainder is the exact sticky information below
        // this quotient, so the common packer performs the operation's sole rounding.
        uint256 numerator = left.significand << generated;
        uint256 quotient = numerator / right.significand;
        bool sticky = numerator % right.significand != 0;
        return _packFiniteIEEE(
            sign, quotient, left.scale - right.scale - int256(generated), sticky, doubles
        );
    }

    function _ieeeRemainder(
        IEEEValue memory left, IEEEValue memory right, uint64 leftRaw, uint64 rightRaw,
        bool doubles
    ) private pure returns (uint64) {
        if (left.classKind == 3 || right.classKind == 3 || left.classKind == 2
            || right.classKind == 0) return _canonicalNaN(doubles);
        if (right.classKind == 2 || left.classKind == 0) return leftRaw;
        uint64 magnitudeMask = doubles
            ? uint64(0x7fffffffffffffff) : uint64(0x7fffffff);
        if ((leftRaw & magnitudeMask) < (rightRaw & magnitudeMask)) return leftRaw;

        uint256 remainder;
        int256 remainderScale;
        if (left.scale >= right.scale) {
            uint256 modulus = right.significand;
            uint256 power = _pow2Mod(uint256(left.scale - right.scale), modulus);
            remainder = mulmod(left.significand % modulus, power, modulus);
            remainderScale = right.scale;
        } else {
            // Since |left|>=|right|, this scale gap is bounded by the significand
            // widths; the shifted divisor is no larger than the dividend.
            uint256 divisor = right.significand << uint256(right.scale - left.scale);
            remainder = left.significand % divisor;
            remainderScale = left.scale;
        }
        if (remainder == 0) return _signedZero(left.sign, doubles);
        return _packFiniteIEEE(left.sign, remainder, remainderScale, false, doubles);
    }

    function _pow2Mod(uint256 exponent, uint256 modulus) private pure returns (uint256 result) {
        if (modulus == 1) return 0;
        result = 1 % modulus;
        uint256 base = 2 % modulus;
        // Binary exponentiation takes at most 12 iterations for every binary32/64
        // exponent gap; there is no exponent-magnitude linear loop.
        while (exponent != 0) {
            if ((exponent & 1) != 0) result = mulmod(result, base, modulus);
            exponent >>= 1;
            if (exponent != 0) base = mulmod(base, base, modulus);
        }
    }

    function _packFiniteIEEE(
        bool sign, uint256 magnitude, int256 scale, bool sticky, bool doubles
    ) private pure returns (uint64) {
        if (magnitude == 0) return _signedZero(sign, doubles);
        uint256 fractionBits = doubles ? 52 : 23;
        uint256 exponentBits = doubles ? 11 : 8;
        int256 bias = doubles ? int256(1023) : int256(127);
        int256 minimumExponent = 1 - bias;
        int256 maximumExponent = bias;
        uint256 top = _highestBit256(magnitude);
        int256 exponent = int256(top) + scale;
        uint256 rounded;
        if (exponent >= minimumExponent) {
            if (top > fractionBits) {
                rounded = _roundMagnitude(magnitude, top - fractionBits, sticky);
            } else {
                rounded = magnitude << (fractionBits - top);
            }
            if (rounded == (uint256(1) << (fractionBits + 1))) {
                rounded >>= 1;
                ++exponent;
            }
            if (exponent > maximumExponent) return _signedInfinity(sign, doubles);
            uint256 encoded = (uint256(exponent + bias) << fractionBits)
                | (rounded & ((uint256(1) << fractionBits) - 1));
            if (sign) encoded |= uint256(1) << (fractionBits + exponentBits);
            return uint64(encoded);
        }

        int256 quantumScale = minimumExponent - int256(fractionBits);
        int256 shift = quantumScale - scale;
        if (shift > 0) rounded = _roundMagnitude(magnitude, uint256(shift), sticky);
        else rounded = magnitude << uint256(-shift);
        if (rounded == 0) return _signedZero(sign, doubles);
        uint256 normalBoundary = uint256(1) << fractionBits;
        uint256 encodedSubnormal = rounded >= normalBoundary ? normalBoundary : rounded;
        if (sign) encodedSubnormal |= uint256(1) << (fractionBits + exponentBits);
        return uint64(encodedSubnormal);
    }

    function _roundMagnitude(uint256 magnitude, uint256 shift, bool sticky)
        private pure returns (uint256)
    {
        if (shift == 0) return magnitude;
        if (shift >= 256) return 0;
        uint256 quotient = magnitude >> shift;
        uint256 remainder = magnitude & ((uint256(1) << shift) - 1);
        uint256 half = uint256(1) << (shift - 1);
        if (remainder > half || (remainder == half && (sticky || (quotient & 1) != 0))) {
            ++quotient;
        }
        return quotient;
    }

    function _canonicalNaN(bool doubles) private pure returns (uint64) {
        return doubles ? uint64(0x7ff8000000000000) : uint64(0x7fc00000);
    }

    function _signedInfinity(bool sign, bool doubles) private pure returns (uint64) {
        uint64 bits = doubles ? uint64(0x7ff0000000000000) : uint64(0x7f800000);
        return sign ? bits | (doubles ? uint64(0x8000000000000000) : uint64(0x80000000)) : bits;
    }

    function _signedZero(bool sign, bool doubles) private pure returns (uint64) {
        if (!sign) return 0;
        return doubles ? uint64(0x8000000000000000) : uint64(0x80000000);
    }

    function _highestBit256(uint256 value) private pure returns (uint256 bit) {
        // Arithmetic intermediates are bounded by 110 bits; this remains a small,
        // representation-bounded normalization loop rather than an exponent loop.
        while (value > 1) {
            value >>= 1;
            ++bit;
        }
    }

    function _highestBit(uint64 value) private pure returns (uint256 bit) {
        // All callers exclude zero; this loop is bounded by the 64-bit value representation.
        while (value > 1) {
            value >>= 1;
            ++bit;
        }
    }

    function _roundRightEven(uint64 value, uint256 shift) private pure returns (uint64) {
        if (shift == 0) return value;
        if (shift > 64) return 0;
        if (shift == 64) {
            uint64 half64 = uint64(1) << 63;
            return value > half64 ? 1 : 0; // an exact half rounds to the even zero
        }
        uint64 quotient = value >> shift;
        uint64 mask = (uint64(1) << shift) - 1;
        uint64 remainder = value & mask;
        uint64 half = uint64(1) << (shift - 1);
        if (remainder > half || (remainder == half && (quotient & 1) != 0)) ++quotient;
        return quotient;
    }

    function _signedIntegerToIEEE(
        uint64 raw, uint256 width, uint256 precision, uint256 bias, uint256 fractionBits
    ) private pure returns (uint64) {
        uint64 signBit = width == 32 ? uint64(1) << 31 : uint64(1) << 63;
        uint64 widthMask = width == 32 ? uint64(type(uint32).max) : type(uint64).max;
        raw &= widthMask;
        bool negative = (raw & signBit) != 0;
        uint64 magnitude;
        unchecked { magnitude = negative ? ((~raw & widthMask) + 1) : raw; }
        if (magnitude == 0) return 0;
        uint256 exponent = _highestBit(magnitude);
        uint64 significand;
        if (exponent + 1 > precision) {
            significand = _roundRightEven(magnitude, exponent + 1 - precision);
        } else {
            significand = magnitude << (precision - exponent - 1);
        }
        if (significand == (uint64(1) << precision)) {
            significand >>= 1;
            ++exponent;
        }
        uint64 fractionMask = (uint64(1) << fractionBits) - 1;
        uint64 sign = negative ? uint64(1) << (fractionBits + (fractionBits == 23 ? 8 : 11)) : 0;
        return sign | (uint64(exponent + bias) << fractionBits) | (significand & fractionMask);
    }

    function _ieeeToSignedInteger(
        uint64 raw, uint256 exponentBits, uint256 fractionBits, uint256 targetBits
    ) private pure returns (uint64) {
        uint256 signShift = exponentBits + fractionBits;
        bool negative = ((raw >> signShift) & 1) != 0;
        uint64 fractionMask = (uint64(1) << fractionBits) - 1;
        uint64 fraction = raw & fractionMask;
        uint256 exponentMask = (uint256(1) << exponentBits) - 1;
        uint256 encodedExponent = (uint256(raw) >> fractionBits) & exponentMask;
        uint64 minimum = uint64(1) << (targetBits - 1);
        uint64 maximum = minimum - 1;
        if (encodedExponent == exponentMask) {
            if (fraction != 0) return 0;
            return negative ? minimum : maximum;
        }
        int256 exponent = encodedExponent == 0
            ? int256(1) - int256(exponentMask >> 1)
            : int256(encodedExponent) - int256(exponentMask >> 1);
        if (exponent < 0) return 0;
        if (exponent >= int256(targetBits - 1)) return negative ? minimum : maximum;
        uint64 significand = encodedExponent == 0
            ? fraction : ((uint64(1) << fractionBits) | fraction);
        uint64 magnitude = uint256(exponent) >= fractionBits
            ? significand << (uint256(exponent) - fractionBits)
            : significand >> (fractionBits - uint256(exponent));
        if (!negative) return magnitude;
        unchecked { return ~magnitude + 1; }
    }

    function _floatToDoubleBits(uint32 raw) private pure returns (uint64) {
        uint64 sign = (uint64(raw >> 31)) << 63;
        uint256 encodedExponent = (raw >> 23) & 0xff;
        uint64 fraction = uint64(raw & 0x7fffff);
        if (encodedExponent == 0xff) {
            if (fraction != 0) return 0x7ff8000000000000;
            return sign | 0x7ff0000000000000;
        }
        if (encodedExponent == 0) {
            if (fraction == 0) return sign;
            uint256 top = _highestBit(fraction);
            int256 exponent = int256(top) - 149;
            uint64 normalized = fraction << (52 - top);
            return sign | (uint64(uint256(exponent + 1023)) << 52)
                | (normalized & 0x000fffffffffffff);
        }
        // Add the binary64 bias before subtracting the binary32 bias. For
        // ordinary finite floats below 1.0, subtracting 127 first would
        // underflow Solidity's unsigned arithmetic even though the rebased
        // exponent is positive.
        return sign | (uint64(encodedExponent + 1023 - 127) << 52) | (fraction << 29);
    }

    function _doubleToFloatBits(uint64 raw) private pure returns (uint32) {
        uint32 sign = uint32(raw >> 63) << 31;
        uint256 encodedExponent = (raw >> 52) & 0x7ff;
        uint64 fraction = raw & 0x000fffffffffffff;
        if (encodedExponent == 0x7ff) {
            if (fraction != 0) return 0x7fc00000;
            return sign | 0x7f800000;
        }
        uint64 significand;
        int256 scale;
        if (encodedExponent == 0) {
            if (fraction == 0) return sign;
            significand = fraction;
            scale = -1074;
        } else {
            significand = (uint64(1) << 52) | fraction;
            scale = int256(encodedExponent) - 1023 - 52;
        }
        uint256 top = _highestBit(significand);
        int256 exponent = int256(top) + scale;
        if (exponent >= -126) {
            uint64 rounded = top > 23
                ? _roundRightEven(significand, top - 23)
                : significand << (23 - top);
            if (rounded == (uint64(1) << 24)) {
                rounded >>= 1;
                ++exponent;
            }
            if (exponent > 127) return sign | 0x7f800000;
            return sign | (uint32(uint256(exponent + 127)) << 23)
                | uint32(rounded & 0x7fffff);
        }
        int256 subnormalShift = scale + 149;
        uint64 subnormal = subnormalShift >= 0
            ? significand << uint256(subnormalShift)
            : _roundRightEven(significand, uint256(-subnormalShift));
        if (subnormal >= (uint64(1) << 23)) return sign | 0x00800000;
        return sign | uint32(subnormal);
    }

    function _compareIEEE(
        uint64 left, uint64 right, uint256 exponentBits, uint256 fractionBits, bool nanLow
    ) private pure returns (int8) {
        uint64 fractionMask = (uint64(1) << fractionBits) - 1;
        uint256 exponentMask = (uint256(1) << exponentBits) - 1;
        bool leftNaN = ((uint256(left) >> fractionBits) & exponentMask) == exponentMask
            && (left & fractionMask) != 0;
        bool rightNaN = ((uint256(right) >> fractionBits) & exponentMask) == exponentMask
            && (right & fractionMask) != 0;
        if (leftNaN || rightNaN) return nanLow ? int8(-1) : int8(1);
        uint64 signBit = uint64(1) << (exponentBits + fractionBits);
        uint64 magnitudeMask = signBit - 1;
        uint64 leftMagnitude = left & magnitudeMask;
        uint64 rightMagnitude = right & magnitudeMask;
        if (leftMagnitude == 0 && rightMagnitude == 0) return 0;
        if (left == right) return 0;
        bool leftNegative = (left & signBit) != 0;
        bool rightNegative = (right & signBit) != 0;
        if (leftNegative != rightNegative) return leftNegative ? int8(-1) : int8(1);
        if (!leftNegative) return leftMagnitude < rightMagnitude ? int8(-1) : int8(1);
        return leftMagnitude > rightMagnitude ? int8(-1) : int8(1);
    }

    function _newArrayPrimitive(uint8 atype) private pure returns (uint8) {
        if (atype == 4) return PRIMITIVE_BOOLEAN;
        if (atype == 5) return PRIMITIVE_CHAR;
        if (atype == 6) return PRIMITIVE_FLOAT;
        if (atype == 7) return PRIMITIVE_DOUBLE;
        if (atype == 8) return PRIMITIVE_BYTE;
        if (atype == 9) return PRIMITIVE_SHORT;
        if (atype == 10) return PRIMITIVE_INT;
        if (atype == 11) return PRIMITIVE_LONG;
        return 0;
    }

    function _normalizeInt(uint32 value, uint8 subtype) private pure returns (uint32) {
        if (subtype == PRIMITIVE_BYTE) return uint32(int32(int8(uint8(value))));
        if (subtype == PRIMITIVE_CHAR) return uint32(uint16(value));
        if (subtype == PRIMITIVE_SHORT) return uint32(int32(int16(uint16(value))));
        if (subtype == PRIMITIVE_BOOLEAN) return value & 1;
        return value; // I
    }

    function _normalizePackedInt(uint256 value, uint8 subtype) private pure returns (uint256) {
        return _packInt(_normalizeInt(uint32(_payload(value)), subtype));
    }

    function _packInt(uint32 value) private pure returns (uint256) {
        return (KIND_INT << KIND_SHIFT) | uint256(value);
    }

    function _packRef(uint32 handle) private pure returns (uint256) {
        return (KIND_REF << KIND_SHIFT) | uint256(handle);
    }

    function _packLong(uint64 value) private pure returns (uint256) {
        return (KIND_LONG << KIND_SHIFT) | uint256(value);
    }

    function _packFloat(uint32 value) private pure returns (uint256) {
        return (KIND_FLOAT << KIND_SHIFT) | uint256(value);
    }

    function _packDouble(uint64 value) private pure returns (uint256) {
        return (KIND_DOUBLE << KIND_SHIFT) | uint256(value);
    }

    function _payload(uint256 value) private pure returns (uint256) {
        return uint64(value);
    }

    function _valueKind(uint256 value) private pure returns (uint256) {
        return value >> KIND_SHIFT;
    }

    function _requireKind(uint256 value, uint256 wanted, uint256 pc) private pure {
        if (_valueKind(value) != wanted) revert BytecodeError(14, pc);
    }

    function _requireIntPair(uint256[] memory stack, uint256 sp, uint256 pc) private pure {
        _requireKind(stack[sp - 2], KIND_INT, pc);
        _requireKind(stack[sp - 1], KIND_INT, pc);
    }

    function _requireLongPair(uint256[] memory stack, uint256 sp, uint256 pc) private pure {
        _requireKind(stack[sp - 2], KIND_LONG, pc);
        _requireKind(stack[sp - 1], KIND_LONG, pc);
    }

    function _heapKindAt(uint256 metadata) private pure returns (uint8) {
        if (metadata == 0) return 0;
        return (metadata & HEAP_OBJECT_MARKER) != 0 ? HEAP_OBJECT : HEAP_ARRAY;
    }

    function _requireHeapKind(
        uint256 handle, uint256[] memory heapKinds, uint256 nextHandle, uint8 wanted, uint256 pc
    ) private pure {
        if (handle == 0 || handle > nextHandle
            || _heapKindAt(heapKinds[handle]) != wanted) {
            revert ReferenceError(1, pc);
        }
    }

    function _validatePackedRef(
        uint256 value, uint256[] memory heapKinds, uint256 nextHandle, uint256 pc
    ) private pure {
        _requireKind(value, KIND_REF, pc);
        uint256 handle = _payload(value);
        if (handle != 0 && (handle > nextHandle || _heapKindAt(heapKinds[handle]) == 0)) {
            revert ReferenceError(1, pc);
        }
    }

    function _ensureStringLayout(
        ExceptionArena memory arena, ClassInfo[] memory classes, uint256 stringClass,
        uint256[] memory parentLinks, uint8[] memory hierarchyState
    ) private pure returns (bool fits) {
        if (arena.stringLayoutLoaded) return true;
        if (stringClass < classes.length && classes[stringClass].cp.length == 0
            && classes[stringClass].data.length != 0) {
            classes[stringClass] = _parseBundleClass(classes[stringClass].data);
        }
        if (stringClass >= classes.length
            || !_isNamedClass(classes[stringClass], bytes("java/lang/String"))) {
            revert BootstrapProfileError(1, 0);
        }
        arena.stringClass = stringClass;
        _validateHierarchy(classes, stringClass, parentLinks, hierarchyState);
        ClassInfo memory c = classes[stringClass];
        uint256 valuePlusOne;
        uint256 hashPlusOne;
        for (uint256 i = 0; i < c.fields.length; ++i) {
            FieldInfo memory field = c.fields[i];
            (uint256 no, uint256 nn) = _utf(c.cp[field.nameIndex]);
            (uint256 doff, uint256 dn) = _utf(c.cp[field.descriptorIndex]);
            if (_equalsLiteral(c.data, no, nn, bytes("value"))
                && _equalsLiteral(c.data, doff, dn, bytes("[C"))) valuePlusOne = i + 1;
            if (_equalsLiteral(c.data, no, nn, bytes("hash"))
                && _equalsLiteral(c.data, doff, dn, bytes("I"))) hashPlusOne = i + 1;
        }
        if (valuePlusOne == 0 || hashPlusOne == 0) revert BootstrapProfileError(1, 0);
        uint256 fieldCount = _instanceFieldCount(
            classes, stringClass, parentLinks, ROOT_FAULT_SENTINEL
        );
        // An otherwise valid inherited layout can exceed the ordinary-object quota.
        // Report a failed allocation, not malformed bootstrap metadata, and avoid
        // materializing an over-limit default array before the caller raises OOM.
        if (fieldCount > MAX_OBJECT_FIELDS) return false;
        arena.stringValueOffset = _instanceFieldOffset(
            classes, stringClass, stringClass, valuePlusOne - 1,
            parentLinks, ROOT_FAULT_SENTINEL
        );
        arena.stringHashOffset = _instanceFieldOffset(
            classes, stringClass, stringClass, hashPlusOne - 1,
            parentLinks, ROOT_FAULT_SENTINEL
        );
        arena.stringDefaults = _objectFieldDefaults(classes, stringClass, fieldCount, parentLinks);
        arena.stringLayoutLoaded = true;
        return true;
    }

    function _stringUnits(
        ExceptionArena memory arena, uint256 handle, uint256 pc
    ) private pure returns (uint64[] memory units) {
        if (handle == 0 || handle > arena.nextHandle
            || _heapKindAt(arena.heap.metadata[handle]) != HEAP_OBJECT
            || arena.heap.classes[handle] != arena.stringClass
            || arena.heap.objectHeap[handle].length != arena.stringDefaults.length) {
            revert BytecodeError(14, pc);
        }
        uint256 packedBacking = arena.heap.objectHeap[handle][arena.stringValueOffset];
        if (_valueKind(packedBacking) != KIND_REF) revert BytecodeError(14, pc);
        uint256 backing = _payload(packedBacking);
        if (backing == 0 || backing > arena.nextHandle
            || _heapKindAt(arena.heap.metadata[backing]) != HEAP_ARRAY
            || arena.heap.ranks[backing] != 1
            || arena.heap.metadata[backing] != PRIMITIVE_CHAR) revert BytecodeError(14, pc);
        units = arena.heap.arrayHeap[backing];
        for (uint256 i = 0; i < units.length; ++i) {
            if (units[i] > 0xffff) revert BytecodeError(14, pc);
        }
    }

    function _runStringNative(
        uint8 binding, Frame memory f, uint256 base, uint256 receiverHandle,
        ExceptionArena memory arena, uint256 pc
    ) private pure returns (uint256 value) {
        uint64[] memory left = _stringUnits(arena, receiverHandle, pc);
        if (binding == 1) return _packInt(uint32(left.length));
        if (binding == 2) return _packInt(left.length == 0 ? 1 : 0);
        if (binding == 3) {
            int32 index = int32(uint32(_payload(f.stack[base + 1])));
            if (index < 0 || uint256(uint32(index)) >= left.length) {
                revert StringProfileError(2, pc);
            }
            return _packInt(uint32(left[uint256(uint32(index))]));
        }
        if (binding == 4) {
            uint256 other = _payload(f.stack[base + 1]);
            if (other == 0 || other > arena.nextHandle
                || _heapKindAt(arena.heap.metadata[other]) != HEAP_OBJECT
                || arena.heap.classes[other] != arena.stringClass) return _packInt(0);
            return _packInt(_sameStringUnits(left, _stringUnits(arena, other, pc)) ? 1 : 0);
        }
        if (binding == 5) {
            uint256 cached = arena.heap.objectHeap[receiverHandle][arena.stringHashOffset];
            if (_valueKind(cached) != KIND_INT) revert BytecodeError(14, pc);
            uint32 hash = uint32(_payload(cached));
            if (hash == 0 && left.length != 0) {
                hash = _stringHash(left);
                arena.heap.objectHeap[receiverHandle][arena.stringHashOffset] = _packInt(hash);
            }
            return _packInt(hash);
        }
        if (binding == 6) return _packRef(uint32(receiverHandle));
        if (binding == 7) {
            uint256 other = _payload(f.stack[base + 1]);
            uint64[] memory right = _stringUnits(arena, other, pc);
            uint256 common = left.length < right.length ? left.length : right.length;
            for (uint256 i = 0; i < common; ++i) {
                if (left[i] != right[i]) {
                    int32 difference = int32(uint32(left[i])) - int32(uint32(right[i]));
                    return _packInt(uint32(difference));
                }
            }
            int32 lengthDifference = int32(uint32(left.length)) - int32(uint32(right.length));
            return _packInt(uint32(lengthDifference));
        }
        revert StringProfileError(1, pc); // deferred subSequence
    }

    function _internStringReceiver(
        ExceptionArena memory arena, uint256 receiverHandle, uint256 pc
    ) private pure returns (uint256 ref, bool oom) {
        uint64[] memory units = _stringUnits(arena, receiverHandle, pc);
        uint32 hash = _stringHash(units);
        for (uint256 i; i < arena.internCount; ++i) {
            if (arena.internHashes[i] == hash
                && _sameStringUnits(
                    units, _stringUnits(arena, arena.internHandles[i], pc)
                )) return (arena.internHandles[i], false);
        }
        // Hits above remain legal at the cap. A miss has no partial insertion and
        // is reported by the caller as the ordinary arena OOM kind 7.
        if (arena.internCount == MAX_INTERNED_STRINGS) return (0, true);
        if (arena.internHandles.length == 0) {
            arena.internHandles = new uint256[](MAX_INTERNED_STRINGS);
            arena.internHashes = new uint32[](MAX_INTERNED_STRINGS);
        }
        // Canonical order is by authoritative heap handle, including a receiver
        // allocated before a literal which entered the pool first.
        uint256 at = arena.internCount;
        while (at != 0 && arena.internHandles[at - 1] > receiverHandle) {
            arena.internHandles[at] = arena.internHandles[at - 1];
            arena.internHashes[at] = arena.internHashes[at - 1];
            --at;
        }
        arena.internHandles[at] = receiverHandle;
        arena.internHashes[at] = hash;
        ++arena.internCount;
        return (receiverHandle, false);
    }

    function _stringHash(uint64[] memory units) private pure returns (uint32 hash) {
        unchecked {
            for (uint256 i = 0; i < units.length; ++i) {
                hash = hash * 31 + uint32(units[i]);
            }
        }
    }

    function _sameStringUnits(uint64[] memory first, uint64[] memory second)
        private pure returns (bool)
    {
        if (first.length != second.length) return false;
        for (uint256 i = 0; i < first.length; ++i) {
            if (first[i] != second[i]) return false;
        }
        return true;
    }

    function _validateClassLiteralOperand(ClassInfo memory c, uint256 cpIndex, uint256 pc)
        private pure
    {
        if (cpIndex == 0 || cpIndex >= c.cp.length || uint8(c.cp[cpIndex]) != 7) {
            revert BytecodeError(13, pc);
        }
        uint256 nameIndex = (c.cp[cpIndex] >> 8) & 0xffff;
        if (nameIndex == 0 || nameIndex >= c.cp.length || uint8(c.cp[nameIndex]) != 1) {
            revert BytecodeError(13, pc);
        }
        (uint256 off, uint256 n) = _utf(c.cp[nameIndex]);
        // Arrays and primitive mirrors are explicitly outside this copy profile.
        if (!_validInternalName(c.data, off, n)) revert BytecodeError(13, pc);
    }

    function _ensureClassLayout(
        ExceptionArena memory arena, ClassInfo[] memory classes,
        uint256[] memory parentLinks, uint8[] memory hierarchyState
    ) private pure returns (bool fits) {
        if (arena.classLayoutLoaded) return true;
        uint256 ci = arena.classClass;
        if (ci >= classes.length || !_isNamedClass(classes[ci], bytes("java/lang/Class"))) {
            revert BootstrapProfileError(2, 0);
        }
        _validateHierarchy(classes, ci, parentLinks, hierarchyState);
        uint256 namePlusOne;
        for (uint256 i; i < classes[ci].fields.length; ++i) {
            FieldInfo memory field = classes[ci].fields[i];
            (uint256 no, uint256 nn) = _utf(classes[ci].cp[field.nameIndex]);
            (uint256 doff, uint256 dn) = _utf(classes[ci].cp[field.descriptorIndex]);
            if (_equalsLiteral(classes[ci].data, no, nn, bytes("name"))
                && _equalsLiteral(classes[ci].data, doff, dn, bytes("Ljava/lang/String;"))) {
                if (namePlusOne != 0) revert BootstrapProfileError(2, 0);
                namePlusOne = i + 1;
            }
        }
        uint256 fields = _instanceFieldCount(classes, ci, parentLinks, ROOT_FAULT_SENTINEL);
        if (namePlusOne == 0 || fields > MAX_OBJECT_FIELDS) revert BootstrapProfileError(2, 0);
        arena.classNameOffset = _instanceFieldOffset(
            classes, ci, ci, namePlusOne - 1, parentLinks, ROOT_FAULT_SENTINEL
        );
        arena.classDefaults = _objectFieldDefaults(classes, ci, fields, parentLinks);
        arena.classLayoutLoaded = true;
        return true;
    }

    function _classNameUnits(ClassInfo memory c) private pure returns (uint64[] memory units) {
        // Internal names are already structural-checked.  Classfile names used by
        // this profile are MUTF-8; reject malformed encodings rather than inventing
        // a host-decoded spelling, and change '/' only after decoding UTF-16 units.
        uint256 at = c.thisNameOffset;
        uint256 end = at + c.thisNameLength;
        uint256 count;
        while (at < end) {
            uint8 first = uint8(c.data[at]);
            if (first >= 1 && first <= 0x7f) ++at;
            else if (first >= 0xc0 && first <= 0xdf && end - at >= 2
                && (uint8(c.data[at + 1]) & 0xc0) == 0x80) at += 2;
            else if (first >= 0xe0 && first <= 0xef && end - at >= 3
                && (uint8(c.data[at + 1]) & 0xc0) == 0x80 && (uint8(c.data[at + 2]) & 0xc0) == 0x80) at += 3;
            else revert BootstrapProfileError(2, 0);
            ++count;
        }
        units = new uint64[](count); at = c.thisNameOffset; uint256 out;
        while (at < end) {
            uint8 first = uint8(c.data[at]); uint256 value;
            if (first <= 0x7f) { value = first; ++at; }
            else if (first <= 0xdf) { value = (uint256(first & 0x1f) << 6) | uint8(c.data[at + 1]) & 0x3f; at += 2; }
            else { value = (uint256(first & 0x0f) << 12) | (uint256(uint8(c.data[at + 1]) & 0x3f) << 6) | (uint8(c.data[at + 2]) & 0x3f); at += 3; }
            units[out++] = value == 0x2f ? 0x2e : uint64(value);
        }
    }

    function _classMirrorMatches(ExceptionArena memory arena, uint256 h, uint64[] memory name)
        private pure returns (bool)
    {
        if (_heapKindAt(arena.heap.metadata[h]) != HEAP_OBJECT || arena.heap.classes[h] != arena.classClass
            || arena.heap.objectHeap[h].length != arena.classDefaults.length) return false;
        uint256 value = arena.heap.objectHeap[h][arena.classNameOffset];
        if (_valueKind(value) != KIND_REF || _payload(value) == 0) return false;
        return _sameStringUnits(name, _stringUnits(arena, _payload(value), ROOT_FAULT_SENTINEL));
    }

    function _classLiteralMirror(
        ExceptionArena memory arena, ClassInfo[] memory classes, uint256 caller, uint256 cpIndex,
        uint256[] memory parentLinks, uint8[] memory hierarchyState, uint256 pc
    ) private pure returns (uint256 mirror, bool oom) {
        _validateClassLiteralOperand(classes[caller], cpIndex, pc);
        uint256 nameIndex = (classes[caller].cp[cpIndex] >> 8) & 0xffff;
        (uint256 off, uint256 n) = _utf(classes[caller].cp[nameIndex]);
        (bool found, uint256 target) = _findClass(classes, classes[caller].data, off, n);
        if (!found) _missingClass(0x100c, pc, classes[caller].data, off, n);
        if (!_classAccessible(classes[caller], classes[target])) revert ReferenceError(2, pc);
        uint64[] memory name = _classNameUnits(classes[target]);
        if (!_ensureClassLayout(arena, classes, parentLinks, hierarchyState)) return (0, true);
        for (uint256 h = 1; h <= arena.nextHandle; ++h) {
            if (_classMirrorMatches(arena, h, name)) return (h, false);
        }
        uint256 fields = arena.classDefaults.length;
        // Reserve the mirror object before the String allocation.  A String miss
        // consumes one object/two handles; the checked reserve makes the whole
        // literal allocation atomic with respect to ordinary quotas.
        if (arena.ordinaryObjectCount >= MAX_OBJECTS || fields > MAX_OBJECT_FIELDS
            || fields > MAX_OBJECT_FIELD_SLOTS - arena.ordinaryFieldSlots
            || arena.nextHandle >= MAX_HANDLES) return (0, true);
        (uint256 nameRef, bool stringOOM) = _internStringUnits(
            arena, classes, name, parentLinks, hierarchyState, 1, fields
        );
        if (stringOOM) return (0, true);
        _ensureExceptionRegistry(arena, classes, parentLinks, hierarchyState);
        uint256 h = arena.nextHandle + 1;
        arena.nextHandle = h;
        ++arena.ordinaryObjectCount; arena.ordinaryFieldSlots += fields;
        arena.heap.metadata[h] = HEAP_OBJECT_MARKER;
        arena.heap.classes[h] = arena.classClass;
        arena.heap.objectHeap[h] = _copyExceptionDefaults(arena.classDefaults);
        arena.heap.objectHeap[h][arena.classNameOffset] = _packRef(uint32(nameRef));
        return (h, false);
    }

    function _validateClassMirrors(Program memory p, RuntimeState memory s) private pure {
        uint256 ci = s.arena.classClass;
        if (ci >= p.classes.length || !_isNamedClass(p.classes[ci], bytes("java/lang/Class"))) {
            revert LC0StateError(7, 0);
        }
        bool any;
        for (uint256 h = 1; h <= s.nextHandle; ++h) {
            if (_heapKindAt(s.arena.heap.metadata[h]) != HEAP_OBJECT || s.arena.heap.classes[h] != ci) continue;
            any = true;
        }
        if (!any) return;
        if (!_ensureClassLayout(s.arena, p.classes, s.parentLinks, s.hierarchyState)) revert LC0StateError(7, 0);
        bool[] memory targets = new bool[](p.classes.length);
        for (uint256 h = 1; h <= s.nextHandle; ++h) {
            if (_heapKindAt(s.arena.heap.metadata[h]) != HEAP_OBJECT || s.arena.heap.classes[h] != ci) continue;
            bool matched;
            for (uint256 target; target < p.classes.length; ++target) {
                uint64[] memory name = _classNameUnits(p.classes[target]);
                if (!_classMirrorMatches(s.arena, h, name)) continue;
                if (matched || targets[target]) revert LC0StateError(7, 0);
                targets[target] = true; matched = true;
            }
            if (!matched) revert LC0StateError(7, 0);
        }
    }

    /// Strict MUTF-8 has one canonical encoding for every non-NUL UTF-16 unit and
    /// the sole c080 encoding for NUL, so validated byte equality would be sound.
    /// The pool nevertheless compares decoded length/content after its hash lookup.
    function _internStringConstant(
        ExceptionArena memory arena, ClassInfo[] memory classes, uint256 classIndex,
        uint256 cpIndex, uint256[] memory parentLinks, uint8[] memory hierarchyState
    ) private pure returns (uint256 ref, bool oom) {
        if (arena.stringRefs[classIndex].length == 0) arena.stringRefs[classIndex] = new uint256[](classes[classIndex].cp.length);
        ref = arena.stringRefs[classIndex][cpIndex];
        if (ref != 0) return (ref, false);
        uint64[] memory units = _decodeStringConstant(classes[classIndex], classIndex, cpIndex);
        (ref, oom) = _internStringUnits(arena, classes, units, parentLinks, hierarchyState, 0, 0);
        if (!oom) arena.stringRefs[classIndex][cpIndex] = ref;
    }

    function _internStringUnits(
        ExceptionArena memory arena, ClassInfo[] memory classes, uint64[] memory units,
        uint256[] memory parentLinks, uint8[] memory hierarchyState,
        uint256 reserveObjects, uint256 reserveFields
    ) private pure returns (uint256 ref, bool oom) {
        if (!_ensureStringLayout(
            arena, classes, arena.stringClass, parentLinks, hierarchyState
        )) return (0, true);
        uint32 hash = _stringHash(units);
        for (uint256 i = 0; i < arena.internCount; ++i) {
            if (arena.internHashes[i] != hash) continue;
            uint256 candidate = arena.internHandles[i];
            uint256 backing = _payload(arena.heap.objectHeap[candidate][arena.stringValueOffset]);
            if (_sameStringUnits(units, arena.heap.arrayHeap[backing])) {
                return (candidate, false);
            }
        }
        uint256 fields = arena.stringDefaults.length;
        // The complete miss is checked before any guest handle, quota counter,
        // heap cell, or pool entry is published. Pool hits above remain available
        // even when every ordinary quota is exhausted.
        if (arena.internCount == MAX_INTERNED_STRINGS
            || arena.ordinaryObjectCount > MAX_OBJECTS - 1 - reserveObjects
            || arena.ordinaryArrayCount == MAX_ARRAYS
            || units.length > MAX_ARRAY_LENGTH
            || units.length > MAX_ARRAY_ELEMENTS - arena.ordinaryArrayElements
            || fields > MAX_OBJECT_FIELDS
            || fields > MAX_OBJECT_FIELD_SLOTS - arena.ordinaryFieldSlots
            || reserveFields > MAX_OBJECT_FIELD_SLOTS - arena.ordinaryFieldSlots - fields
            || arena.nextHandle > MAX_HANDLES - 2 - reserveObjects) return (0, true);

        _ensureExceptionRegistry(arena, classes, parentLinks, hierarchyState);
        if (arena.heap.arrayHeap.length == 0) {
            arena.heap.arrayHeap = new uint64[][](MAX_HANDLES + 1);
            arena.heap.ranks = new uint8[](MAX_HANDLES + 1);
        }
        if (arena.internHandles.length == 0) {
            arena.internHandles = new uint256[](MAX_INTERNED_STRINGS);
            arena.internHashes = new uint32[](MAX_INTERNED_STRINGS);
        }
        uint256 arrayHandle = arena.nextHandle + 1;
        uint256 objectHandle = arrayHandle + 1;
        arena.heap.ranks[arrayHandle] = 1;
        arena.heap.metadata[arrayHandle] = PRIMITIVE_CHAR;
        // Transfer the decoder's sole full-sized UTF-16 buffer into the ordinary array heap.
        arena.heap.arrayHeap[arrayHandle] = units;
        arena.heap.metadata[objectHandle] = HEAP_OBJECT_MARKER;
        arena.heap.classes[objectHandle] = arena.stringClass;
        arena.heap.objectHeap[objectHandle] = _copyExceptionDefaults(arena.stringDefaults);
        arena.heap.objectHeap[objectHandle][arena.stringValueOffset] = _packRef(uint32(arrayHandle));
        arena.heap.objectHeap[objectHandle][arena.stringHashOffset] = _packInt(0);
        arena.nextHandle = objectHandle;
        ++arena.ordinaryArrayCount;
        ++arena.ordinaryObjectCount;
        arena.ordinaryArrayElements += units.length;
        arena.ordinaryFieldSlots += fields;
        arena.internHandles[arena.internCount] = objectHandle;
        arena.internHashes[arena.internCount] = hash;
        ++arena.internCount;
        return (objectHandle, false);
    }

    function _classNameBytes(ClassInfo memory c) private pure returns (bytes memory name) {
        name = new bytes(c.thisNameLength);
        for (uint256 i; i < c.thisNameLength; ++i) {
            name[i] = c.data[c.thisNameOffset + i];
        }
    }

    function _exactKnownKind(ExceptionArena memory arena, uint256 dynamicClass)
        private pure returns (uint256)
    {
        for (uint256 kind = 1; kind <= 12; ++kind) {
            if (arena.classesByKind[kind] == dynamicClass) return kind;
        }
        return 0;
    }

    // Resolve pinned VFS fields with their exact computational type. This is
    // deliberately separate from Throwable's REF-only helper below: adding the
    // stream handle:I must not weaken canonical Throwable reference validation.
    function _canonicalVFSFieldOffset(
        ClassInfo[] memory classes, uint256 owner, bytes memory name,
        bytes memory descriptor, uint256 expectedKind, uint256[] memory parentLinks, uint256 pc
    ) private pure returns (uint256 offset) {
        if (classes[owner].cp.length == 0) {
            classes[owner] = _parseBundleClass(classes[owner].data);
        }
        uint256 foundPlusOne;
        for (uint256 i; i < classes[owner].fields.length; ++i) {
            FieldInfo memory field = classes[owner].fields[i];
            (uint256 no, uint256 nn) = _utf(classes[owner].cp[field.nameIndex]);
            (uint256 doff, uint256 dn) = _utf(classes[owner].cp[field.descriptorIndex]);
            if (!_equalsLiteral(classes[owner].data, no, nn, name)
                || !_equalsLiteral(classes[owner].data, doff, dn, descriptor)) continue;
            if (foundPlusOne != 0 || (field.accessFlags & 0x0008) != 0
                || _fieldKind(classes[owner], field) != expectedKind) {
                revert VFS0aProfileError(4, pc);
            }
            foundPlusOne = i + 1;
        }
        if (foundPlusOne == 0) revert VFS0aProfileError(4, pc);
        return _instanceFieldOffset(
            classes, owner, owner, foundPlusOne - 1, parentLinks, pc
        );
    }

    // Resolve pinned private Throwable fields from their declaring owner/name/descriptor;
    // no host-supplied slot number or dynamic-class coincidence is trusted.
    function _canonicalFieldOffset(
        ClassInfo[] memory classes, uint256 owner, bytes memory name,
        bytes memory descriptor, uint256[] memory parentLinks, uint256 pc
    ) private pure returns (uint256 offset) {
        if (classes[owner].cp.length == 0) {
            classes[owner] = _parseBundleClass(classes[owner].data);
        }
        uint256 foundPlusOne;
        for (uint256 i; i < classes[owner].fields.length; ++i) {
            FieldInfo memory field = classes[owner].fields[i];
            (uint256 no, uint256 nn) = _utf(classes[owner].cp[field.nameIndex]);
            (uint256 doff, uint256 dn) = _utf(classes[owner].cp[field.descriptorIndex]);
            if (!_equalsLiteral(classes[owner].data, no, nn, name)
                || !_equalsLiteral(classes[owner].data, doff, dn, descriptor)) continue;
            if (foundPlusOne != 0 || (field.accessFlags & 0x0008) != 0
                || _fieldKind(classes[owner], field) != KIND_REF) {
                revert ThrowableProfileError(2, owner, i);
            }
            foundPlusOne = i + 1;
        }
        if (foundPlusOne == 0) revert ThrowableProfileError(2, owner, 0);
        return _instanceFieldOffset(
            classes, owner, owner, foundPlusOne - 1, parentLinks, pc
        );
    }

    function _initializeVMThrowableFields(
        ExceptionArena memory arena, ClassInfo[] memory classes, uint256 dynamicClass,
        uint256 ref, uint256[] memory parentLinks, uint256 pc
    ) private pure {
        uint256 messageOffset = _canonicalFieldOffset(
            classes, arena.throwableClass, bytes("detailMessage"), bytes("Ljava/lang/String;"),
            parentLinks, pc
        );
        uint256 causeOffset = _canonicalFieldOffset(
            classes, arena.throwableClass, bytes("cause"), bytes("Ljava/lang/Throwable;"),
            parentLinks, pc
        );
        uint256[] memory fields = arena.heap.objectHeap[ref];
        if (messageOffset >= fields.length || causeOffset >= fields.length
            || !_typeAssignable(classes, dynamicClass, arena.throwableClass, parentLinks)) {
            revert ThrowableProfileError(2, dynamicClass, 0);
        }
        fields[messageOffset] = _packRef(0);
        fields[causeOffset] = _packRef(uint32(ref));
    }

    function _storeVMWrapperException(
        ExceptionArena memory arena, ClassInfo[] memory classes, uint256 wrapperRef,
        uint256 causeRef, uint256[] memory parentLinks, uint256 pc
    ) private pure {
        uint256 wrapperClass = arena.classesByKind[3];
        uint256 offset = _canonicalFieldOffset(
            classes, wrapperClass, bytes("exception"), bytes("Ljava/lang/Throwable;"),
            parentLinks, pc
        );
        uint256[] memory fields = arena.heap.objectHeap[wrapperRef];
        if (offset >= fields.length || causeRef == 0 || causeRef >= wrapperRef
            || !_typeAssignable(classes, arena.heap.classes[causeRef], arena.throwableClass,
                parentLinks)
            || _typeAssignable(classes, arena.heap.classes[causeRef], arena.errorClass,
                parentLinks)) revert ThrowableProfileError(2, wrapperClass, 0);
        fields[offset] = _packRef(uint32(causeRef));
    }

    function _configureExceptionClasses(
        ExceptionArena memory arena, uint256 at
    ) private pure {
        arena.throwableClass = at;
        arena.errorClass = at + 1;
        arena.classesByKind[1] = at + 12; // ArithmeticException
        arena.classesByKind[2] = at + 3;  // StackOverflowError
        arena.classesByKind[3] = at + 6;  // ExceptionInInitializerError
        arena.classesByKind[4] = at + 14; // NegativeArraySizeException
        arena.classesByKind[5] = at + 18; // ArrayIndexOutOfBoundsException
        arena.classesByKind[6] = at + 13; // NullPointerException
        arena.classesByKind[7] = at + 4;  // OutOfMemoryError
        arena.classesByKind[8] = at + 15; // ClassCastException
        arena.classesByKind[9] = at + 16; // ArrayStoreException
        arena.classesByKind[10] = at + 7; // IncompatibleClassChangeError
        arena.classesByKind[11] = at + 9; // AbstractMethodError
        arena.classesByKind[12] = at + 8; // NoClassDefFoundError
    }

    function _ensureExceptionRegistry(
        ExceptionArena memory arena, ClassInfo[] memory classes,
        uint256[] memory parentLinks, uint8[] memory hierarchyState
    ) private pure {
        if (arena.heap.metadata.length != 0) return;
        uint256 oomClass = arena.classesByKind[7];
        if (classes[oomClass].cp.length == 0) {
            classes[oomClass] = _parseBundleClass(classes[oomClass].data);
        }
        arena.heap.objectHeap = new uint256[][](MAX_HANDLES + 1);
        arena.heap.metadata = new uint256[](MAX_HANDLES + 1);
        arena.heap.classes = new uint256[](MAX_HANDLES + 1);
        arena.fieldDefaults = new uint256[][](classes.length);
        arena.layoutsLoaded = new bool[](classes.length);
        _validateHierarchy(classes, arena.classesByKind[7], parentLinks, hierarchyState);
        uint256 fields = _instanceFieldCount(
            classes, arena.classesByKind[7], parentLinks, ROOT_FAULT_SENTINEL
        );
        if (fields > MAX_EXCEPTION_FIELD_SLOTS) revert ObjectError(2, ROOT_FAULT_SENTINEL);
        arena.nextHandle = 1;
        arena.emergencyRef = 1;
        arena.fieldSlots = fields;
        arena.heap.metadata[1] = HEAP_OBJECT_MARKER | 7;
        arena.heap.classes[1] = arena.classesByKind[7];
        arena.fieldDefaults[oomClass] = _objectFieldDefaults(
            classes, oomClass, fields, parentLinks
        );
        arena.layoutsLoaded[oomClass] = true;
        arena.heap.objectHeap[1] = _copyExceptionDefaults(arena.fieldDefaults[oomClass]);
        _initializeVMThrowableFields(
            arena, classes, oomClass, 1, parentLinks, ROOT_FAULT_SENTINEL
        );
    }

    function _copyExceptionDefaults(uint256[] memory defaults)
        private pure returns (uint256[] memory values)
    {
        values = new uint256[](defaults.length);
        // Plain bounded value cells; Cancun MCOPY preserves every tag/bit and
        // copies into a distinct allocation (no shared mutable default object).
        assembly ("memory-safe") {
            mcopy(add(values, 32), add(defaults, 32), mul(mload(defaults), 32))
        }
    }

    function _raiseJava(
        uint256 kind, uint256 faultPC, ExceptionArena memory arena,
        ClassInfo[] memory classes, uint256[][] memory objectHeap,
        uint256[] memory heapKinds, uint256[] memory heapClasses,
        uint256[] memory exceptionKinds, uint256[] memory parentLinks,
        uint8[] memory hierarchyState, uint256 nextHandle
    ) private pure returns (uint256) {
        _ensureExceptionRegistry(arena, classes, parentLinks, hierarchyState);
        objectHeap = arena.heap.objectHeap;
        heapKinds = arena.heap.metadata;
        heapClasses = arena.heap.classes;
        exceptionKinds = arena.heap.metadata;
        if (nextHandle < arena.nextHandle) nextHandle = arena.nextHandle;
        uint256 dynamicClass = arena.classesByKind[kind];
        if (classes[dynamicClass].cp.length == 0) {
            classes[dynamicClass] = _parseBundleClass(classes[dynamicClass].data);
        }
        // A loaded arena layout also certifies its immutable class/interface
        // closure. Avoid allocating traversal scratch again for every raise.
        if (!arena.layoutsLoaded[dynamicClass]) {
            _validateHierarchy(classes, dynamicClass, parentLinks, hierarchyState);
        }
        uint256 fields = arena.layoutsLoaded[dynamicClass]
            ? arena.fieldDefaults[dynamicClass].length
            : _instanceFieldCount(classes, dynamicClass, parentLinks, faultPC);
        if (arena.objectCount == MAX_EXCEPTION_OBJECTS
            || fields > MAX_EXCEPTION_FIELD_SLOTS - arena.fieldSlots) {
            arena.pending = PendingException(true, 7, arena.emergencyRef, faultPC);
            return nextHandle;
        }
        if (nextHandle >= MAX_HANDLES) {
            arena.pending = PendingException(true, 7, arena.emergencyRef, faultPC);
            return nextHandle;
        }
        ++nextHandle;
        arena.nextHandle = nextHandle;
        ++arena.objectCount;
        arena.fieldSlots += fields;
        heapClasses[nextHandle] = dynamicClass;
        exceptionKinds[nextHandle] = HEAP_OBJECT_MARKER | kind;
        if (!arena.layoutsLoaded[dynamicClass]) {
            arena.fieldDefaults[dynamicClass] = _objectFieldDefaults(
                classes, dynamicClass, fields, parentLinks
            );
            arena.layoutsLoaded[dynamicClass] = true;
        }
        // Private immutable templates, never aliases of mutable guest objects.
        objectHeap[nextHandle] = _copyExceptionDefaults(arena.fieldDefaults[dynamicClass]);
        _initializeVMThrowableFields(
            arena, classes, dynamicClass, nextHandle, parentLinks, faultPC
        );
        arena.pending = PendingException(true, kind, nextHandle, faultPC);
        return nextHandle;
    }

    function _resolveCatchClass(
        ClassInfo[] memory classes, uint256 currentClass, Selected memory s,
        uint256 entryIndex, uint256[] memory parentLinks, uint8[] memory hierarchyState,
        uint256 throwableClass
    ) private pure returns (uint256 resolved) {
        uint256 cached = s.handlerClassesPlusOne[entryIndex];
        if (cached != 0) return cached - 1;
        ClassInfo memory current = classes[currentClass];
        uint256 cpIndex = s.handlerCatchTypes[entryIndex];
        uint256 nameIndex = (current.cp[cpIndex] >> 8) & 0xffff;
        (uint256 off, uint256 n) = _utf(current.cp[nameIndex]);
        (bool found, uint256 target) = _findClass(classes, current.data, off, n);
        if (!found) revert HandlerError(5, currentClass, s.methodIndex, entryIndex);
        if (target != currentClass && !_classAccessible(current, classes[target])) {
            revert HandlerError(9, currentClass, s.methodIndex, entryIndex);
        }
        _validateHierarchy(classes, target, parentLinks, hierarchyState);
        if (_isInterface(classes[target])
            || !_objectIsClass(target, throwableClass, parentLinks)) {
            revert HandlerError(6, currentClass, s.methodIndex, entryIndex);
        }
        s.handlerClassesPlusOne[entryIndex] = target + 1;
        return target;
    }

    function _poisonAliases(Frame memory caller, uint256 handle) private pure {
        for (uint256 i = 0; i < caller.locals.length; ++i) {
            if (caller.initialized[i] && _payload(caller.locals[i]) == handle
                && _valueKind(caller.locals[i]) == KIND_UNINIT) {
                caller.initialized[i] = false;
                caller.locals[i] = 0;
            }
        }
        for (uint256 i = 0; i < caller.sp; ++i) {
            if (_payload(caller.stack[i]) == handle
                && _valueKind(caller.stack[i]) == KIND_UNINIT) caller.stack[i] = 0;
        }
    }

    function _push(uint256[] memory stack, uint256 sp, uint256 value, uint256 pc)
        private
        pure
        returns (uint256)
    {
        uint256 words = _stackWords(stack, sp);
        uint256 added = _isCategory2Kind(_valueKind(value)) ? 2 : 1;
        if (words > stack.length || added > stack.length - words) revert BytecodeError(9, pc);
        stack[sp] = value;
        return sp + 1;
    }

    function _stackWords(uint256[] memory stack, uint256 sp) private pure returns (uint256 words) {
        for (uint256 i = 0; i < sp; ++i) {
            words += _isCategory2Kind(_valueKind(stack[i])) ? 2 : 1;
        }
    }

    function _isCategory1(uint256 value) private pure returns (bool) {
        uint256 kind = _valueKind(value);
        return kind == KIND_INT || kind == KIND_REF || kind == KIND_UNINIT
            || kind == KIND_FLOAT;
    }

    function _isCategory2Kind(uint256 kind) private pure returns (bool) {
        return kind == KIND_LONG || kind == KIND_DOUBLE;
    }

    function _loadLong(
        uint256[] memory stack, uint256 sp, uint256[] memory locals,
        bool[] memory initialized, uint256 local, uint256 pc
    ) private pure returns (uint256) {
        if (local >= locals.length || local + 1 >= locals.length) revert BytecodeError(8, pc);
        if (!initialized[local]) revert BytecodeError(11, pc);
        _requireKind(locals[local], KIND_LONG, pc);
        if (!initialized[local + 1]) revert BytecodeError(11, pc);
        _requireKind(locals[local + 1], KIND_LONG_TAIL, pc);
        return _push(stack, sp, locals[local], pc);
    }

    function _storeLong(
        uint256[] memory stack, uint256 sp, uint256[] memory locals,
        bool[] memory initialized, uint256 local, uint256 pc
    ) private pure returns (uint256) {
        return _storeCategory2(
            stack, sp, locals, initialized, local, KIND_LONG, KIND_LONG_TAIL, pc
        );
    }

    function _loadDouble(
        uint256[] memory stack, uint256 sp, uint256[] memory locals,
        bool[] memory initialized, uint256 local, uint256 pc
    ) private pure returns (uint256) {
        if (local >= locals.length || local + 1 >= locals.length) revert BytecodeError(8, pc);
        if (!initialized[local]) revert BytecodeError(11, pc);
        _requireKind(locals[local], KIND_DOUBLE, pc);
        if (!initialized[local + 1]) revert BytecodeError(11, pc);
        _requireKind(locals[local + 1], KIND_DOUBLE_TAIL, pc);
        return _push(stack, sp, locals[local], pc);
    }

    function _storeDouble(
        uint256[] memory stack, uint256 sp, uint256[] memory locals,
        bool[] memory initialized, uint256 local, uint256 pc
    ) private pure returns (uint256) {
        return _storeCategory2(
            stack, sp, locals, initialized, local, KIND_DOUBLE, KIND_DOUBLE_TAIL, pc
        );
    }

    function _storeCategory2(
        uint256[] memory stack, uint256 sp, uint256[] memory locals,
        bool[] memory initialized, uint256 local, uint256 kind, uint256 tail, uint256 pc
    ) private pure returns (uint256) {
        if (local >= locals.length || local + 1 >= locals.length) revert BytecodeError(8, pc);
        if (sp == 0) revert BytecodeError(3, pc);
        _requireKind(stack[sp - 1], kind, pc);
        _invalidateLocal(locals, initialized, local);
        _invalidateLocal(locals, initialized, local + 1);
        locals[local] = stack[sp - 1];
        locals[local + 1] = tail << KIND_SHIFT;
        initialized[local] = true;
        initialized[local + 1] = true;
        return sp - 1;
    }

    function _copyArguments(
        Frame memory child, Selected memory target, uint256[] memory stack,
        uint256 stackAt, uint256 localAt
    ) private pure {
        for (uint256 i = 0; i < target.argumentCount; ++i) {
            uint256 value = stack[stackAt + i];
            child.locals[localAt] = value;
            child.initialized[localAt] = true;
            if (_isCategory2Kind(target.argumentKinds[i])) {
                child.locals[localAt + 1] = (target.argumentKinds[i] == KIND_LONG
                    ? KIND_LONG_TAIL : KIND_DOUBLE_TAIL) << KIND_SHIFT;
                child.initialized[localAt + 1] = true;
                localAt += 2;
            } else {
                ++localAt;
            }
        }
    }

    function _loadKind(
        uint256[] memory stack,
        uint256 sp,
        uint256[] memory locals,
        bool[] memory initialized,
        uint256 local,
        uint256 wantedKind,
        uint256 pc
    ) private pure returns (uint256) {
        if (local >= locals.length) revert BytecodeError(8, pc);
        if (!initialized[local]) revert BytecodeError(11, pc);
        _requireKind(locals[local], wantedKind, pc);
        return _push(stack, sp, locals[local], pc);
    }

    function _storeKind(
        uint256[] memory stack,
        uint256 sp,
        uint256[] memory locals,
        bool[] memory initialized,
        uint256 local,
        uint256 wantedKind,
        uint256 pc
    ) private pure returns (uint256) {
        if (local >= locals.length) revert BytecodeError(8, pc);
        if (sp == 0) revert BytecodeError(3, pc);
        _requireKind(stack[sp - 1], wantedKind, pc);
        _invalidateLocal(locals, initialized, local);
        locals[local] = stack[sp - 1];
        initialized[local] = true;
        return sp - 1;
    }

    function _loadReference(
        uint256[] memory stack, uint256 sp, uint256[] memory locals, bool[] memory initialized,
        uint256 local, uint256 pc
    ) private pure returns (uint256) {
        if (local >= locals.length) revert BytecodeError(8, pc);
        if (!initialized[local]) revert BytecodeError(11, pc);
        uint256 kind = _valueKind(locals[local]);
        if (kind != KIND_REF && kind != KIND_UNINIT) revert BytecodeError(14, pc);
        return _push(stack, sp, locals[local], pc);
    }

    function _storeReference(
        uint256[] memory stack, uint256 sp, uint256[] memory locals, bool[] memory initialized,
        uint256 local, uint256 pc
    ) private pure returns (uint256) {
        if (local >= locals.length) revert BytecodeError(8, pc);
        if (sp == 0) revert BytecodeError(3, pc);
        uint256 kind = _valueKind(stack[sp - 1]);
        if (kind != KIND_REF && kind != KIND_UNINIT) revert BytecodeError(14, pc);
        _invalidateLocal(locals, initialized, local);
        locals[local] = stack[sp - 1];
        initialized[local] = true;
        return sp - 1;
    }

    function _initializeAliases(Frame memory f, uint256 handle) private pure {
        uint256 uninitialized = (KIND_UNINIT << KIND_SHIFT) | handle;
        uint256 initializedRef = _packRef(uint32(handle));
        for (uint256 i = 0; i < f.sp; ++i) {
            if (f.stack[i] == uninitialized) f.stack[i] = initializedRef;
        }
        for (uint256 i = 0; i < f.locals.length; ++i) {
            if (f.initialized[i] && f.locals[i] == uninitialized) f.locals[i] = initializedRef;
        }
    }

    function _permuteStack(uint256[] memory stack, uint256 sp, uint8 op, uint256 pc)
        private pure returns (uint256)
    {
        if (sp == 0) revert BytecodeError(3, pc);
        uint256 v1 = stack[sp - 1];
        bool c1 = _isCategory1(v1);
        bool c2 = _isCategory2Kind(_valueKind(v1));
        if (!c1 && !c2) revert BytecodeError(14, pc);

        if (op == 0x58) { // pop2: one category-2 or two category-1 values
            if (c2) return sp - 1;
            if (sp < 2) revert BytecodeError(3, pc);
            if (!_isCategory1(stack[sp - 2])) revert BytecodeError(14, pc);
            return sp - 2;
        }
        if (op == 0x59) { // dup
            if (!c1) revert BytecodeError(14, pc);
            return _push(stack, sp, v1, pc);
        }
        if (op == 0x5a || op == 0x5f) { // dup_x1 / swap: two category-1 values
            if (!c1) revert BytecodeError(14, pc);
            if (sp < 2) revert BytecodeError(3, pc);
            uint256 v2 = stack[sp - 2];
            if (!_isCategory1(v2)) revert BytecodeError(14, pc);
            if (op == 0x5f) {
                stack[sp - 2] = v1;
                stack[sp - 1] = v2;
                return sp;
            }
            _requireExtraWords(stack, sp, 1, pc);
            stack[sp - 2] = v1;
            stack[sp - 1] = v2;
            stack[sp] = v1;
            return sp + 1;
        }
        if (op == 0x5b) { // dup_x2: c,b,a or A,a (bottom to top)
            if (!c1) revert BytecodeError(14, pc);
            if (sp < 2) revert BytecodeError(3, pc);
            uint256 v2 = stack[sp - 2];
            if (_isCategory2Kind(_valueKind(v2))) {
                _requireExtraWords(stack, sp, 1, pc);
                stack[sp - 2] = v1; stack[sp - 1] = v2; stack[sp] = v1;
                return sp + 1;
            }
            if (!_isCategory1(v2)) revert BytecodeError(14, pc);
            if (sp < 3) revert BytecodeError(3, pc);
            uint256 v3 = stack[sp - 3];
            if (!_isCategory1(v3)) revert BytecodeError(14, pc);
            _requireExtraWords(stack, sp, 1, pc);
            stack[sp - 3] = v1; stack[sp - 2] = v3;
            stack[sp - 1] = v2; stack[sp] = v1;
            return sp + 1;
        }
        if (op == 0x5c) { // dup2: A or b,a
            if (c2) {
                _requireExtraWords(stack, sp, 2, pc);
                stack[sp] = v1;
                return sp + 1;
            }
            if (sp < 2) revert BytecodeError(3, pc);
            uint256 v2 = stack[sp - 2];
            if (!_isCategory1(v2)) revert BytecodeError(14, pc);
            _requireExtraWords(stack, sp, 2, pc);
            stack[sp] = v2; stack[sp + 1] = v1;
            return sp + 2;
        }
        if (op == 0x5d) { // dup2_x1: a,A or c,b,a
            if (c2) {
                if (sp < 2) revert BytecodeError(3, pc);
                uint256 v2 = stack[sp - 2];
                if (!_isCategory1(v2)) revert BytecodeError(14, pc);
                _requireExtraWords(stack, sp, 2, pc);
                stack[sp - 2] = v1; stack[sp - 1] = v2; stack[sp] = v1;
                return sp + 1;
            }
            if (sp < 2) revert BytecodeError(3, pc);
            uint256 v2 = stack[sp - 2];
            if (!_isCategory1(v2)) revert BytecodeError(14, pc);
            if (sp < 3) revert BytecodeError(3, pc);
            uint256 v3 = stack[sp - 3];
            if (!_isCategory1(v3)) revert BytecodeError(14, pc);
            _requireExtraWords(stack, sp, 2, pc);
            stack[sp - 3] = v2; stack[sp - 2] = v1; stack[sp - 1] = v3;
            stack[sp] = v2; stack[sp + 1] = v1;
            return sp + 2;
        }
        // dup2_x2, all four JVMS forms.
        if (c2) {
            if (sp < 2) revert BytecodeError(3, pc);
            uint256 v2 = stack[sp - 2];
            if (_isCategory2Kind(_valueKind(v2))) {
                _requireExtraWords(stack, sp, 2, pc);
                stack[sp - 2] = v1; stack[sp - 1] = v2; stack[sp] = v1;
                return sp + 1;
            }
            if (!_isCategory1(v2)) revert BytecodeError(14, pc);
            if (sp < 3) revert BytecodeError(3, pc);
            uint256 v3 = stack[sp - 3];
            if (!_isCategory1(v3)) revert BytecodeError(14, pc);
            _requireExtraWords(stack, sp, 2, pc);
            stack[sp - 3] = v1; stack[sp - 2] = v3;
            stack[sp - 1] = v2; stack[sp] = v1;
            return sp + 1;
        }
        if (sp < 2) revert BytecodeError(3, pc);
        uint256 v2 = stack[sp - 2];
        if (!_isCategory1(v2)) revert BytecodeError(14, pc);
        if (sp < 3) revert BytecodeError(3, pc);
        uint256 v3 = stack[sp - 3];
        if (_isCategory2Kind(_valueKind(v3))) {
            _requireExtraWords(stack, sp, 2, pc);
            stack[sp - 3] = v2; stack[sp - 2] = v1; stack[sp - 1] = v3;
            stack[sp] = v2; stack[sp + 1] = v1;
            return sp + 2;
        }
        if (!_isCategory1(v3)) revert BytecodeError(14, pc);
        if (sp < 4) revert BytecodeError(3, pc);
        uint256 v4 = stack[sp - 4];
        if (!_isCategory1(v4)) revert BytecodeError(14, pc);
        _requireExtraWords(stack, sp, 2, pc);
        stack[sp - 4] = v2; stack[sp - 3] = v1; stack[sp - 2] = v4;
        stack[sp - 1] = v3; stack[sp] = v2; stack[sp + 1] = v1;
        return sp + 2;
    }

    function _requireExtraWords(
        uint256[] memory stack, uint256 sp, uint256 extra, uint256 pc
    ) private pure {
        uint256 words = _stackWords(stack, sp);
        if (words > stack.length || extra > stack.length - words) revert BytecodeError(9, pc);
    }

    function _invalidateLocal(
        uint256[] memory locals, bool[] memory initialized, uint256 local
    ) private pure {
        if (initialized[local]) {
            uint256 kind = _valueKind(locals[local]);
            if (_isCategory2Kind(kind) && local + 1 < locals.length) {
                locals[local + 1] = 0;
                initialized[local + 1] = false;
            } else if ((kind == KIND_LONG_TAIL || kind == KIND_DOUBLE_TAIL) && local != 0) {
                locals[local - 1] = 0;
                initialized[local - 1] = false;
            }
        }
        locals[local] = 0;
        initialized[local] = false;
    }

    function _unaryCondition(uint8 op, int32 value) private pure returns (bool) {
        if (op == 0x99) return value == 0;
        if (op == 0x9a) return value != 0;
        if (op == 0x9b) return value < 0;
        if (op == 0x9c) return value >= 0;
        if (op == 0x9d) return value > 0;
        return value <= 0;
    }

    function _binaryCondition(uint8 op, int32 left, int32 right) private pure returns (bool) {
        if (op == 0x9f) return left == right;
        if (op == 0xa0) return left != right;
        if (op == 0xa1) return left < right;
        if (op == 0xa2) return left >= right;
        if (op == 0xa3) return left > right;
        return left <= right;
    }

    function _equals(bytes memory data, uint256 off, uint256 n, bytes memory wanted)
        private
        pure
        returns (bool)
    {
        if (n != wanted.length) return false;
        for (uint256 i = 0; i < n; ++i) if (data[off + i] != wanted[i]) return false;
        return true;
    }

    function _equalsSlice(
        bytes memory data,
        uint256 firstOffset,
        uint256 firstLength,
        uint256 secondOffset,
        uint256 secondLength
    ) private pure returns (bool) {
        if (firstLength != secondLength) return false;
        for (uint256 i = 0; i < firstLength; ++i) {
            if (data[firstOffset + i] != data[secondOffset + i]) return false;
        }
        return true;
    }

    function _equalsLiteral(bytes memory data, uint256 off, uint256 n, bytes memory literal)
        private
        pure
        returns (bool)
    {
        return _equals(data, off, n, literal);
    }

    function _readFields(Reader memory r, ClassInfo memory c)
        private
        pure
        returns (FieldInfo[] memory fields)
    {
        uint256 count = _u2(r);
        fields = new FieldInfo[](count);
        for (uint256 i = 0; i < count; ++i) {
            uint16 access = _u2(r);
            uint16 nameIndex = _u2(r);
            uint16 descriptorIndex = _u2(r);
            uint256 attributesCount = _u2(r);
            FieldInfo memory field;
            field.accessFlags = access;
            field.nameIndex = nameIndex;
            field.descriptorIndex = descriptorIndex;
            uint8 supportedKind;
            uint256 descriptorOffset;
            uint256 descriptorLength;
            bool exactStringDescriptor;
            if (descriptorIndex != 0 && descriptorIndex < c.cp.length
                && uint8(c.cp[descriptorIndex]) == 1) {
                (descriptorOffset, descriptorLength) = _utf(c.cp[descriptorIndex]);
                (bool valid, uint256 width, uint8 kind) = _descriptorType(
                    c.data, descriptorOffset, descriptorOffset + descriptorLength, false
                );
                if (valid && width == descriptorLength) supportedKind = kind;
                exactStringDescriptor = _equalsLiteral(
                    c.data, descriptorOffset, descriptorLength, bytes("Ljava/lang/String;")
                );
            }
            bool sawStringConstantAttribute;
            for (uint256 a = 0; a < attributesCount; ++a) {
                uint256 attributeNameIndex = _u2(r);
                uint256 attributeLength = _u4(r);
                bool isConstantValue;
                if (
                    attributeNameIndex != 0 && attributeNameIndex < c.cp.length
                        && uint8(c.cp[attributeNameIndex]) == 1
                ) {
                    (uint256 attributeNameOffset, uint256 attributeNameLength) =
                        _utf(c.cp[attributeNameIndex]);
                    isConstantValue = _equalsLiteral(
                        c.data, attributeNameOffset, attributeNameLength, bytes("ConstantValue")
                    );
                }
                bool primitiveStatic = (access & 0x0008) != 0 && supportedKind != 0
                    && supportedKind != KIND_REF;
                if (isConstantValue && exactStringDescriptor) {
                    if (sawStringConstantAttribute || attributeLength != 2) {
                        revert FieldError(5, i);
                    }
                    sawStringConstantAttribute = true;
                    uint256 constantIndex = _u2(r);
                    if (constantIndex == 0 || constantIndex >= c.cp.length
                        || uint8(c.cp[constantIndex]) != 8) revert FieldError(5, i);
                    uint256 utfIndex = (c.cp[constantIndex] >> 8) & 0xffff;
                    if (utfIndex == 0 || utfIndex >= c.cp.length
                        || uint8(c.cp[utfIndex]) != 1) revert FieldError(5, i);
                    // Instance ConstantValue attributes are structurally checked but ignored.
                    if ((access & 0x0008) != 0) {
                        field.hasConstant = true;
                        field.constantValue = constantIndex;
                    }
                } else if (isConstantValue && primitiveStatic) {
                    if ((supportedKind != KIND_INT && supportedKind != KIND_LONG
                            && supportedKind != KIND_FLOAT && supportedKind != KIND_DOUBLE)
                        || field.hasConstant || attributeLength != 2) {
                        revert FieldError(5, i);
                    }
                    uint256 constantIndex = _u2(r);
                    uint8 wantedTag = supportedKind == KIND_LONG ? 5
                        : (supportedKind == KIND_DOUBLE ? 6
                            : (supportedKind == KIND_FLOAT ? 4 : 3));
                    if (
                        constantIndex == 0 || constantIndex >= c.cp.length
                            || uint8(c.cp[constantIndex]) != wantedTag
                    ) revert FieldError(5, i);
                    field.hasConstant = true;
                    field.constantValue = (supportedKind == KIND_LONG || supportedKind == KIND_DOUBLE)
                        ? (c.cp[constantIndex] >> 8)
                        : (supportedKind == KIND_FLOAT
                            ? uint256(uint32(c.cp[constantIndex] >> 8))
                            : uint256(_normalizeInt(
                                uint32(c.cp[constantIndex] >> 8), uint8(c.data[descriptorOffset])
                            )));
                } else if (isConstantValue && supportedKind == KIND_REF) {
                    // LB0 admits reference ConstantValue only for exact java.lang.String.
                    revert FieldError(5, i);
                } else {
                    _skip(r, attributeLength);
                }
            }
            fields[i] = field;
        }
    }

    function _skipMembers(Reader memory r) private pure {
        uint256 count = _u2(r);
        for (uint256 i = 0; i < count; ++i) {
            _skip(r, 6);
            _skipAttributes(r);
        }
    }

    function _skipAttributes(Reader memory r) private pure {
        uint256 count = _u2(r);
        for (uint256 i = 0; i < count; ++i) {
            _skip(r, 2);
            _skip(r, _u4(r));
        }
    }

    function _checkedMul2(uint256 n, uint256 at) private pure returns (uint256) {
        if (n > type(uint256).max / 2) revert ClassError(11, at);
        return n * 2;
    }

    function _skip(Reader memory r, uint256 n) private pure {
        if (r.pos > r.data.length || n > r.data.length - r.pos) revert ClassError(12, r.pos);
        r.pos += n;
    }

    function _u1(Reader memory r) private pure returns (uint8 v) {
        if (r.pos >= r.data.length) revert ClassError(12, r.pos);
        v = uint8(r.data[r.pos]);
        ++r.pos;
    }

    function _u2(Reader memory r) private pure returns (uint16 v) {
        if (r.pos > r.data.length || r.data.length - r.pos < 2) revert ClassError(12, r.pos);
        v = (uint16(uint8(r.data[r.pos])) << 8) | uint16(uint8(r.data[r.pos + 1]));
        r.pos += 2;
    }

    function _u4(Reader memory r) private pure returns (uint32 v) {
        if (r.pos > r.data.length || r.data.length - r.pos < 4) revert ClassError(12, r.pos);
        v = _unsigned32(r.data, r.pos);
        r.pos += 4;
    }

    function _u2Bounded(Reader memory r, uint256 end) private pure returns (uint16 v) {
        if (r.pos > end || end - r.pos < 2) revert ClassError(13, r.pos);
        return _u2(r);
    }

    function _u4Bounded(Reader memory r, uint256 end) private pure returns (uint32 v) {
        if (r.pos > end || end - r.pos < 4) revert ClassError(13, r.pos);
        return _u4(r);
    }

    function _appendThrowableBootstraps(ClassInfo[] memory classes, uint256 at) private pure {
        classes[at++].data = _bootstrapThrowable();
        classes[at++].data = _bootstrapError();
        classes[at++].data = _bootstrapVirtualMachineError();
        classes[at++].data = _bootstrapStackOverflowError();
        classes[at++].data = _bootstrapOutOfMemoryError();
        classes[at++].data = _bootstrapLinkageError();
        classes[at++].data = _bootstrapExceptionInInitializerError();
        classes[at++].data = _bootstrapIncompatibleClassChangeError();
        classes[at++].data = _bootstrapNoClassDefFoundError();
        classes[at++].data = _bootstrapAbstractMethodError();
        classes[at++].data = _bootstrapException();
        classes[at++].data = _bootstrapRuntimeException();
        classes[at++].data = _bootstrapArithmeticException();
        classes[at++].data = _bootstrapNullPointerException();
        classes[at++].data = _bootstrapNegativeArraySizeException();
        classes[at++].data = _bootstrapClassCastException();
        classes[at++].data = _bootstrapArrayStoreException();
        classes[at++].data = _bootstrapIndexOutOfBoundsException();
        classes[at++].data = _bootstrapArrayIndexOutOfBoundsException();
    }

    function _appendStringBootstraps(ClassInfo[] memory classes, uint256 at) private pure {
        // As with Throwable, append the raw canonical images every invocation and
        // parse each lazily in EVM when resolution reaches it.
        classes[at++].data = _bootstrapComparable();
        classes[at++].data = _bootstrapCharSequence();
        classes[at++].data = _bootstrapString();
    }

    function _appendIOBootstraps(ClassInfo[] memory classes, uint256 at) private pure {
        classes[at++].data = _bootstrapIOException();
        classes[at++].data = _bootstrapFileNotFoundException();
        classes[at++].data = _bootstrapEOFException();
    }

    function _appendVFSBootstraps(ClassInfo[] memory classes, uint256 at) private pure {
        classes[at++].data = _bootstrapAutoCloseable();
        classes[at++].data = _bootstrapCloseable();
        classes[at++].data = _bootstrapFlushable();
        classes[at++].data = _bootstrapFile();
        classes[at++].data = _bootstrapInputStream();
        classes[at++].data = _bootstrapOutputStream();
        classes[at++].data = _bootstrapFileInputStream();
        classes[at++].data = _bootstrapFileOutputStream();
    }

    function _bootstrapAutoCloseable() private pure returns (bytes memory) {
        return hex"cafebabe00000034000a070007070008010005636c6f736501000328295601000a457863657074696f6e730700090100176a6176612f6c616e672f4175746f436c6f736561626c650100106a6176612f6c616e672f4f626a6563740100136a6176612f6c616e672f457863657074696f6e0601000100020000000000010401000300040001000500000004000100060000";
    }

    function _bootstrapCloseable() private pure returns (bytes memory) {
        return hex"cafebabe00000034000c07000807000907000a010005636c6f736501000328295601000a457863657074696f6e7307000b0100116a6176612f696f2f436c6f736561626c650100106a6176612f6c616e672f4f626a6563740100176a6176612f6c616e672f4175746f436c6f736561626c650100136a6176612f696f2f494f457863657074696f6e06010001000200010003000000010401000400050001000600000004000100070000";
    }

    function _bootstrapFlushable() private pure returns (bytes memory) {
        return hex"cafebabe00000034000a070007070008010005666c75736801000328295601000a457863657074696f6e730700090100116a6176612f696f2f466c75736861626c650100106a6176612f6c616e672f4f626a6563740100136a6176612f696f2f494f457863657074696f6e0601000100020000000000010401000300040001000500000004000100060000";
    }

    function _bootstrapFile() private pure returns (bytes memory) {
        return hex"cafebabe00000034003e0a000c00290a0004002a0a0004002b07002c0a0004002d09000a002e0a0004002f0a000a00300a000a00310700320a000a0033070034070035070036010004706174680100124c6a6176612f6c616e672f537472696e673b0100063c696e69743e010015284c6a6176612f6c616e672f537472696e673b2956010004436f646501000d537461636b4d61705461626c6507003207002c070037010009636f6d70617265546f010011284c6a6176612f696f2f46696c653b2949010005706174683001001428294c6a6176612f6c616e672f537472696e673b01000665786973747301000328295a010006697346696c6501000b69734469726563746f72790100056d6b6469720100066d6b6469727301000573746174300100032829490100066d6b64697230010004285a2949010015284c6a6176612f6c616e672f4f626a6563743b29490100095369676e617475726501004e4c6a6176612f6c616e672f4f626a6563743b4c6a6176612f696f2f53657269616c697a61626c653b4c6a6176612f6c616e672f436f6d70617261626c653c4c6a6176612f696f2f46696c653b3e3b0c001100380c003900230c003a003b0100106a6176612f6c616e672f537472696e670c0011003c0c000f00100c0018003d0c002200230c0024002501000c6a6176612f696f2f46696c650c001800190100106a6176612f6c616e672f4f626a6563740100146a6176612f696f2f53657269616c697a61626c650100146a6176612f6c616e672f436f6d70617261626c650100025b430100032829560100066c656e67746801000663686172417401000428492943010005285b432956010015284c6a6176612f6c616e672f537472696e673b29490021000a000c0002000d000e00010012000f00100000000b00010011001200010013000000cb000400080000008c2ab700012bb600023d1cbc054e03360403360503360615061ca200322b1506b6000336071507102fa000111505990006a70015043605a700060336052d1504840401150755840601a7ffce150404a400112d1504046434102fa000068404ff1504bc053a0603360715071504a20012190615072d15073455840701a7ffed2abb0004591906b70005b50006b10000000100140000002d0009ff00160007070015070016010700170101010000fc001c010502fa0008fa000513fd000807001701fa00150001001800190001001300000018000200020000000c2ab400062bb40006b60007ac000000000010001a001b000100130000001100010001000000052ab40006b0000000000001001c001d0001001300000024000100010000000d2ab7000899000704a7000403ac0000000100140000000500020b40010001001e001d0001001300000025000200010000000e2ab7000804a0000704a7000403ac0000000100140000000500020c40010001001f001d0001001300000025000200010000000e2ab7000805a0000704a7000403ac0000000100140000000500020c400100010020001d0001001300000026000200010000000f2a03b7000904a0000704a7000403ac0000000100140000000500020d400100010021001d0001001300000026000200010000000f2a04b7000904a0000704a7000403ac0000000100140000000500020d400101020022002300000102002400250000104100180026000100130000001500020002000000092a2bc0000ab6000bac0000000000010027000000020028";
    }

    function _bootstrapInputStream() private pure returns (bytes memory) {
        return hex"cafebabe00000034001d0a000800150a000700160700170a000300150a0007001807001907001a07001b07001c0100063c696e69743e010003282956010004436f64650100047265616401000328294901000a457863657074696f6e73010005285b422949010007285b424949294901000d537461636b4d61705461626c65070019010005636c6f73650c000a000b0c000d00110100236a6176612f6c616e672f496e6465784f75744f66426f756e6473457863657074696f6e0c000d000e0100136a6176612f696f2f494f457863657074696f6e0100136a6176612f696f2f496e70757453747265616d0100106a6176612f6c616e672f4f626a6563740100116a6176612f696f2f436c6f736561626c6504210007000800010009000000050004000a000b0001000c0000001100010001000000052ab70001b1000000000401000d000e0001000f00000004000100060001000d00100002000c0000001500040002000000092a2b032bbeb60002ac00000000000f00000004000100060001000d00110002000c0000009600030008000000652bbe36041c9b000f1d9b000b1c15041d64a4000bbb000359b70004bf1d9a000503ac2ab600053605150502a0000502ac2b1c1505915404360615061da200212ab600053605150502a00006a700122b1c15066015059154840601a7ffdfa700053a071506ac00010039005d0060000600010012000000170009fc0014010705fc000d01fc000801140e4207001301000f000000040001000600010014000b0002000c0000000d0000000100000001b100000000000f00000004000100060000";
    }

    function _bootstrapOutputStream() private pure returns (bytes memory) {
        return hex"cafebabe00000034001f0a000700160a000600170700180a000300160a0006001907001a07001b07001c07001d0100063c696e69743e010003282956010004436f646501000577726974650100042849295601000a457863657074696f6e7307001e010005285b422956010007285b424949295601000d537461636b4d61705461626c65010005636c6f7365010005666c7573680c000a000b0c000d00120100236a6176612f6c616e672f496e6465784f75744f66426f756e6473457863657074696f6e0c000d000e0100146a6176612f696f2f4f757470757453747265616d0100106a6176612f6c616e672f4f626a6563740100116a6176612f696f2f436c6f736561626c650100116a6176612f696f2f466c75736861626c650100136a6176612f696f2f494f457863657074696f6e042100060007000200080009000000060004000a000b0001000c0000001100010001000000052ab70001b1000000000401000d000e0001000f00000004000100100001000d00110002000c0000001500040002000000092a2b032bbeb60002b100000000000f00000004000100100001000d00120002000c0000005600040006000000362bbe36041c9b000f1d9b000b1c15041d64a4000bbb000359b70004bf03360515051da200132a2b1c15056033b60005840501a7ffedb10000000100130000000e0004fc00140107fc000201fa0015000f000000040001001000010014000b0002000c0000000d0000000100000001b100000000000f000000040001001000010015000b0002000c0000000d0000000100000001b100000000000f00000004000100100000";
    }

    function _bootstrapFileInputStream() private pure returns (bytes memory) {
        return hex"cafebabe0000003400580a001c00350700360a000200350a001b003709001b00380700390a001b003a0a0006003b0a001b003c07003d08003e0a000a003b0a001b003f0700400a000e00350a001b00410a001b00420800430800440800450800460a004700480a001900490a0019004a07004b0a0019004c07004d07004e01000668616e646c65010001490100063c696e69743e010011284c6a6176612f696f2f46696c653b2956010004436f646501000d537461636b4d61705461626c6507004d07004f01000a457863657074696f6e7301000472656164010003282949010005285b422949010007285b4249492949010005636c6f736501000328295601000c6572726f724d657373616765010023284c6a6176612f696f2f46696c653b49294c6a6176612f6c616e672f537472696e673b07004b0700500100056f70656e30010011284c6a6176612f696f2f46696c653b2949010008726561644f6e65300100057265616430010006636c6f7365300c001f002b01001e6a6176612f6c616e672f4e756c6c506f696e746572457863657074696f6e0c003000310c001d001e01001d6a6176612f696f2f46696c654e6f74466f756e64457863657074696f6e0c002c002d0c001f00510c003200270100136a6176612f696f2f494f457863657074696f6e01000d53747265616d20436c6f7365640c002600290100236a6176612f6c616e672f496e6465784f75744f66426f756e6473457863657074696f6e0c003300290c0034002701001c20284e6f20737563682066696c65206f72206469726563746f727929010011202849732061206469726563746f72792901001220284e6f742061206469726563746f72792901001420285065726d697373696f6e2064656e6965642907004f0c005200530c005400270c005500560100106a6176612f6c616e672f537472696e670c001f00570100176a6176612f696f2f46696c65496e70757453747265616d0100136a6176612f696f2f496e70757453747265616d01000c6a6176612f696f2f46696c650100025b43010015284c6a6176612f6c616e672f537472696e673b2956010005706174683001001428294c6a6176612f6c616e672f537472696e673b0100066c656e67746801000663686172417401000428492943010005285b4329560021001b001c000000010002001d001e0000000a0001001f00200002002100000052000400030000002d2ab700012bc7000bbb000259b70003bf2a2bb700043d1c9e00092a1cb50005b1bb0006592b1cb80007b70008bf000000010022000000130002ff001000020700230700240000fc000f0100250000000400010006000100260027000200210000002f00030002000000172ab700093c1b10fea0000dbb000a59120bb7000cbf1bac000000010022000000060001fc0015010025000000040001000a000100260028000200210000001500040002000000092a2b032bbeb6000dac000000000025000000040001000a000100260029000200210000005d000400060000003f2bbe36041c9b000f1d9b000b1c15041d64a4000bbb000e59b7000fbf1d9a000503ac2a2b1c1db700103605150510fea0000dbb000a59120bb7000cbf1505ac0000000100220000000c0004fc0014010705fc0019010025000000040001000a0001002a002b000200210000002c00030002000000142ab700113c1b99000dbb000a59120bb7000cbfb1000000010022000000060001fc0013010025000000040001000a000a002c002d00010021000000bf00040009000000831b02a0000912124da7001e1b10fea0000912134da700121b10fca0000912144da7000612154d2ab600164e2db6001736042cb6001736051504150560bc053a0603360715071504a20014190615072d1507b6001855840701a7ffeb03360815081505a20017190615071508602c1508b6001855840801a7ffe8bb0019591906b7001ab00000000100220000002a00080b0b0bfc000207002eff001c00080700240107002e07002e010107002f01000017fc000201fa001a01020030003100000102003200270000010200330029000001020034002700000000";
    }

    function _bootstrapFileOutputStream() private pure returns (bytes memory) {
        return hex"cafebabe00000034005e0a001c003a0a001d003b07003c0a0003003b0a001c003d09001c003e07003f0a001c00400a000700410a001c00420700430800440a000b00410a001c00450700460a000f003b0a001c00470a001c004808004908004a08004b08004c0a004d004e0a001a004f0a001a00500700510a001a005207005307005401000668616e646c65010001490100063c696e69743e010011284c6a6176612f696f2f46696c653b2956010004436f646501000a457863657074696f6e73010012284c6a6176612f696f2f46696c653b5a295601000d537461636b4d61705461626c65070053070055010005777269746501000428492956010005285b422956010007285b4249492956010005636c6f736501000328295601000c6572726f724d657373616765010023284c6a6176612f696f2f46696c653b49294c6a6176612f6c616e672f537472696e673b0700510700560100056f70656e30010012284c6a6176612f696f2f46696c653b5a294901000977726974654f6e653001000428492949010006777269746530010007285b4249492949010006636c6f7365300100032829490c002000240c0020002d01001e6a6176612f6c616e672f4e756c6c506f696e746572457863657074696f6e0c003200330c001e001f01001d6a6176612f696f2f46696c654e6f74466f756e64457863657074696f6e0c002e002f0c002000570c003400350100136a6176612f696f2f494f457863657074696f6e01000d53747265616d20436c6f7365640c0028002b0100236a6176612f6c616e672f496e6465784f75744f66426f756e6473457863657074696f6e0c003600370c0038003901001c20284e6f20737563682066696c65206f72206469726563746f727929010011202849732061206469726563746f72792901001220284e6f742061206469726563746f72792901001420285065726d697373696f6e2064656e696564290700550c005800590c005a00390c005b005c0100106a6176612f6c616e672f537472696e670c0020005d0100186a6176612f696f2f46696c654f757470757453747265616d0100146a6176612f696f2f4f757470757453747265616d01000c6a6176612f696f2f46696c650100025b43010015284c6a6176612f6c616e672f537472696e673b2956010005706174683001001428294c6a6176612f6c616e672f537472696e673b0100066c656e67746801000663686172417401000428492943010005285b4329560021001c001d000000010002001e001f0000000b000100200021000200220000001300030002000000072a2b03b70001b100000000002300000004000100070001002000240002002200000054000400040000002e2ab700022bc7000bbb000359b70004bf2a2b1cb700053e1d9e00092a1db50006b1bb0007592b1db80008b70009bf000000010025000000140002ff00100003070026070027010000fc00100100230000000400010007000100280029000200220000002f00030003000000172a1bb7000a3d1c10fea0000dbb000b59120cb7000dbfb1000000010025000000060001fc0016010023000000040001000b00010028002a000200220000001500040002000000092a2b032bbeb6000eb1000000000023000000040001000b00010028002b000200220000005a000400060000003c2bbe36041c9b000f1d9b000b1c15041d64a4000bbb000f59b70010bf1d9a0004b12a2b1c1db700113605150510fea0000dbb000b59120cb7000dbfb10000000100250000000c0004fc0014010704fc0019010023000000040001000b0001002c002d000200220000002c00030002000000142ab700123c1b99000dbb000b59120cb7000dbfb1000000010025000000060001fc0013010023000000040001000b000a002e002f00010022000000bf00040009000000831b02a0000912134da7001e1b10fea0000912144da700121b10fca0000912154da7000612164d2ab600174e2db6001836042cb6001836051504150560bc053a0603360715071504a20014190615072d1507b6001955840701a7ffeb03360815081505a20017190615071508602c1508b6001955840801a7ffe8bb001a591906b7001bb00000000100250000002a00080b0b0bfc0002070030ff001c000807002701070030070030010107003101000017fc000201fa001a01020032003300000102003400350000010200360037000001020038003900000000";
    }

    function _bootstrapComparable() private pure returns (bytes memory) {
        return hex"cafebabe00000034000a0700020100146a6176612f6c616e672f436f6d70617261626c650700040100106a6176612f6c616e672f4f626a656374010009636f6d70617265546f010015284c6a6176612f6c616e672f4f626a6563743b29490100095369676e61747572650100062854543b29490100283c543a4c6a6176612f6c616e672f4f626a6563743b3e4c6a6176612f6c616e672f4f626a6563743b0601000100030000000000010401000500060001000700000002000800010007000000020009";
    }

    function _bootstrapCharSequence() private pure returns (bytes memory) {
        return hex"cafebabe00000034000d0700020100166a6176612f6c616e672f4368617253657175656e63650700040100106a6176612f6c616e672f4f626a6563740100066c656e6774680100032829490100066368617241740100042849294301000b73756253657175656e636501001c284949294c6a6176612f6c616e672f4368617253657175656e63653b010008746f537472696e6701001428294c6a6176612f6c616e672f537472696e673b0601000100030000000000040401000500060000040100070008000004010009000a00000401000b000c00000000";
    }

    function _bootstrapString() private pure returns (bytes memory) {
        return hex"cafebabe0000003400320a000200030700040c000500060100106a6176612f6c616e672f4f626a6563740100063c696e69743e010003282956090008000907000a0c000b000c0100106a6176612f6c616e672f537472696e6701000576616c75650100025b43090008000e0c000f001001000468617368010001490a000800120c00130014010009636f6d70617265546f010015284c6a6176612f6c616e672f537472696e673b29490700160100146a6176612f696f2f53657269616c697a61626c650700180100146a6176612f6c616e672f436f6d70617261626c6507001a0100166a6176612f6c616e672f4368617253657175656e6365010004436f6465010005285b43295601000d537461636b4d61705461626c6507000c010015284c6a6176612f6c616e672f537472696e673b29560100066c656e6774680100032829490100076973456d70747901000328295a01000663686172417401000428492943010006657175616c73010015284c6a6176612f6c616e672f4f626a6563743b295a01000868617368436f6465010008746f537472696e6701001428294c6a6176612f6c616e672f537472696e673b010006696e7465726e01000b73756253657175656e636501001c284949294c6a6176612f6c616e672f4368617253657175656e63653b010015284c6a6176612f6c616e672f4f626a6563743b29490100104d6574686f64506172616d65746572730100095369676e617475726501006a4c6a6176612f6c616e672f4f626a6563743b4c6a6176612f696f2f53657269616c697a61626c653b4c6a6176612f6c616e672f436f6d70617261626c653c4c6a6176612f6c616e672f537472696e673b3e3b4c6a6176612f6c616e672f4368617253657175656e63653b003100080002000300150017001900020012000b000c00000002000f00100000000d0002000500060001001b00000016000200010000000a2ab700012a01b50007b10000000000010005001c0001001b0000004b00040004000000232ab700012bbebc054d033e1d2bbea2000f2c1d2b1d3455840301a7fff12a2cb50007b100000001001d000000160002ff000b000407000807001e07001e010000fa001100010005001f0001001b0000002100020002000000152ab700012a2bb40007b500072a2bb4000db5000db1000000000101002000210000010100220023000001010024002500000101002600270000010100280021000001010029002a000001010013001400000101002b002a00000101002c002d000010410013002e0002001b0000001500020002000000092a2bc00008b60011ac00000000002f00000005010000100000010030000000020031";
    }

    /// @dev Java 8 `public interface Runnable { public abstract void run(); }`, generated by bootstrap/build_runnable.py.
    function _bootstrapRunnable() private pure returns (bytes memory) {
        return hex"cafebabe0000003400070700020100126a6176612f6c616e672f52756e6e61626c650700040100106a6176612f6c616e672f4f626a65637401000372756e01000328295606010001000300000000000104010005000600000000";
    }

    /// @dev Java 8 minimal owned Class mirror shell; build_class.py pins this exact image.
    function _bootstrapClass() private pure returns (bytes memory) {
        return hex"cafebabe0000003400120a000200030700040c000500060100106a6176612f6c616e672f4f626a6563740100063c696e69743e010003282956090008000907000a0c000b000c01000f6a6176612f6c616e672f436c6173730100046e616d650100124c6a6176612f6c616e672f537472696e673b010004436f64650100076765744e616d6501001428294c6a6176612f6c616e672f537472696e673b0100095369676e61747572650100283c543a4c6a6176612f6c616e672f4f626a6563743b3e4c6a6176612f6c616e672f4f626a6563743b003100080002000000010002000b000c000000020002000500060001000d0000001100010001000000052ab70001b1000000000001000e000f0001000d0000001100010001000000052ab40007b00000000000010010000000020011";
    }

    /// @dev Java 8 owned platform map hierarchy; build_platform_map.py pins all five images.
    function _bootstrapMap() private pure returns (bytes memory) { return hex"cafebabe00000034001507000201000d6a6176612f7574696c2f4d61700700040100106a6176612f6c616e672f4f626a656374010003676574010026284c6a6176612f6c616e672f4f626a6563743b294c6a6176612f6c616e672f4f626a6563743b0100095369676e6174757265010017284c6a6176612f6c616e672f4f626a6563743b2954563b010003707574010038284c6a6176612f6c616e672f4f626a6563743b4c6a6176612f6c616e672f4f626a6563743b294c6a6176612f6c616e672f4f626a6563743b01000b28544b3b54563b2954563b01000473697a650100032829490100076973456d70747901000328295a010005636c65617201000328295601000b636f6e7461696e734b6579010015284c6a6176612f6c616e672f4f626a6563743b295a01003c3c4b3a4c6a6176612f6c616e672f4f626a6563743b563a4c6a6176612f6c616e672f4f626a6563743b3e4c6a6176612f6c616e672f4f626a6563743b0601000100030000000000060401000500060001000700000002000804010009000a0001000700000002000b0401000c000d00000401000e000f00000401001000110000040100120013000000010007000000020014"; }
    function _bootstrapConcurrentMap() private pure returns (bytes memory) { return hex"cafebabe00000034000c0700020100226a6176612f7574696c2f636f6e63757272656e742f436f6e63757272656e744d61700700040100106a6176612f6c616e672f4f626a65637407000601000d6a6176612f7574696c2f4d617001000b7075744966416273656e74010038284c6a6176612f6c616e672f4f626a6563743b4c6a6176612f6c616e672f4f626a6563743b294c6a6176612f6c616e672f4f626a6563743b0100095369676e617475726501000b28544b3b54563b2954563b0100533c4b3a4c6a6176612f6c616e672f4f626a6563743b563a4c6a6176612f6c616e672f4f626a6563743b3e4c6a6176612f6c616e672f4f626a6563743b4c6a6176612f7574696c2f4d61703c544b3b54563b3e3b06010001000300010005000000010401000700080001000900000002000a0001000900000002000b"; }
    function _bootstrapAbstractMap() private pure returns (bytes memory) { return hex"cafebabe00000034000e0a000200030700040c000500060100106a6176612f6c616e672f4f626a6563740100063c696e69743e0100032829560700080100156a6176612f7574696c2f41627374726163744d617007000a01000d6a6176612f7574696c2f4d6170010004436f64650100095369676e61747572650100533c4b3a4c6a6176612f6c616e672f4f626a6563743b563a4c6a6176612f6c616e672f4f626a6563743b3e4c6a6176612f6c616e672f4f626a6563743b4c6a6176612f7574696c2f4d61703c544b3b54563b3e3b04210007000200010009000000010004000500060001000b0000001100010001000000052ab70001b1000000000001000c00000002000d"; }
    function _bootstrapConcurrentHashMap() private pure returns (bytes memory) { return hex"cafebabe00000034003e0a000200030700040c000500060100156a6176612f7574696c2f41627374726163744d61700100063c696e69743e0100032829560700080100106a6176612f6c616e672f4f626a65637409000a000b07000c0c000d000e0100266a6176612f7574696c2f636f6e63757272656e742f436f6e63757272656e74486173684d61700100046b6579730100135b4c6a6176612f6c616e672f4f626a6563743b09000a00100c0011000e01000676616c75657307001301001e6a6176612f6c616e672f4e756c6c506f696e746572457863657074696f6e0a0012000309000a00160c0017001801000475736564010001490a0007001a0c001b001c010006657175616c73010015284c6a6176612f6c616e672f4f626a6563743b295a0a000a001e0c001f002001000466696e64010015284c6a6176612f6c616e672f4f626a6563743b29490a000a00220c00230024010005636865636b010027284c6a6176612f6c616e672f4f626a6563743b4c6a6176612f6c616e672f4f626a6563743b29560a000a00260c0027000601000467726f770700290100226a6176612f7574696c2f636f6e63757272656e742f436f6e63757272656e744d617007002b0100146a6176612f696f2f53657269616c697a61626c65010004436f646501000d537461636b4d61705461626c6507000e010003676574010026284c6a6176612f6c616e672f4f626a6563743b294c6a6176612f6c616e672f4f626a6563743b0100095369676e6174757265010017284c6a6176612f6c616e672f4f626a6563743b2954563b01000b636f6e7461696e734b657901000b7075744966416273656e74010038284c6a6176612f6c616e672f4f626a6563743b4c6a6176612f6c616e672f4f626a6563743b294c6a6176612f6c616e672f4f626a6563743b01000b28544b3b54563b2954563b01000370757401000473697a650100032829490100076973456d70747901000328295a010005636c65617201008b3c4b3a4c6a6176612f6c616e672f4f626a6563743b563a4c6a6176612f6c616e672f4f626a6563743b3e4c6a6176612f7574696c2f41627374726163744d61703c544b3b54563b3e3b4c6a6176612f7574696c2f636f6e63757272656e742f436f6e63757272656e744d61703c544b3b54563b3e3b4c6a6176612f696f2f53657269616c697a61626c653b0021000a000200020028002a00030002000d000e000000020011000e00000002001700180000000b0001000500060001002c0000002100020001000000152ab700012a07bd0007b500092a07bd0007b5000fb1000000000002002300240001002c0000002700020003000000112bc600072cc7000bbb001259b70014bfb100000001002d00000004000208070002001f00200001002c0000003d0002000300000021033d1c2ab40015a200182ab400091c322bb600199900051cac840201a7ffe602ac00000001002d0000000a0003fc00020116fa00050002002700060001002c0000006400040004000000432ab40009be0478bd00074c2ab4000fbe0478bd00074d033e1d2ab40015a2001b2b1d2ab400091d32532c1d2ab4000f1d3253840301a7ffe32a2bb500092a2cb5000fb100000001002d0000000f0002fe001807002e07002e01fa001f0001002f00300002002c0000003e00020003000000212bc7000bbb001259b70014bf2a2bb7001d3d1c9c000701a700092ab4000f1c32b000000001002d0000000b00030cfc000d0145070007003100000002003200010033001c0001002c00000032000200020000001a2bc7000bbb001259b70014bf2a2bb7001d9b000704a7000403ac00000001002d0000000600030c0b40010001003400350002002c0000005d00050004000000442a2b2cb700212a2bb7001d3e1d9b000a2ab4000f1d32b02ab400152ab40009bea000072ab700252ab400092ab400152b532ab4000f2a59b400155a0460b500152c5301b000000001002d000000070002fc0017010f00310000000200360001003700350002002c00000068000500050000004f2a2b2cb700212a2bb7001d3e1d9b00152ab4000f1d323a042ab4000f1d2c531904b02ab400152ab40009bea000072ab700252ab400092ab400152b532ab4000f2a59b400155a0460b500152c5301b000000001002d000000070002fc0022010f00310000000200360001003800390001002c0000001100010001000000052ab40015ac000000000001003a003b0001002c00000024000100010000000d2ab400159a000704a7000403ac00000001002d0000000500020b40010001003c00060001002c0000002200020001000000162a07bd0007b500092a07bd0007b5000f2a03b50015b1000000000001003100000002003d"; }

    /// @dev Java 8 minimal owned System; only static native arraycopy is exposed.
    function _bootstrapSystem() private pure returns (bytes memory) { return hex"cafebabe00000034000c0a000200030700040c000500060100106a6176612f6c616e672f4f626a6563740100063c696e69743e0100032829560700080100106a6176612f6c616e672f53797374656d010004436f64650100096172726179636f707901002a284c6a6176612f6c616e672f4f626a6563743b494c6a6176612f6c616e672f4f626a6563743b49492956003100070002000000000002000200050006000100090000001100010001000000052ab70001b1000000000109000a000b00000000"; }

    /// @dev Minimal Java 8 Properties family, compiled from the archived guest
    /// sources under bootstrap/java/util. No host property lookup is involved.
    function _bootstrapDictionary() private pure returns (bytes memory) { return hex"cafebabe0000003400150a000300120700130700140100063c696e69743e010003282956010004436f6465010003676574010026284c6a6176612f6c616e672f4f626a6563743b294c6a6176612f6c616e672f4f626a6563743b0100095369676e6174757265010017284c6a6176612f6c616e672f4f626a6563743b2954563b010003707574010038284c6a6176612f6c616e672f4f626a6563743b4c6a6176612f6c616e672f4f626a6563743b294c6a6176612f6c616e672f4f626a6563743b01000b28544b3b54563b2954563b01000672656d6f766501000473697a6501000328294901003c3c4b3a4c6a6176612f6c616e672f4f626a6563743b563a4c6a6176612f6c616e672f4f626a6563743b3e4c6a6176612f6c616e672f4f626a6563743b0c000400050100146a6176612f7574696c2f44696374696f6e6172790100106a6176612f6c616e672f4f626a656374042100020003000000000005000100040005000100060000001100010001000000052ab70001b1000000000401000700080001000900000002000a0401000b000c0001000900000002000d0401000e00080001000900000002000a0401000f0010000000010009000000020011"; }
    function _bootstrapHashtable() private pure returns (bytes memory) { return hex"cafebabe0000003400460a000e003107003209000d003309000d00340700350a0005003109000d00360a000200370a003800390a000d003a0a000d003b0a000d003c07003d07003e07003f0700400700410100046b6579730100135b4c6a6176612f6c616e672f4f626a6563743b01000676616c75657301000475736564010001490100063c696e69743e010003282956010004436f646501000f726571756972654b657956616c7565010027284c6a6176612f6c616e672f4f626a6563743b4c6a6176612f6c616e672f4f626a6563743b295601000d537461636b4d61705461626c6501000466696e64010015284c6a6176612f6c616e672f4f626a6563743b294907003201000467726f77010003676574010026284c6a6176612f6c616e672f4f626a6563743b294c6a6176612f6c616e672f4f626a6563743b0100095369676e6174757265010017284c6a6176612f6c616e672f4f626a6563743b2954563b01000b636f6e7461696e734b6579010015284c6a6176612f6c616e672f4f626a6563743b295a010003707574010038284c6a6176612f6c616e672f4f626a6563743b4c6a6176612f6c616e672f4f626a6563743b294c6a6176612f6c616e672f4f626a6563743b01000b28544b3b54563b2954563b01000672656d6f766501000473697a650100032829490100076973456d70747901000328295a010005636c65617201008a3c4b3a4c6a6176612f6c616e672f4f626a6563743b563a4c6a6176612f6c616e672f4f626a6563743b3e4c6a6176612f7574696c2f44696374696f6e6172793c544b3b54563b3e3b4c6a6176612f7574696c2f4d61703c544b3b54563b3e3b4c6a6176612f6c616e672f436c6f6e6561626c653b4c6a6176612f696f2f53657269616c697a61626c653b0c001700180100106a6176612f6c616e672f4f626a6563740c001200130c0014001301001e6a6176612f6c616e672f4e756c6c506f696e746572457863657074696f6e0c001500160c004200260700430c004400450c001d001e0c001a001b0c002000180100136a6176612f7574696c2f486173687461626c650100146a6176612f7574696c2f44696374696f6e61727901000d6a6176612f7574696c2f4d61700100136a6176612f6c616e672f436c6f6e6561626c650100146a6176612f696f2f53657269616c697a61626c65010006657175616c730100106a6176612f6c616e672f53797374656d0100096172726179636f707901002a284c6a6176612f6c616e672f4f626a6563743b494c6a6176612f6c616e672f4f626a6563743b494929560021000d000e0003000f001000110003000200120013000000020014001300000002001500160000000b000100170018000100190000002100020001000000152ab700012a07bd0002b500032a07bd0002b50004b1000000000002001a001b000100190000002700020003000000112bc600072cc7000bbb000559b70006bfb100000001001c00000004000208070002001d001e000100190000005900020004000000342bc7000bbb000559b70006bf033d1c2ab40007a2001f2ab400031c324e2d2ba5000b2d2bb600089900051cac840201a7ffdf02ac00000001001c0000001300050cfc000101fc001b07001ffa0001fa00050002002000180001001900000049000500030000003d2ab40003be0568bd00024c2ab40004be0568bd00024d2ab40003032b032ab40007b800092ab40004032c032ab40007b800092a2bb500032a2cb50004b100000000000100210022000200190000003100020003000000152a2bb7000a3d1c9c000701a700092ab400041c32b000000001001c0000000a0002fc000e014507001f00230000000200240001002500260001001900000025000200020000000e2a2bb7000a9b000704a7000403ac00000001001c0000000500020c4001000100270028000200190000006b00030005000000522a2b2cb7000b2a2bb7000a3e1d9b00152ab400041d323a042ab400041d2c531904b02ab400072ab40003bea000072ab7000c2ab400032ab400072b532ab400042ab400072c532a59b400070460b5000701b000000001001c000000070002fc0022010f00230000000200290001002a00220002001900000065000400050000004d2a2bb7000a3d1c9c000501b02ab400041c324e2ab40007046436042ab400031c2ab40003150432532ab400041c2ab40004150432532ab40003150401532ab40004150401532a1504b500072db000000001001c000000060001fc000c0100230000000200240001002b002c000100190000001100010001000000052ab40007ac000000000001002d002e0001001900000024000100010000000d2ab400079a000704a7000403ac00000001001c0000000500020b40010001002f0018000100190000003f0003000200000024033c1b2ab40007a200172ab400031b01532ab400041b0153840101a7ffe72a03b50007b100000001001c000000090002fc000201fa001b00010023000000020030"; }
    function _bootstrapProperties() private pure returns (bytes memory) { return hex"cafebabe0000003400280a0008001a0a0009001b090008001c0a0009001d07001e0a0008001f0a0008002007002107002201000864656661756c74730100164c6a6176612f7574696c2f50726f706572746965733b0100063c696e69743e010003282956010004436f6465010019284c6a6176612f7574696c2f50726f706572746965733b295601000b67657450726f7065727479010026284c6a6176612f6c616e672f537472696e673b294c6a6176612f6c616e672f537472696e673b01000d537461636b4d61705461626c6507002307001e010038284c6a6176612f6c616e672f537472696e673b4c6a6176612f6c616e672f537472696e673b294c6a6176612f6c616e672f537472696e673b01000b73657450726f7065727479010038284c6a6176612f6c616e672f537472696e673b4c6a6176612f6c616e672f537472696e673b294c6a6176612f6c616e672f4f626a6563743b0100095369676e617475726501003b4c6a6176612f7574696c2f486173687461626c653c4c6a6176612f6c616e672f4f626a6563743b4c6a6176612f6c616e672f4f626a6563743b3e3b0c000c000f0c000c000d0c000a000b0c002400250100106a6176612f6c616e672f537472696e670c001000110c002600270100146a6176612f7574696c2f50726f706572746965730100136a6176612f7574696c2f486173687461626c650100106a6176612f6c616e672f4f626a656374010003676574010026284c6a6176612f6c616e672f4f626a6563743b294c6a6176612f6c616e672f4f626a6563743b010003707574010038284c6a6176612f6c616e672f4f626a6563743b4c6a6176612f6c616e672f4f626a6563743b294c6a6176612f6c616e672f4f626a6563743b002100080009000000010004000a000b000000050001000c000d0001000e0000001200020001000000062a01b70001b1000000000001000c000f0001000e00000016000200020000000a2ab700022a2bb50003b1000000000001001000110001000e0000004500020003000000262a2bb700044d2cc100059900082cc00005b02ab40003c7000701a7000b2ab400032bb60006b00000000100120000000d0003fc00120700130a470700140001001000150001000e0000002e00020004000000102a2bb600064e2dc700072ca700042db00000000100120000000c0002fc000e070014400700140001001600170001000e0000001300030003000000072a2b2cb60007b00000000000010018000000020019"; }

    function _bootstrapObject() private pure returns (bytes memory) {
        return hex"cafebabe0000003400090700020100106a6176612f6c616e672f4f626a6563740100063c696e69743e010003282956010004436f6465010006657175616c73010015284c6a6176612f6c616e672f4f626a6563743b295a01000d537461636b4d61705461626c65002100010000000000000002000100030004000100050000000d0000000100000001b1000000000001000600070001000500000022000200020000000b2a2ba6000704a7000403ac0000000100080000000500020940010000";
    }

    function _bootstrapCloneable() private pure returns (bytes memory) {
        return hex"cafebabe0000003400050700020100136a6176612f6c616e672f436c6f6e6561626c650700040100106a6176612f6c616e672f4f626a6563740601000100030000000000000000";
    }

    function _bootstrapSerializable() private pure returns (bytes memory) {
        return hex"cafebabe0000003400050700020100146a6176612f696f2f53657269616c697a61626c650700040100106a6176612f6c616e672f4f626a6563740601000100030000000000000000";
    }

    function _bootstrapFloat() private pure returns (bytes memory) {
        return hex"cafebabe00000034000e0a000200030700040c000500060100106a6176612f6c616e672f4f626a6563740100063c696e69743e01000328295607000801000f6a6176612f6c616e672f466c6f6174010004436f646501000e696e7442697473546f466c6f617401000428492946010011666c6f6174546f526177496e744269747301000428462949003100070002000000000003000200050006000100090000001100010001000000052ab70001b1000000000109000a000b00000109000c000d00000000";
    }

    function _bootstrapDouble() private pure returns (bytes memory) {
        return hex"cafebabe00000034000e0a000200030700040c000500060100106a6176612f6c616e672f4f626a6563740100063c696e69743e0100032829560700080100106a6176612f6c616e672f446f75626c65010004436f64650100106c6f6e6742697473546f446f75626c65010004284a2944010013646f75626c65546f5261774c6f6e67426974730100042844294a003100070002000000000003000200050006000100090000001100010001000000052ab70001b1000000000109000a000b00000109000c000d00000000";
    }

    function _bootstrapThrowable() private pure returns (bytes memory) {
        return hex"cafebabe00000034001b0a000500150900040016090004001707001807001907001a01000d64657461696c4d6573736167650100124c6a6176612f6c616e672f537472696e673b01000563617573650100154c6a6176612f6c616e672f5468726f7761626c653b0100063c696e69743e010003282956010004436f6465010015284c6a6176612f6c616e672f537472696e673b295601000a6765744d65737361676501001428294c6a6176612f6c616e672f537472696e673b010008676574436175736501001728294c6a6176612f6c616e672f5468726f7761626c653b01000d537461636b4d61705461626c650700180c000b000c0c0009000a0c000700080100136a6176612f6c616e672f5468726f7761626c650100106a6176612f6c616e672f4f626a6563740100146a6176612f696f2f53657269616c697a61626c65002100040005000100060002000200070008000000020009000a000000040001000b000c0001000d00000016000200010000000a2ab700012a2ab50002b1000000000001000b000e0001000d0000001b000200020000000f2ab700012a2ab500022a2bb50003b1000000000001000f00100001000d0000001100010001000000052ab40003b0000000000001001100120001000d0000002a00020001000000112ab400022aa6000701a700072ab40002b00000000100130000000700020c430700140000";
    }

    function _bootstrapError() private pure returns (bytes memory) {
        return hex"cafebabe00000034000a0a000200030700040c000500060100136a6176612f6c616e672f5468726f7761626c650100063c696e69743e01000328295607000801000f6a6176612f6c616e672f4572726f72010004436f6465002100070002000000000001000100050006000100090000001100010001000000052ab70001b1000000000000";
    }

    function _bootstrapVirtualMachineError() private pure returns (bytes memory) {
        return hex"cafebabe00000034000a0a000200030700040c0005000601000f6a6176612f6c616e672f4572726f720100063c696e69743e01000328295607000801001d6a6176612f6c616e672f5669727475616c4d616368696e654572726f72010004436f6465042100070002000000000001000100050006000100090000001100010001000000052ab70001b1000000000000";
    }

    function _bootstrapStackOverflowError() private pure returns (bytes memory) {
        return hex"cafebabe00000034000a0a000200030700040c0005000601001d6a6176612f6c616e672f5669727475616c4d616368696e654572726f720100063c696e69743e01000328295607000801001c6a6176612f6c616e672f537461636b4f766572666c6f774572726f72010004436f6465002100070002000000000001000100050006000100090000001100010001000000052ab70001b1000000000000";
    }

    function _bootstrapOutOfMemoryError() private pure returns (bytes memory) {
        return hex"cafebabe00000034000a0a000200030700040c0005000601001d6a6176612f6c616e672f5669727475616c4d616368696e654572726f720100063c696e69743e01000328295607000801001a6a6176612f6c616e672f4f75744f664d656d6f72794572726f72010004436f6465002100070002000000000001000100050006000100090000001100010001000000052ab70001b1000000000000";
    }

    function _bootstrapLinkageError() private pure returns (bytes memory) {
        return hex"cafebabe00000034000a0a000200030700040c0005000601000f6a6176612f6c616e672f4572726f720100063c696e69743e0100032829560700080100166a6176612f6c616e672f4c696e6b6167654572726f72010004436f6465002100070002000000000001000100050006000100090000001100010001000000052ab70001b1000000000000";
    }

    function _bootstrapExceptionInInitializerError() private pure returns (bytes memory) {
        return hex"cafebabe0000003400120a0004000e090003000f070010070011010009657863657074696f6e0100154c6a6176612f6c616e672f5468726f7761626c653b0100063c696e69743e010003282956010004436f6465010018284c6a6176612f6c616e672f5468726f7761626c653b295601000c676574457863657074696f6e01001728294c6a6176612f6c616e672f5468726f7761626c653b01000867657443617573650c000700080c000500060100256a6176612f6c616e672f457863657074696f6e496e496e697469616c697a65724572726f720100166a6176612f6c616e672f4c696e6b6167654572726f720021000300040000000100020005000600000004000100070008000100090000001100010001000000052ab70001b10000000000010007000a0001000900000016000200020000000a2ab700012a2bb50002b1000000000001000b000c000100090000001100010001000000052ab40002b0000000000001000d000c000100090000001100010001000000052ab40002b0000000000000";
    }

    function _bootstrapIncompatibleClassChangeError() private pure returns (bytes memory) {
        return hex"cafebabe00000034000a0a000200030700040c000500060100166a6176612f6c616e672f4c696e6b6167654572726f720100063c696e69743e0100032829560700080100266a6176612f6c616e672f496e636f6d70617469626c65436c6173734368616e67654572726f72010004436f6465002100070002000000000001000100050006000100090000001100010001000000052ab70001b1000000000000";
    }

    function _bootstrapNoClassDefFoundError() private pure returns (bytes memory) {
        return hex"cafebabe00000034000a0a000200030700040c000500060100166a6176612f6c616e672f4c696e6b6167654572726f720100063c696e69743e01000328295607000801001e6a6176612f6c616e672f4e6f436c617373446566466f756e644572726f72010004436f6465002100070002000000000001000100050006000100090000001100010001000000052ab70001b1000000000000";
    }

    function _bootstrapAbstractMethodError() private pure returns (bytes memory) {
        return hex"cafebabe00000034000a0a000200030700040c000500060100266a6176612f6c616e672f496e636f6d70617469626c65436c6173734368616e67654572726f720100063c696e69743e01000328295607000801001d6a6176612f6c616e672f41627374726163744d6574686f644572726f72010004436f6465002100070002000000000001000100050006000100090000001100010001000000052ab70001b1000000000000";
    }

    function _bootstrapException() private pure returns (bytes memory) {
        return hex"cafebabe00000034000d0a000400090a0004000a07000b07000c0100063c696e69743e010003282956010004436f6465010015284c6a6176612f6c616e672f537472696e673b29560c000500060c000500080100136a6176612f6c616e672f457863657074696f6e0100136a6176612f6c616e672f5468726f7761626c65002100030004000000000002000100050006000100070000001100010001000000052ab70001b100000000000100050008000100070000001200020002000000062a2bb70002b1000000000000";
    }

    function _bootstrapRuntimeException() private pure returns (bytes memory) {
        return hex"cafebabe00000034000a0a000200030700040c000500060100136a6176612f6c616e672f457863657074696f6e0100063c696e69743e01000328295607000801001a6a6176612f6c616e672f52756e74696d65457863657074696f6e010004436f6465002100070002000000000001000100050006000100090000001100010001000000052ab70001b1000000000000";
    }

    function _bootstrapArithmeticException() private pure returns (bytes memory) {
        return hex"cafebabe00000034000a0a000200030700040c0005000601001a6a6176612f6c616e672f52756e74696d65457863657074696f6e0100063c696e69743e01000328295607000801001d6a6176612f6c616e672f41726974686d65746963457863657074696f6e010004436f6465002100070002000000000001000100050006000100090000001100010001000000052ab70001b1000000000000";
    }

    function _bootstrapNullPointerException() private pure returns (bytes memory) {
        return hex"cafebabe00000034000a0a000200030700040c0005000601001a6a6176612f6c616e672f52756e74696d65457863657074696f6e0100063c696e69743e01000328295607000801001e6a6176612f6c616e672f4e756c6c506f696e746572457863657074696f6e010004436f6465002100070002000000000001000100050006000100090000001100010001000000052ab70001b1000000000000";
    }

    function _bootstrapNegativeArraySizeException() private pure returns (bytes memory) {
        return hex"cafebabe00000034000a0a000200030700040c0005000601001a6a6176612f6c616e672f52756e74696d65457863657074696f6e0100063c696e69743e0100032829560700080100246a6176612f6c616e672f4e65676174697665417272617953697a65457863657074696f6e010004436f6465002100070002000000000001000100050006000100090000001100010001000000052ab70001b1000000000000";
    }

    function _bootstrapClassCastException() private pure returns (bytes memory) {
        return hex"cafebabe00000034000a0a000200030700040c0005000601001a6a6176612f6c616e672f52756e74696d65457863657074696f6e0100063c696e69743e01000328295607000801001c6a6176612f6c616e672f436c61737343617374457863657074696f6e010004436f6465002100070002000000000001000100050006000100090000001100010001000000052ab70001b1000000000000";
    }

    function _bootstrapArrayStoreException() private pure returns (bytes memory) {
        return hex"cafebabe00000034000a0a000200030700040c0005000601001a6a6176612f6c616e672f52756e74696d65457863657074696f6e0100063c696e69743e01000328295607000801001d6a6176612f6c616e672f417272617953746f7265457863657074696f6e010004436f6465002100070002000000000001000100050006000100090000001100010001000000052ab70001b1000000000000";
    }

    function _bootstrapIndexOutOfBoundsException() private pure returns (bytes memory) {
        return hex"cafebabe00000034000a0a000200030700040c0005000601001a6a6176612f6c616e672f52756e74696d65457863657074696f6e0100063c696e69743e0100032829560700080100236a6176612f6c616e672f496e6465784f75744f66426f756e6473457863657074696f6e010004436f6465002100070002000000000001000100050006000100090000001100010001000000052ab70001b1000000000000";
    }

    function _bootstrapArrayIndexOutOfBoundsException() private pure returns (bytes memory) {
        return hex"cafebabe00000034000a0a000200030700040c000500060100236a6176612f6c616e672f496e6465784f75744f66426f756e6473457863657074696f6e0100063c696e69743e0100032829560700080100286a6176612f6c616e672f4172726179496e6465784f75744f66426f756e6473457863657074696f6e010004436f6465002100070002000000000001000100050006000100090000001100010001000000052ab70001b1000000000000";
    }


    function _bootstrapIOException() private pure returns (bytes memory) {
        return hex"cafebabe00000034000d0a000400090a0004000a07000b07000c0100063c696e69743e010003282956010004436f6465010015284c6a6176612f6c616e672f537472696e673b29560c000500060c000500080100136a6176612f696f2f494f457863657074696f6e0100136a6176612f6c616e672f457863657074696f6e002100030004000000000002000100050006000100070000001100010001000000052ab70001b100000000000100050008000100070000001200020002000000062a2bb70002b1000000000000";
    }

    function _bootstrapFileNotFoundException() private pure returns (bytes memory) {
        return hex"cafebabe00000034000d0a000400090a0004000a07000b07000c0100063c696e69743e010003282956010004436f6465010015284c6a6176612f6c616e672f537472696e673b29560c000500060c0005000801001d6a6176612f696f2f46696c654e6f74466f756e64457863657074696f6e0100136a6176612f696f2f494f457863657074696f6e002100030004000000000002000100050006000100070000001100010001000000052ab70001b100000000000100050008000100070000001200020002000000062a2bb70002b1000000000000";
    }

    function _bootstrapEOFException() private pure returns (bytes memory) {
        return hex"cafebabe00000034000d0a000400090a0004000a07000b07000c0100063c696e69743e010003282956010004436f6465010015284c6a6176612f6c616e672f537472696e673b29560c000500060c000500080100146a6176612f696f2f454f46457863657074696f6e0100136a6176612f696f2f494f457863657074696f6e002100030004000000000002000100050006000100070000001100010001000000052ab70001b100000000000100050008000100070000001200020002000000062a2bb70002b1000000000000";
    }
}
