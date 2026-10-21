# P34 authenticated selected-method dependency preflight

## Scope and trust boundary

This folder adds a disposable, read-only EVM diagnostic for one **explicit** bound
class resource and one **explicit** classfile method-index/PC window. It is not an
interpreter optimization, a guest Java result, a loader, or a continuation path.
It never calls `startMain`/`resumeMain`, executes a guest method, mutates the
coordinator/package, creates a checkpoint, searches the whole ZIP, or treats an
observed class reference as proof that the guest loads/needs it. Original JARs,
classes, resources, worlds, heads, checkpoints, and original receipts are neither
inputs nor present here. All class/ZIP data in this folder is a small generated
Java 8 test fixture.

The only frozen execution baseline used is
`../performance-base-p34/`. `run_generated.py` verifies every path/size/SHA-256
in that folder's `SOURCE_MANIFEST.json` before testing. Its Go helper installs
only the pinned P34 engine runtime as the coordinator constructor's code-hash
anchor; it does not invoke the engine. It uses the repository's AS0/ZI0/DI0
artifact-store packages to CREATE and populate a generated-only EVM world, then
CREATEs the pinned ordinary coordinator and this diagnostic. Every diagnostic
call is an EVM `STATICCALL`. No parent checkpoint/session is opened or reused.

## Parent-facing artifact and API

`BindingMethodInspector.json` contains the compiler-pinned ABI, init bytecode,
runtime template, source SHA-256, and template code hashes. It is built with
`solc 0.8.30+commit.73712a01`, optimizer runs 1, via-IR, Cancun, and no metadata
hash. Source SHA-256 is `fc648c4a2135a24000bc2f03fc13f0beb88533a70cbbe1220a3155b95913dc96`;
runtime template SHA-256/Keccak-256 are
`2e9e22b5a4ce89de162c86524797b2853c425e0c5d02ced6a875716e576ca5cf` /
`cb7a23c5473fd500b2b10856252109263ee033729d3f5e7f276f9ce5ad251edb`. The
init/runtime templates are 18,604/18,117 bytes; the runtime is below ordinary
EIP-170. Constructor immutables change the deployed runtime hash per world. Its constructor is:

```text
(address coordinator, bytes32 coordinatorCodeHash, bytes32 packageRoot)
```

Create it in a fresh successful-world COPY, passing the exact coordinator address,
`EXTCODEHASH(coordinator)`, and `coordinator.packageRoot()` from that copy. The
immutable anchors bind the diagnostic to that one coordinator/package. The view
entry point is:

```text
inspect(uint8 binding, uint16 methodIndex,
        uint32 pcStart, uint32 pcEnd, uint16 maxResults)
    returns (ScanResult)
```

`binding` is the ordinary coordinator's zero-based `classBinding(uint8)` index;
`methodIndex` is the zero-based classfile method-table index. `pcEnd` is exclusive.
Both PC endpoints must be instruction boundaries. `maxResults` must be 1..128.
The result carries the binding name, declaring class, selected method/name/
descriptor/index, requested PC window, decoded instruction/switch/wide counts,
class-byte Keccak, package/index/resource roots, coordinator address/code hash,
and references. Every reference gives methodIndex, PC, opcode/opcode byte, an
explicit provenance string, constant-pool index/tag, and either the owner/member/
descriptor or referenced type name. Byte strings are returned without host
normalization; the helper prints readable text and lossless hex.

The call rechecks coordinator code hash, package root, owner, final index root, and
ordinary `classBinding` output. It then checks the bound decoder's exact DI0 code
hash, owner, phase 4, index root, plain size, and final root before copying bytes
from `DI0.read` in chunks of at most 4,096 bytes. It verifies the classfile's
`this_class` name matches the coordinator resource name with `.class` removed.

