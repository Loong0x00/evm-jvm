# Preparation-cost attribution preflight (COPY-only)

**Original worker measurement draft, retained below.** Parent verified/further
resolved allocation costs in JAVA_EVM_MC_PREPARATION_COST_PARENT_PREFLIGHT.md.
Named bucket0 does not itself exclude semantic phases; no optimization/acceptance. This is a bounded
COPY of the capacity-baseline prototype at `ea1fa2c8a`. Accepted CB0 remains four
classes / 65536 bytes. The COPY-only 8 / 262144-byte transport is not promoted.

## Question and boundaries

The measurement attributes the dense three-image ordinary refusal, rather than
assuming its `74874471`-gas receipt identifies a Solidity function. It compares the
known cheap padded 262144-byte positive (result 17, `7879725` gas), the method-rich
BigCaller+BigEntry positive (result 15, `48451006` gas), and BigPair+BigEntry+
BigTwin (`181969` class bytes, result 23 only at explicitly labelled 1B boundary).
It uses the normal owned COPY transport: AS0 -> ZI0 -> DI0 FINAL reads -> copied
coordinator -> copied VFS runtime. No class bytes are decoded, parsed, inflated, or
executed by the host.

Only a freshly generated ignored `build/java-diff-mc-capacity-cost-*` tree is
modified. It contains copied Go observer code that installs Geth read-only
`tracing.Hooks`, and copied compiler recipes requesting source maps/AST/generated
sources. It does not change Solidity source, EVM input, state, events, storage,
limits, COMMIT_RESERVE, opcode semantics, or gas. The traced and untraced calls use
identical compiled runtime bytes and package/world inputs; trace wall time is not a
runtime-performance result.

## Attribution method

The observer records aggregated `(contract address, PC)` execution count and opcode
cost, plus call-frame enter/exit records. PC decoding advances by one opcode plus
`PUSH1..PUSH32` immediate widths (including `PUSH0` as width zero), and source maps
are decoded against those instruction PCs. A source span/function name is a location
attribution only: via-IR spans can be shared, inlined, synthetic, or unmapped and do
not prove a unique semantic phase. Results retain unmapped/ambiguous cost separately.

Opcode-cost aggregates are *exclusive bytecode work*: a CALL-family opcode's own
cost remains in its caller, while the callee's opcodes are in its own address/frame.
Forwarded CALL gas is never added to child gas. Frame `OnExit` gas is inclusive and
is reported separately. Root gas, all-PC cost total, frame records, reverts, and any
refund/unknown residual are reconciled rather than assuming a sum of frame gas.

The normal ordinary 100M/30s observation is mandatory; the existing 1B/120s
boundary direct/resume observations, if replayed, remain labelled BOUNDARY ONLY and
never alter ordinary acceptance.

## Evidence

The reproducible copied-build/trace driver and immutable raw outputs are under
`evidence/java-evm/preparation-cost/preflight/`. It must preserve raw command
stdout/stderr and watchdog data before cleanup. Its compile receipt must show
solc `0.8.30+commit.73712a01.Emscripten.clang`, optimizer runs 200, viaIR, Cancun,
and metadata disabled, and prove the VFS runtime SHA-256 remains
`4a7f61989c5ec68edbee96d34cd97c7f0f54f26ffc30d8b351247bd26839f86f`.

## Run `20260912T174003`

`evidence/java-evm/preparation-cost/preflight/run-20260912T174003/report.json`
contains the aggregate-PC report and compressed raw aggregate receipts. The fresh
COPY compiled the unchanged runtime to exactly **292968 bytes** / SHA-256
`4a7f61989c5ec68edbee96d34cd97c7f0f54f26ffc30d8b351247bd26839f86f` and
coordinator to **3792 bytes** / SHA-256
`1fc9cc6be252cc9256e280fb2a5669fbdd6a92a03955639d83ddc5173f365363`.
The debug query used the pinned compiler, optimizer 200, viaIR, Cancun,
`appendCBOR:false`, `bytecodeHash:none`, plus `ast`, source maps, and generated
sources. Those debug products did not affect the deployed bytes.

