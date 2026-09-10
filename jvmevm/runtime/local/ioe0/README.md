# MC-IOE0 local IOException continuation runtime

`IOException0Interpreter.sol` is the schema-1 IOE0 successor to accepted MC-SC0.
It is derived from accepted SC0 source SHA-256
`c983cd99ea1cb2139d978508ebc3fd935cdb28453bd0b3be46c19bee5d169a38`;
no accepted runtime or bootstrap file is modified.

IOE0 retains SC0's four-method/13-field ABI, quotas, finite 100M ordinary and 1B
boundary gas profiles, 25M commit reserve, 1 MiB checkpoint ceiling, String
semantics, one authoritative heap, and durable continuation controls. It uses the
distinct `JVMIOE01`/`IES1` envelope/machine namespace and 30-image bootstrap root.
The first 24 SC0 images are byte-identical; only Throwable, Exception and
ExceptionInInitializerError are substituted, and IOException,
FileNotFoundException and EOFException are appended after String.

The pinned Java Code implements constructor-supplied Throwable/IOException
messages and canonical getters. VM-origin objects retain arena identity and quota
accounting, initialize `Throwable.cause` to self and `detailMessage` to null, and
EIIE wrappers store their cause only in the canonical `exception` field. The IOE0
codec has no wrapper-cause side table. Unsupported VM-origin getter combinations
hard-fail with `ThrowableAPIProfileError`; in particular implicit VM Arithmetic
`getMessage()` does not fabricate `/ by zero`, null, or a host message.

Pinned source/class provenance for the six substituted/appended images and the
inherited String image is recorded in `artifacts/IOException0Interpreter.json`.
The six IOE0 images reproduce with Java 8 `javac -source 8 -target 8 -g:none`
(using the build's Java-base patch arrangement); the inherited String pin retains
its accepted `javac --release 8 -g:none` record. `build.js` verifies every source
hash, decoded class length/hash, and embedded Solidity image before compiling.

## Reproducible Solidity build

```sh
npm ci --ignore-scripts
npm run build
npm run check
```

The build pins solc `0.8.30+commit.73712a01.Emscripten.clang`, optimizer 200,
via-IR, Cancun, and disabled metadata. Accepted artifact: source SHA-256
`de0a45a5911f5e792aa69f776096a78afaf11e246b7b53d5cf67f9b7a1df7086`;
runtime 233286 bytes, SHA-256
`507ed54d56d4cbe5e559013fbf5a3e598d75a28c0ffe33735573f646eac659a0`.
The oversized runtime is for explicit LOCAL code installation, not CREATE or
standard-chain deployment evidence. This library slice is not VFS, file/stream
support, logging, scheduling, a listener, Minecraft startup, or EULA execution.
Parent acceptance, independent gates and precise limitations are recorded in
`JAVA_EVM_MC_IOE0_REVIEW.md`.
