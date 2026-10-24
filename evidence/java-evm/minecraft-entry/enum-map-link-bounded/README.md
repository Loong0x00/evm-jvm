# P58: EnumMap type-link marker only

This is a disposable, unaccepted candidate based only on the approved P57 source
snapshot at `../enum-map-link-source-base-p57` (all 11 declared hashes verified).
It implements the measured `instanceof java/util/EnumMap` type link. It does **not**
implement EnumMap data, construction, universe, clone, or Map behavior, and no
EnumMap object is created by the generated guest fixture.

## Reproduce

From the repository root, with the local pinned compiler dependencies already
available:

```sh
evidence/java-evm/minecraft-entry/enum-map-link-bounded/build_candidate.sh
```

This compiles the marker and generated fixture with Java 8, rebuilds the pinned
engine/coordinator artifacts, compiles the local Go EVM driver offline, and runs
source/prefix/ABI/receipt checks. The fixture is a generated 150-class ZIP whose
first class performs EnumMap identity, `instanceof`, cast, array covariance/store,
clone and `reflect.Array.newInstance` checks. Java on the host is used only for this
generated-fixture oracle; all reported guest behavior is from EVM execution.

The exact runtime pins, bootstrap-prefix proof, q1/q7 EVM summaries and raw-owner
refusal are in `pins.json` and `execution-report.json`. Failed attempts and scope
corrections are retained in `attempt-history.json` and `logs/`; no failed attempt
was deleted or relabeled as a pass. Local ignored `world-*` directories retain the
full generated EVM process state and reports for parent replay.

## Layout and scope

- `engine/`, `coordinator/`: only candidate Solidity sources and generated JSON
  artifacts. ABI remains byte-for-byte equal to P57; all nine engine and four
  coordinator code domains are fresh.
- `bootstrap/java/util/Map.java` and `AbstractMap.java`: compile context only; their
  accepted bootstrap images are not replaced or embedded from these sources.
- `bootstrap/java/util/EnumMap.java`: raw-superclass, erased marker class with one
  private super-chaining constructor and unbound native erased Map-method guards.
- `canonical-driver.go`: canonical local MR0 driver with this candidate's exact
  engine/coordinator runtime pins and fresh domains.
- `tests-src/`, `build_fixture.sh`: reproducible Java 8 generated test sources.
- `root_helper.py`, `verify_candidate.py`, `write_evidence.py`: ordered-root, source,
  artifact and generated-run checks.

P58 bootstrap index is 123 after the exact 123-image P57 prefix; with 150 raw
classes the EnumMap mirror target is internal class index 273 (274 total). No
accepted quota, checkpoint, config-root ABI, EVM gas rule, coordinator interface,
or stock execution profile is changed. This candidate has not been independently
accepted and is not evidence of original Minecraft execution.
