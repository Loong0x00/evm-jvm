# BENCHMARK_RESULT — EnumSet recovery continuation

## Result

Recovered the terminated `enum-set-preflight` candidate, retained and converged its
coherent design, and completed the single official engine build **under the fixed
384 KiB runtime cap**:

- engine runtime **393027 B ≤ 393216 B** (headroom 189 B), solc 0.8.30 viaIR runs=200
- runtime SHA256 `d0e1a7af114a89d7a2184c056ab9cca7b08de6b8f9e2277a9120a58e9c93d8c6`
- runtime Keccak `049e0d6a481e702b650bb120f3fa49aee5df976d8cdf3f8200f8c514cc06e521`
- coordinator rebuilt and re-pinned: 4146 B, Keccak
  `4db069a0f62bb2418143dae88b1fc0d5c9f76997129a9cf3594712113e700848`, domain
  `MC-ENUM-SET-PARENT1`

The terminated draft allocated a snapshot `Object[]` from the enum's ACC_ENUM fields on
every `allOf` call and measured **393821 B (+605 B over the cap)**. The converged design
keeps the same append-only image and native binding but returns the enum class's own
already-published static synthetic constant table (`$VALUES`) — the same table Java 8's
`Class.getEnumConstantsShared()` returns for the measured `EnumSet.allOf` path. The
primitive is a pure reader: it allocates nothing, schedules no initializer, mutates no
arena state, and fabricates no value. Generic derivation, genuine initialization and
honest failures are preserved:

- null operand → ordinary guest `NullPointerException` (kind 6), catchable;
- non-enum operand → ordinary guest `ClassCastException` (kind 8), no initializer run;
- enum whose constant table has not genuinely been published (uninitialized or failed
  `<clinit>`) → atomic typed `EnumSetProfileError(2, classIndex)`; nothing is faked and
  no failed state is silently recovered;
- measured path: `StandardLevel.<clinit>` has already published its constants before
  PC187 `EnumSet.allOf(StandardLevel.class)`, and the later `LEVELSET.iterator()` uses
  the accepted bounded HashSet insertion-ordered iterator (built in declaration order).

No Log4j/StandardLevel special case, no host reflection, no fabricated constants, no
cap increase, no fake initialization.

## Files Changed (all under `evidence/java-evm/minecraft-entry/enum-set-preflight/`)

- `bootstrap/java/util/EnumSet.java` + `EnumSet.class.hex` — one genuine append-only
  image (457 B, SHA256 `ab36a2f498e571717f53554bb485b5d84a38616fc376f1af7a0f5a66846ff230`),
  compiled Java8 `-g:none`, extends the accepted bounded `HashSet`, declares the sole
  private static native `universe0(Class)`.
- `engine/MCEntryInterpreter.sol` + `build.js` + built artifacts — append-only engine
  delta (image 83, binding 12, reserved replacement) and the official cap-checked build.
- `coordinator/MCEntryCoordinator.sol` + artifacts — rebased domain and freshly measured
  engine code hash pin.
- `tools/stage_engine.py` — deterministic, uniqueness-asserted delta staging.
- `tools/verify_source.py` — independent reverse verifier (does not run the staging
  script).
- `tools/Go.txt` — driver rebased from the accepted parent driver (domain, engine
  SHA/Keccak/length, coordinator Keccak); pins only, not executed here.
- `pins.json`, `parent-input.json` — basis `1ddd4f59a`, parent `parent-1ddd4f59a`.

## Verification (run here)

- `stage_engine.py` re-run is byte-deterministic; staged source SHA256
  `5f1521448321d999a8d05a2fb97aaca7f14ee5f8b0821a8944a2378d91c5a3df`.
- `verify_source.py` passes: parent input hashes; javac8 recompile of `EnumSet.java`
  equals the committed image; recomputed Keccak equals `pins.json`; independent full
  reconstruction of the delta equals the committed engine; all 82 prior bootstrap
  images byte-identical and in order; binding-12 descriptor/flag validation; branch is
  allocation/initializer-free; coordinator equals parent + domain + fresh engine pin.
- Official engine build (`engine/build.js`, 384 KiB check) exit 0; coordinator build
  (`coordinator/build.js`, 24 KiB check) exit 0.

**Not run here (parent-owned):** generated/retained/original29 gate matrices,
Go driver execution, and any original Minecraft artifact/world access. This candidate
has not been exercised against the measured original29 frontier; that remains the
parent's acceptance gate.

## Remaining Uncertainty

- Runtime headroom is only **189 B**; any later source edit must be re-measured against
  the cap. The build did pass the pinned check in this session.
- An enum that has not yet published its constant table is refused with a typed bounded
  profile error rather than lazily initialized. The measured mid-`<clinit>` path and
  already-initialized paths are supported; this bounded refusal is deliberate (no fake
  initialization, no failed-state recovery) and is the main semantic deviation from
  full Java 8 `EnumSet.allOf`.
- `tools/` gate copies inherited from the previous stage were not re-run or relabelled;
  their profile labels are historical and the parent should treat them as scaffolding.
