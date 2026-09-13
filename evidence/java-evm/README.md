# Durable Java-in-EVM evidence

Latest system-ClassLoader parent: `minecraft-entry/parent-bc4aa5f31/`; LOCAL384
after measured320 failure. Original loader array is committed; next exact class is
LinkedHashSet, before any ClassLoader.getResources or fake empty resource result.

Latest defining-loader parent: `minecraft-entry/parent-102911980/`; repaired
pool-hit quota and VM loader override guards. Raw mirrors now commit one nonnull
loader; next exact method is ClassLoader.getSystemClassLoader, not resources yet.

Latest single-Thread parent: `minecraft-entry/parent-cc0c40e71/`; original default
null context path commits and next exact member is Class.getClassLoader. A real
raw-class defining-loader identity is required; null-all empty search is forbidden.

Latest ClassLoader type parent: `minecraft-entry/parent-d19622e52/`; corrected
worker RSS summary and committed original ClassLoader[] path. Next exact member is
Thread.currentThread; no loader/resource behavior has been fabricated.

Latest PrivilegedAction parent: `minecraft-entry/parent-a30955bb0/`; repaired
full domain isolation and committed original LoaderUtil init under q1. Next exact
platform type is ClassLoader at findUrlResources anewarray; no fake empty search.

Latest security-getter parent: `minecraft-entry/parent-2293e298e/`; exact source
build passes and original22 now requires PrivilegedAction. Successful checkpoint
remains before LoaderUtil initializer; no failed-call Java progress is credited.

User-authorized LOCAL1B budget: `minecraft-entry/local-budget-1b/`; unchanged
EVM accounting/runtime, genuine Properties construction now passes, next missing
System.getSecurityManager member. Existing frame cap128, diagnostic16 corrected.

Latest read-only parent cost proof: `minecraft-entry/parent-4d3f37402/`; original
q1 actually hits `_commit` reserve guard, with identical observer ON/OFF results.
No budget or runtime change; LOCAL ceiling can be amended separately.

Latest Properties parent: `minecraft-entry/parent-c24d374bc/`, recovered worker,
Java8 dispatch repair, source-only proof and original minimum-slice gas refusal.
See `JAVA_EVM_MC_PROPERTIES_PARENT_PREFLIGHT.md`; no startup/accepted-cap claim.

Latest class-count parent: `minecraft-entry/parent-6748eb593/`, whole source-only
build, count controls and original20 actual next Properties allocation blocker.
See `JAVA_EVM_MC_CLASSCOUNT_PARENT_PREFLIGHT.md`; accepted baseline unchanged.

Latest parent arraycopy review: `minecraft-entry/parent-f780f1a13/`; source-only
native arity repair, canonical receipts and original16 next missing dependency.
See `JAVA_EVM_MC_ARRAYCOPY_PARENT_PREFLIGHT.md`. Public snapshot was explicitly
pushed to `1e4027b9b`; subsequent work remains local.

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

## CB0 production bridge

Parent accepted fixed class package bridge in JAVA_EVM_MC_CB0_REVIEW.md; evidence
cb0/ retains interrupted candidate provenance, real parent failures and fixes,
explicit nested engine-event amendment, complete549.346s/1202511872B final observer
and54.842s/351748096B test-only audit delta. Eight actual input-to-terminal processes,
exact64KiB package, high32MiB input and durable Java317/299 are generated fixtures,
NOT original Minecraft execution or a general loader. No push follows implicitly.

## Selected-table parent COPY

`selected-table/parent-b55892680/` retains actual worker-order regression, emitted
unused getter allocations, both parent repairs, fresh331.597450s/874287104B gate,
source/debug/driver/fixtures/receipts/opaque checkpoints. Dense ordinary progress
and broad alias/persistence evidence are generated-only, not8/256KiB promotion,
MR0 acceptance or original Minecraft execution. See parent Selected preflight.
