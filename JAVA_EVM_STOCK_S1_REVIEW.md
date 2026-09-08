# Stock S1 independent correctness review

Review target: integrated commit `b01b9e6626e1372b9a19c4dd6960863c09e5f100` and the frozen `JAVA_EVM_STOCK_S1_PLAN.md` (SHA-256 `a387ca41d53239d65a27a396bc57bdfb90626b44fec7c5158a9cf2b3ac4762c2`). This review changed no production Solidity, harness, verifier, S0, monolith, or legacy fixture file.

## Result

**Stock S1 is not acceptable against the frozen registration budget.** I reproduced the known 8M aggregate failure with a corrected boundary class in which all 31 test methods (32 declared methods including the constructor) are individually eligible. This removes the integrated verifier's uninitialized-local confounder and measures an even higher valid-boundary cost.

I found no additional reproducible production semantic defect in the reviewed parser/selection, branch dataflow, metadata provenance/root/literal cache, argument initialization, loop progress/lifecycle/cap, reserve/atomicity, resume, or signed-replay paths. That statement is limited to the frozen S1 integer profile and the checked artifacts; it is not S1 acceptance or a general JVM claim.

## Blocking finding: a valid maximum cannot register within 8M

`TestStockS1ReviewDiagnosticAggregate` constructs a 1,959-byte Java 52 class with:

- exactly 32 declared methods (constructor plus 31 public static `()I` methods);
- exactly 256 valid cached `ldc` integer records;
- Code lengths at most 254, stack/locals within 1, and no handlers;
- zero-literal methods implemented as `iconst_0; ireturn`, so every selected test method is flow-valid.

The unchanged class bytes are deployed through the accepted ordinary `ArtifactPage` CREATE and registered through the checked `S1ClassParser` artifact.

At the frozen 8,000,000 transaction gas limit, registration fails with exact revert:

```text
S1ClassError(6,0)
return data:
429f0aa9
0000000000000000000000000000000000000000000000000000000000000006
0000000000000000000000000000000000000000000000000000000000000000
```

The failed signed transaction used 7,962,585 gas. It left the parser nonce unchanged, no internal metadata-page code, no registry record, and no event, confirming rollback/atomicity rather than semantic success.

A diagnostic-only 12M transaction succeeds and produces canonical 6,337-byte `STOP || metadata`:

```text
signed gas used:     8,469,676
intrinsic gas:          22,456
execution gas used:  8,447,220
metadata code hash:  0x87a5a64d2930ac494f01e5e3bf8606e5b7f6515b73728b7b14228052f8d102fb
```

The on-chain metadata exactly matches the test-side schema-2 assembly from the raw trusted bytes, and an independent M2-word decode confirms domain 0 for every one of the 31 test methods. The 12M run is diagnostic evidence only and does not relax or satisfy the frozen 8M requirement.

## Integrated verifier fixture defect

The aggregate fixture at `validation_test.go:1192-1224` does not actually make all of its declared test methods valid. For methods `m04` through `m30`, it emits `iload_0; ireturn` with descriptor `()I`, `maxLocals=1`, and no instruction that initializes local 0. The production parser correctly records the first such method (declared index 5) as:

```text
errorDomain=2, errorCode=11, errorLocation=0
S1BytecodeError(uninitialized, pc=0)
```

The verifier's `stockS1VerifyMetadataExpected` helper performs width/literal decoding but no branch/dataflow validation, so it incorrectly emits domain 0 for that method. A 12M diagnostic registration of the original fixture gives:

```text
signed gas used:     8,370,667
intrinsic gas:          22,456
execution gas used:  8,348,211
actual metadata hash: 0x3a097d77209d6a9447256aecf6e2f06948fdc71c6213b915b70e4253bed5e131
oracle metadata hash: 0x9f26600d62e6aa457b3a601d116aef1587c7b35ffc790a72130518ae88bd8381
```

Thus the post-gas-gate metadata mismatch is a verifier-oracle defect, not evidence that the parser mishandles this uninitialized-local case. More importantly, that invalid fixture understates the true all-eligible boundary: the corrected valid fixture costs 99,009 more signed gas (99,009 more execution gas) and still exceeds 8M.

## Other reviewed properties

Source review and retained actual-EVM probes found the following behavior consistent with the frozen plan:

- selection is by one unambiguous declared name, with recorded access/descriptor/Code/bytecode errors before argument mismatch;
- branch offsets are signed relative to the branch opcode, all targets are checked against instruction starts, and zero-offset `goto` is valid;
- the flow worklist enforces equal stack heights and definite-local initialization at joins and backward edges;
- literals are retained only for valid methods, ordered by method/PC, and selected literals are checked against the immutable issued metadata page;
- class/program/input roots and `int32[]` argument hashing are ABI-encoded and the coordinator initializes exact tagged locals;
- parser registry issuance, raw/metadata/component code hashes, and selected program provenance are rechecked by the step module/coordinator;
- equal-PC loops advance by positive executed counts; exact-cap return wins, otherwise `STEP_LIMIT` preserves machine state and terminal resume rejects;
- dirty-word validation occurs before committed writes, reserve checks bracket ABI preparation/staticcall, and failed calls retain the previous checkpoint;
- signed all-82 execution, small-budget/prefix runs, and deterministic direct replay pass with checked artifacts.

## Artifact and build evidence

Pinned artifact bytes were read directly and their source-hash maps were compared with the six local Solidity sources; all entries match. Checked runtime SHA-256 values are:

- `S1MetadataPage`: `0668b20e4ee135e7cac4091998933a5123658a8e777994fdb4b4ee2d553e6438` (3 bytes template runtime)
- `S1ClassParser`: `395432e7fac77737298c50ee6c6ec51ac8136458a19ce97af991b69ad0fb5ef8` (15,393 bytes)
- `S1StepModule`: `9c70f525c57139efdae676555ada7fc28dfc307be1694376f7e525a675dcee35` (8,408 bytes)
- `S1Coordinator`: `957472808404f19124cb5b5f8440e5186d8d3f7eec60da9451fb150a2a37e9f8` (6,328-byte template)

I did not rebuild Solidity. `npm run check` could not load local module `solc`; no dependency was downloaded or installed. Consequently this review establishes checked-artifact/source-hash evidence, not an independent compiler reproduction.

The retained broad test command compiles the five trusted Java sources with the existing harness command (`javac --release 8`, default debug attributes), checks their pinned identities, runs JVM 8/JVM 21/monolith assertions, and executes the signed stock paths. No host-derived metadata or result entered a production call.

## Reproduction

```sh
go test ./jvmevm/stock/s1 -run 'TestStockS1Review' -v -count=1 -timeout=10m

go test ./jvmevm/stock/s1 -run 'TestStockS1(Review|Harness|VerifyFrozen|VerifyNegative|VerifySigned|VerifyDeterministic|VerifyMalformed|VerifyStock)' -count=1 -timeout=20m

go test ./jvmevm/stock/s1 -count=1 -timeout=20m
```

The first two commands pass. The full package remains red at `TestStockS1VerifyParserCapsMetadataCanonicalityAndSelection/declared32-literals256-metadata6336`, with exact `S1ClassError(6,0)` under 8M. Ignored logs are under `build/java-diff-stock-s1-review/`.
