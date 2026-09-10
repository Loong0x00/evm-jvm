# Durable Java-in-EVM evidence

User instruction: important plans, constraints, acceptance results and failure
reproducers must NOT live only in `/tmp`. This directory is the Git-tracked home
for the recent parent evidence. Canonical plans/reviews remain repository-root
`JAVA_EVM_*.md`; accepted code/tests/artifacts remain under `jvmevm/`.

## Scope

- `as0/`: accepted AS0 final package/repro, parent validation failures and corrected
  probes, relocated executable/new-process control, accepted VFS regression.
- `vfs0a/`: accepted final VFS suite and reproducibility run.
- `zi0/`: UNACCEPTED ZIP-index preflight original and corrected parent replays,
  failures and static inventory. This is NOT DEFLATE/ClassLoader/Minecraft success.
- `zi0/prototype/`: disposable original/corrected sources, emitted artifacts and
  synthetic drivers needed to reproduce the parent findings. Go drivers use `.go.txt`
  to avoid making an evidence directory part of normal package discovery.
- `manifest.json`: original path, byte length and SHA256 for every archived capture.
  Original `/tmp` paths are provenance only; original captured bytes are unchanged.
- `watchdog.py`: captured process-group20min/4GiB enforcement helper. Its sampled
  RSS is observed peak, not an assertion about unobserved between-sample peaks.

No credentials, official server JAR/class payloads, extracted world files or
machine-generated success substitutes belong here. ZIP inventory consists of STATIC
facts and transport hashes only; it is not supplied as execution lookup authority.
The ZIP fixtures are generated synthetic bytes. No server was executed.

The accepted AS0 suite is4.096s (external4.358s); original ZI0 replays have13 parent
proposed-refusal counterexamples. Corrected ZI0 observations fix12 definite flag/
descriptor cases; the remaining ZIP64-prelude case is deliberately still an accepted
observation pending profile policy. Do not count its changed expectation as a fix.
See the stage reviews for the precise claims and different gas contexts.

## Verify the archived bytes

From repository root:

```sh
python3 evidence/java-evm/verify.py
```

To reconstruct the small ZI0 parent measurement workspaces (not production), from
repository root with the already pinned solc installation:

```sh
for variant in original corrected adversarial corrected-gaps; do
  dst=build/java-diff-mc-zi0-parent/$variant
  mkdir -p "$dst"
  cp evidence/java-evm/zi0/prototype/$variant/main.go.txt "$dst/main.go"
done
for variant in original corrected; do
  dst=build/java-diff-mc-zi0-parent/$variant
  cp evidence/java-evm/zi0/prototype/$variant/{ZI0Prototype.sol,build.js,prototype.json} "$dst/"
  node "$dst/build.js"
  cmp "$dst/prototype.json" evidence/java-evm/zi0/prototype/$variant/prototype.json
done
for variant in original corrected adversarial corrected-gaps; do
  go build -o build/java-diff-mc-zi0-parent/$variant/probe ./build/java-diff-mc-zi0-parent/$variant
done
```

The `adversarial` original probe intentionally exits1 and records its counterexamples;
that is expected reproduction, NOT a successful production gate. The other three
probe variants exit0 on the recorded outcomes. Archive future logs into a new named
run directory here, e.g. `zi0/runs/<revision>-<purpose>/`, with the command, exit status,
limits, elapsed/RSS and relevant artifact hashes. Do not overwrite these historical
captures or depend on old temporary directories. A replay still requires the pinned
geth checkout and compiler; embedding these measurement sources is not a standalone
production deployment claim.

Transient database directories, binaries and caches may use `build/` or test temp
directories only if reconstructible. If a failure depends on irreplaceable state,
preserve that state or a sufficient reproducible fixture before cleanup. No blanket
migration/cleanup of all historical temporary data has been performed or claimed.
