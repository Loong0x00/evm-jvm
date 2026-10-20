# P25 raw73 / 516040 LOCAL envelope candidate

This isolated stage changes only the accepted P25 raw-resource envelope. Its Solidity
baseline is the exact accepted `../parent-raw72-q65536/artifacts/engine` and
`.../coordinator` source. P25 labels and domain are retained. The parent historical
stage and accepted profile are unchanged.

## Scope and retained limits

- Engine raw-class count/aggregate bytes: **72 / 513,384 -> 73 / 516,040**; only the
  two engine constants and their two `_configRoot` leaves change.
- Coordinator arrays/count guard and raw byte guards admit 73 / 516,040. Its engine
  runtime-codehash pin is updated to the compiled candidate.
- Observer normal raw bound and MR01 class diagnostic bound change **72 -> 73** and
  **169 -> 170**. Separate raw74 probes verify driver/coordinator/engine refusals.
- All **97 bootstrap leaves and images** are unchanged. Computed P25 root remains
  `60d5d3b5d4ecaf68427aa6bba3dcb3084e04b64f09b5d155d2f651746aeb875e`.
- JVM slice max remains 65,536; internal/transfer max 4,096; per-class max 262,144;
  arrays/objects 4,096; handles 8,449; checkpoint 1 MiB; commit reserve 25,000,000;
  owned-call watchdog 30 s. Engine runtime is 392,091 bytes (cap 393,216).
- This is a generated-only **LOCAL Execute/Call candidate**, not standard deployment or
  full Session acceptance. The parent separately handles the untouched original73
  binding and fresh max-gas q65536 replay. No original JAR/classes/resources,
  checkpoint, world, EULA, or Minecraft `Done` claim is included here.

`tools/build.py` performs exact source normalization against the accepted P25 Solidity
and generated-only observer, compiles with the provisioned offline solc 0.8.30 and
checks the actual ordered 97-leaf root, ABI/storage layout, codehash pins, and runtime
cap. It does not globally replace `72` or modify bootstrap slot 72. The fixture tool
uses generated Java 8 class sources only and never runs guest classes on the host.

## Generated-only gate result

The final archived run is `results/generated-gate-p25-raw73-v3/` (check its
`SHA256SUMS` and `source-manifest.json`; earlier v1/v2 archives are retained unchanged). The
ordinary 1,000,000,000-gas gate completed in 46.252 s and independently reverified all
12 public coordinator receipts. Raw71/raw72 controls and raw73 positives completed and
reopened at q1/q7/q4096. Direct raw73 engine execution completed. Exact 516,040-byte
raw73 inputs succeeded in direct-engine and coordinator paths; 516,041 was refused
atomically. Raw74 was refused at driver, coordinator, and engine layers. Invalid JVM
and internal budget controls remained typed/atomic. The q4096 and q65536 loop paths
have equal terminal MR01 payload, roots, results, and counters; q65536 commits 4,101
JVM instructions in one watchdog-bounded slice.

These generated fixtures validate only the envelope and retained controls; they do not
prove the measured original `ey.class` binding or Minecraft startup.

## Reproduction (from repository root)

Choose fresh, append-only output names under `build/`:

```sh
python3 evidence/java-evm/minecraft-entry/raw73-byte516040/tools/build.py \
  build/java-diff-mc-raw73-byte516040-build-repro
python3 evidence/java-evm/minecraft-entry/raw73-byte516040/tools/generate_fixtures.py \
  build/java-diff-mc-raw73-byte516040-fixtures-repro
python3 evidence/java-evm/minecraft-entry/raw73-byte516040/tools/gate.py \
  build/java-diff-mc-raw73-byte516040-build-repro \
  build/java-diff-mc-raw73-byte516040-fixtures-repro \
  build/java-diff-mc-raw73-byte516040-gate-repro
python3 evidence/java-evm/minecraft-entry/raw73-byte516040/tools/archive.py \
  build/java-diff-mc-raw73-byte516040-build-repro \
  build/java-diff-mc-raw73-byte516040-fixtures-repro \
  build/java-diff-mc-raw73-byte516040-gate-repro \
  evidence/java-evm/minecraft-entry/raw73-byte516040/results/generated-gate-repro
```

The build/gate scripts force local `NODE_PATH`, offline npm mode, `GOPROXY=off`, and
`GOSUMDB=off`; no install, network, external geth process, or sibling/original inputs
are used. Build artifacts are generated in this stage and may be removed after replay;
the committed pins and archived receipts retain the reproducibility evidence.