| opaque package / ordinary result | receipt gas | exclusive-PC sum |
|---|---:|---:|
| padded 262144B, result 17 | 7,879,725 | 7,879,725 |
| BigCaller+BigEntry, result 15 | 48,451,006 | 48,451,006 |
| BigPair+BigEntry+BigTwin 181969B, LC0ControlError7 | 74,874,471 | 74,874,471 |

For all three rows, `comparison.json` checks the parent untraced receipt's gas,
revert/result, roots, head, slice/counters, checkpoint fields and logs exactly.
Thus the read-only trace did not change the observed result. It is **not** a wall
clock comparison. The dense trace is a real revert, not OOG: root coordinator
frame used 74,874,471 gas and the reverted engine frame used 73,073,563 gas.

### Dense cost attribution

The observer saw 29,290 aggregate PC entries (not per-instruction rows). Raw hook
cost including forwarded calls is 7,125,909,910 gas; 7,051,035,439 is recorded as
forwarded call gas and must not be summed with child work. Subtraction yields the
74,874,471 exclusive-PC sum exactly. The sum of inclusive `OnExit` frame uses is
148,402,622 and is deliberately not used as an additive total. No residual remains
after exclusive reconciliation; the hook does not independently expose a StateDB
refund counter, so this says only that receipt gas reconciles, not that refunds have
a separate measured semantic allocation.

Source-map attribution is intentionally limited. **51,143,120 gas (68.31%)** maps
to VFS source spans that solc/viaIR labels only as a whole-contract span (not a
unique function); its largest PC is VFS PC 116216, 3,684,738 gas / 221 executions,
and PC 146470, 1,353,491 / 2556. These are real hot PCs but are *not* identified as
a semantic phase. A further 1,427,965 gas (1.91%) is unmapped VFS code and 454,588
(0.61%) is DI0/other dependency code without a requested source map.

Named source-map groups provide the defensible lower-bound phase evidence:

| VFS named helper in dense refusal | gas | receipt share | BigEntry pair gas |
|---|---:|---:|---:|
| `_u2` metadata reads | 6,107,556 | 8.16% | 3,223,260 |
| `_parseBundleClass` | 3,071,292 | 4.10% | 1,580,129 |
| `_equals` reference/name comparisons | 2,894,278 | 3.87% | 1,523,513 |
| `_validUtf8` metadata/name validation | 2,402,100 | 3.21% | 1,230,426 |
| `_skip` | 1,520,078 | 2.03% | 796,768 |
| `_readConstantPool` | 1,079,215 | 1.44% | 652,474 |
| `_u4` | 797,392 | 1.06% | 409,336 |
| `_resolveCall` reference selection | 520,306 | 0.69% | 1,040,397 |
| coordinator `_loadAll` | 50,426 | 0.07% | 29,336 |

The dense start reverts before a returned checkpoint, so source-mapped
`_restoreSelection`, `_validateRestoredReferences`, `_validateInitAndFrames`, and
`_commit` each record zero in this call. This excludes them as an observed dense
*start* hotspot, but does not make a claim about resume. The 26,423,465-gas dense
minus one-BigEntry difference is therefore partly quantified by repeated named
metadata/parser/reference helpers, while its majority remains compiler-span
ambiguous. Aggregate gas alone cannot select an optimization target.

PC decoding pairs the deployed bytecode instruction stream with source-map entries,
advancing one byte per opcode plus `PUSH1..PUSH32` immediate widths (and zero-width
`PUSH0`). The run script contains the exact solc output-selection recipe; `analyze.py`
decodes inherited source-map fields and chooses only an innermost AST
`FunctionDefinition` containing a span. Whole-contract, synthetic, shared/inlined,
and absent spans remain explicitly ambiguous/unmapped.

## Candidate next step (not implementation)

The smallest justified follow-up is a separate COPY-only **metadata-read preflight**:
cache or bound one already-validated class parser metadata representation keyed by
its existing EVM resource root, then measure only cold start, same-process repeat,
and disk reopen against the named `_u2`/`_parseBundleClass`/constant-pool groups.
It must prove equal roots/results and account for cache validation/publication cost;
it must not assume the 68.31% ambiguous span belongs to that cache. This is neither
a demand loader nor a capacity promotion, ClassLoader claim, or production rewrite.
