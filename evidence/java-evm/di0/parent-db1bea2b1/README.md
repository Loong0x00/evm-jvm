# DI0 parent preflight evidence (unaccepted)

See JAVA_EVM_MC_DI0_PARENT_PREFLIGHT.md for decisions and proof boundaries.
The original worker source/artifact was independently rebuilt and its deterministic
EVM report compared (time/RSS deliberately excluded). replay.json/watchdog.json
record the original replay; preflight/artifact-summary.json pins the original code.

compat-replay.go.txt / compat-probes.go.txt are parent generated-fixture Go probes
using the original EVM artifact. generated/ contains ONLY these small handcrafted
raw streams and ZIP wrappers, not server bytes. InflateOracle.java is a HOST-TEST
Java8 oracle, never production decoder authority. java8-oracle.json distinguishes
raw Inflater, ZipFile and ZipInputStream (they differ on trailing compressed bytes).
compat-final-evm.json retains original prototype disagreements with that oracle.

corrected/ contains a disposable source/artifact/compiler and replay with explicit
HLIT<=286/HDIST<=30 policy and ignored final unused bits. Complete indexed whole-byte
consumption remains required. Its21-case replay and10 compatibility probes pass;
this is NOT DI0 acceptance or a production output/Java heap limit. The old64KiB
prototype cap remains in that artifact, even though size inventory motivates a
DI0-only256KiB followup proposal. Original reports are preserved, not overwritten.

inventory-sizes.py is STATIC header/size analysis of the pinned official JAR. It
never inflates/extracts any server bytes and its output is not an execution catalogue.
Reproduction from repository root:

```sh
python3 evidence/java-evm/di0/parent-db1bea2b1/inventory-sizes.py \
  /home/user/evm-jvm/mc-startup-inventory/build/java-diff-mc-startup-preflight/artifacts/minecraft_server.1.12.2.jar
/usr/lib/jvm/java-8-openjdk/bin/javac -d build/java-diff-mc-di0-parent-compat \
  evidence/java-evm/di0/parent-db1bea2b1/InflateOracle.java
/usr/lib/jvm/java-8-openjdk/bin/java -cp build/java-diff-mc-di0-parent-compat \
  InflateOracle evidence/java-evm/di0/parent-db1bea2b1/generated
```

For EVM replay, reconstruct a FRESH ignored workspace with corrected/DI0Inflate.sol,
compile.js and replay.go.txt renamed replay.go. Run pinned solc via compile.js and
compare its DI0Inflate.json with the committed corrected artifact, then build/run
`go run replay.go DI0Inflate.json` from that workspace. Capture new output under a
NEW evidence run directory with evidence/java-evm/watchdog.py; do not overwrite the
historical files. The compatibility Go probes use repository-relative paths shown
in their source. Corrected compatibility checks read/compare generated fixtures;
they do not overwrite them. No temporary directory is sole evidence authority.
