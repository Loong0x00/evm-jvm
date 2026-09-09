# LOCAL MC-LC0 continuation transport

Package `lc0` is the bounded Go transport for the frozen MC-LC0 runtime. It:

* loads the compiler-checked ABI/runtime/provenance artifact embedded by
  `jvmevm/runtime/local/lc0/assets.go`; no source-tree artifact path is required;
* explicitly installs the oversized runtime code once into a fixed LOCAL
  StateDB account (this is **not** CREATE or standard-deployment proof);
* uses `runtime.Call` with a nonzero owner, zero value, and reproducible dev-chain
  context for every `start`, `resume`, and `head` call;
* ABI-packs unchanged class bytes, entry strings, signed `int32` arguments, and
  opaque checkpoint bytes, and decodes only the outer `SliceResult`/`Head` ABI;
* keeps checkpoints as hash-checked opaque blobs. Production Go has no Java,
  machine-stream, classfile, heap, frame, or metadata decoder.

`Open` accepts an empty directory for initialization or an existing directory
containing exactly this store format. It refuses unrelated nonempty directories.
Durability publication order is checkpoint write+fsync, StateDB/trie commit+sync,
then atomic manifest replacement+directory fsync. The prior trie root remains
loadable. A failure before manifest publication reloads the prior durable root;
a failure after rename with an ambiguous directory fsync poisons the session and
requires close/reopen rather than claiming rollback. Reopen verifies owner,
context, code hash, committed code, and trie root and never reinstalls code or
injects a head. Failed publication returns only diagnostic gas, never speculative
slice/checkpoint/log output. Store metadata is checked before opening LevelDB;
owned unpublished manifest temporaries are preserved and ignored. Existing orphan
blobs are synced again before publication. Reads are bounded and internal linked
entries are refused; explicitly requested store-root aliases are resolved first.
This is not isolation against another process concurrently replacing store paths.

Acceptance and retained parent findings: `JAVA_EVM_MC_LC0_REVIEW.md`.

The profile remains LOCAL: ordinary tests use at most 100,000,000 gas and boundary
calls at most 1,000,000,000 gas, with external 30/120-second watchdogs. The EVM gas
limit is enforced in-process; callers running adversarial or boundary work should
also use a subprocess watchdog and 4 GiB memory limit. There is no RPC, P2P, VFS,
Minecraft startup, EULA, or listener surface here.
