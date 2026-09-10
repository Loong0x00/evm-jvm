# MC-ZI0 opaque transport

This package is the Go transport for the frozen `ZI0ZipIndex` EVM artifact. It
creates one accepted AS0 store and, after sealing, one ZI0 controller in the
same StateDB/trie. All ZIP directory decisions remain in EVM bytecode: Go only
packs ABI calls, transports opaque bytes, commits/reloads state, and exposes
copied getter results.

`NewMemory` and `Open` initially create/open only AS0. Upload uses separate
`Append` and `Seal` calls; `CreateIndex` is a separate ordinary EVM CREATE.
`Discover`, `Scan`, and `Finish` are exact CAS operations. Disk publication is
format-1 metadata plus synchronously committed trie/code and atomic manifest
replacement. Runtime assets are embedded by `zi0/runtime`; no compiler,
filesystem artifact, host ZIP parser, or prototype fallback is used here.

The package is implementation work and is not itself ZI0 acceptance evidence.
Final artifact hashes, runtime availability, and the sixteen parent gates are
owned by the parent integration.