Finite diagnostic bounds are explicit: a 1..262,144-byte class, at most 8,192
constant-pool slots, at most 2,048 interfaces/fields/methods/attribute entries,
classfile Code length at most 65,535 bytes, and at most 128 returned references.
The entire selected method's Code is decoded to validate widths/boundaries and
branch destinations, but only references within the caller's PC window are
returned. `tableswitch`/`lookupswitch` alignment and payload sizes, `wide`, all
standard instruction widths, constant-pool operand tags, branch boundaries, and
truncation/reserved opcodes are checked in the EVM. This is a bounded dependency
scanner, not a complete JVM bytecode verifier: it does not validate every
verification rule, stack map, descriptor grammar, bootstrap linkage, or runtime
class-availability condition.

The output is **static candidate metadata only**. A constant-pool owner/type,
member descriptor, or call-site is not evidence that it executes, is required,
missing at runtime, or should be automatically added to a package. The parent must
select any candidate classes explicitly, use an independent generated/JVM oracle
where appropriate, and then perform a fresh precise q1 equivalence replay. Do not
filter candidates automatically against a host-side original ZIP catalogue.

## Generated fixture coverage

`fixtures/src/scan/` compiles with `javac --release 8 -g:none`. The generated
`Probe.class` contains `<clinit>`, constructors, field reads/writes, `new`, array
creation, casts, `instanceof`, class literals, virtual/static/interface calls,
`tableswitch`, `lookupswitch`, a 260+ local wide method, a `sipush` whose operand
bytes resemble invocation opcodes, and a 5KB string literal. The class is 8,349
bytes to exercise three DI0 reads (4,096 + 4,096 + 157). Additional explicit ZIP
entries are a 19-byte truncation and valid `Helper.class` bytes intentionally
bound under `scan/WrongName.class`.

The test compares every reported generated-fixture `(methodIndex, PC, opcode,
constant-pool index/tag, owner/member/descriptor/type)` against `javap -v -p -c
-s` output and the fixture-only constant-pool oracle. It also checks decoded
instruction counts, switch counts, wide instructions, exact resource roots/sizes,
chunk limits, and that all diagnostic STATICCALLs preserve the EVM state root.
Negative controls cover truncated bytes, resource/class-name mismatch, a PC endpoint
inside an operand, an undersized output cap, an invalid binding, mismatched
constructor package/code-hash anchors, modified coordinator/DI0 code hashes, and
isolated forged-copy mutations of coordinator owner/package/index-root and DI0
owner/phase/index-root/plain-size/final-root. Forged storage mutations are
**test-only copied-state controls**; they never feed a successful result or change
the genuine generated world.

## Reproduction and recorded result

From the repository root:

```sh
node evidence/java-evm/minecraft-entry/perf-evm-dependency-preflight/build.js --check
go test ./evidence/java-evm/minecraft-entry/perf-evm-dependency-preflight/tools
python3 evidence/java-evm/minecraft-entry/perf-evm-dependency-preflight/run_generated.py \
  --summary evidence/java-evm/minecraft-entry/perf-evm-dependency-preflight/results/<fresh-run-name>.json
```

The fixture generator creates only `fixtures/generated/`; pass
`--rebuild-generated` only when intentionally regenerating these generated-only
class/ZIP/javap inputs. Summary paths are append-only in practice: use a fresh name
for a new run. The helper and Python oracle accept no external class/archive path
as a binding source; the six generated bindings are a literal list in the script.

`results/strict-final.json` records the final run: all 13 frozen P34
source-manifest files verified; 14 selected methods and 1,123 decoded instructions
crosschecked; 18 reference rows exactly matched generated `javap`; 15 negative
diagnostic controls plus two constructor refusal checks passed; all three class
reads were at most 4,096 bytes; the largest EVM call used 38,517,629 gas. Ordinary
world/setup/query calls used 149,828,714 gas; forged-storage guard probes used
64,940,923; remaining negative probes used 39,787, totaling 214,809,424 below the
initial 1,000,000,000 test budget in 5.564s. No test-budget shortage occurred, so
no budget was doubled. This is fixture/tool verification only, not original-JAR
evidence, performance-equivalence acceptance, a Minecraft run, or guest completion.
