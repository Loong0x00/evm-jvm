> CURRENT: AS0 is parent-accepted as a bounded immutable EVM raw-byte store.
> See JAVA_EVM_MC_AS0_REVIEW.md for parent Go fixes, final gates and proof limits.
> Worker candidate/batch-replay observations below are historical, not the sole
> acceptance evidence. No ZIP/ClassLoader/JVM mounting/Minecraft startup is claimed.

# MC-AS0 opaque Go transport (implementation candidate)

This package drives one frozen `AS0ArtifactStore` instance in the unmodified
Cancun EVM. It is **not accepted AS0 evidence by itself** and is not a ZIP
reader, inflater, class catalogue/loader, JVM profile, Minecraft execution,
EULA action, listener, or startup/`Done` claim.

## Pinned surface

The only build input is the runtime package's embedded combined artifact; there
is no source-tree/compiler fallback. With solc 0.8.30, optimizer 200, via-IR,
Cancun and metadata disabled, the current peer artifact has:

- constructor bytecode: 3166 bytes, SHA-256
  `b792253995eafb2ecbc6d7c6c6f28fc0fc03ad0d5073a97f4c62b4ea93dd0f88`;
- fixed deployed runtime: 2831 bytes, SHA-256
  `e7f8e95b0af80bf15e89a01ceb635d8ae858560c606cc86ac3877d8f0de69b13`.

`Runtime`, `InitCode`, and `ABI` return defensive copies. `NewMemory(owner,
length)` and `Open(directory,owner,length)` execute the constructor by ordinary
`runtime.Create`; only that controller can CREATE `STOP || raw` child pages.
There is no Go `SetCode`, page byte map, page import, ZIP interpretation, or
host content authority.

Public operation types/signatures are:

```go
type Creation struct { Performed bool; Controller common.Address; GasUsed uint64; RuntimeCodeHash, StateRoot common.Hash }
type Operation struct { GasUsed uint64; StateRoot common.Hash; Logs []*types.Log; RevertData []byte }
type Page struct { Address common.Address; CodeHash, Commitment common.Hash; GasUsed uint64 }
type Read struct { Bytes []byte; GasUsed uint64 }
type Head struct { /* EVM lifecycle getters, identity/root, summed getter gas */ }

func RuntimeHash() (string, error) // SHA-256 transport/report pin, not EVM authority
func NewMemory(owner common.Address, length uint32) (*Session, error)
func Open(directory string, owner common.Address, length uint32) (*Session, error)
func (*Session) Creation() (Creation, error)
func (*Session) Append(cursor uint32, raw []byte, expectedPi common.Hash, gas uint64) (Operation, error)
func (*Session) Seal(cursor uint32, expectedChain common.Hash, gas uint64) (Operation, error)
func (*Session) Read(offset, length uint32, gas uint64) (Read, error)
func (*Session) Page(index uint64, gas uint64) (Page, error)
func (*Session) Head(gas uint64) (Head, error)
func (*Session) Close() error
```

Gas is always finite in `1..1,000,000,000`. Fresh controller CREATE uses the
ordinary 100M allowance and is reported by `Creation`; after reopen
`Performed=false` means no deployment happened (the zero `GasUsed` is not a
zero-cost CREATE claim). Mutation gas excludes later EVM views. `Head.GasUsed`
is explicitly the sum of its ten separate getter calls. Host-computed expected
Pi/chain values are transport assertions only; the EVM computes commitments
from actual calldata and issued addresses/code.

## Durable format

Disk format 1 is identified by exactly
`JVMEVM-MC-AS0-DISK-STORE-1\n`. The strict JSON manifest binds format, fixed dev
context, owner, controller, declared length, pinned runtime code hash, and the
committed state root. Metadata and fixed top-level entry types are checked
before LevelDB is opened. A requested root alias may resolve; links inside the
store are refused. Reads of marker/manifest are regular-file and size bounded.

Every successful append and seal synchronously commits trie **and code**, syncs
the key-value store, writes/fsyncs an owned manifest temporary, atomically
renames it, and fsyncs the directory. Pre-publication failure reloads the prior
published root. Failure after rename poisons the session until reopen because
publication is ambiguous. Publication failures return diagnostic gas only—no
success root, page, event, or bytes. Owned unpublished manifest temporaries and
unrelated files are preserved rather than treated as authority or deleted.
An interrupted initial nonempty layout without a manifest fails closed and is
not wiped or assigned an invented root.

Views execute against a copied `StateDB`; their returned bytes/metadata come
from EVM ABI calls and cannot mutate publication authority. Reopen loads the
manifest root, checks exact controller code and calls EVM identity/limit/getter
methods. It never redeploys the controller or recreates pages.

## Limits and evidence boundary

Constants are 8192-byte pages, 4096 pages, 33,554,432 total bytes, and 4096
bytes per read. Ordinary tests use at most 100M gas/call; explicit boundary
calls may use 1B. Full generated 32MiB memory and per-append-durable disk gates
remain bounded by the frozen external 20-minute/4GiB watchdog. Summed upload gas
must be reported separately from maximum per-call gas.

All fixtures are trusted generated opaque bytes. Their host hashes only check
transport identity; they do not establish an official whole-JAR SHA-256, and
no fixture bytes are executed or interpreted as a JAR/class/resource.

## Harness measurement at peer runtime `655bdfe21`

The full package gate was run with an external 1200-second/4GiB process-group
watchdog:

```sh
python3 build/java-diff-mc-as0-harness/watch.py 1200 4294967296 \
  build/java-diff-mc-as0-harness/full-watch.json bash -c \
  'go test -count=1 -v ./jvmevm/artifactstore/as0 > \
   build/java-diff-mc-as0-harness/full.log 2>&1'
go vet ./jvmevm/artifactstore/as0
```

It passed in 2.877s at 286,056,448 bytes peak group RSS. Both memory and disk
controls uploaded all 33,554,432 generated bytes in 4096 calls and sealed. Each
reported controller CREATE 611,673 gas, summed append gas 7,289,399,396,
maximum single append 1,830,926 gas, seal 34,194 gas, and the measured 4096-byte
cross-page read 24,835 gas. These sums cover many calls and are not one-call or
instruction-count claims. Every disk append was individually committed and
manifest-published; the test closed at page 2048, resumed/sealed in another
process, then reopened/read in the original process without child recreation.

The memory final state root was
`0x13b09aaa76659801fdaed2731b9ad81dc70618b472ea18cc996f8d1f835e58f6`.
The distinct-owner disk final state root was
`0x8bb74da2d592c2ebc7c9859bf98448f5f9ee257eb68ead79d728b9a9b12cc18e`
and sealed EVM content commitment was
`0xe0a22812f4fcc785f3c05ac4125b4b7d4f79bdcd04f515ab011189d672fbb1bf`.
Tests also pin exact `AS0Error` precedence/codes 2/3/4/5/8/9/10 plus EVM view
bounds 11/13, unsealed read 12 through the small controls, post-CREATE wrong-Pi
and OOG rollback/retry address, full-before-seal empty-append rejection, exact
partial/full page counts, copied views, strict manifest identity, initial
fail-closed handling, root aliases/internal-link refusal, prepublication old-root
retry, and ambiguous post-rename poisoning/reopen. Runtime/parent independent
review remains required; these results do not claim AS0 acceptance.
