# MC-AS0 immutable artifact-store controller

This directory is the production runtime-worker delivery for the frozen
`JAVA_EVM_MC_AS0_PLAN.md`. It is an implementation candidate pending parent
integration and acceptance. It does not change the accepted VFS0a/JVM profiles,
EVM behavior, gas accounting, or consensus code.

`AS0ArtifactStore` controls one sequential artifact. Ordinary EVM `CREATE` deploys
the controller, and each successful `append` makes the controller execute `CREATE`
for runtime code `STOP || raw`. No host-installed child code, overwrite, upgrade,
abort, import, callback, fallback, or measurement-only hash/comparator API exists.
The constructor writes nonzero `owner` and `declaredLength` to storage; there are no
Solidity immutables or setters, so deployed controller bytecode is identical across
owners and declared lengths.

The contract implements the frozen ABI, `AS0Error(1..14)`, `PageIssued`, and
`Sealed`. Limits are 8192 bytes/page, 4096 pages, 32 MiB/artifact, and 4096 bytes/read.
Append computes the page/code/ordered commitments in the EVM and intentionally checks
the caller's page assertion after child creation, so a mismatch exercises ordinary
outer-call rollback. An at-full or empty append is rejected before `CREATE`; sealing
also requires exactly `ceil(declaredLength / 8192)` pages. Sealed reads use
`EXTCODEHASH` and `EXTCODECOPY`, skip the leading STOP byte, and can cross a page.

Sealing proves completeness under the specified instance-bound Keccak commitments,
not confidentiality: page code is publicly inspectable before sealing. The content
commitment is not a location-independent file digest, an official whole-JAR SHA-256,
a ZIP/DEFLATE proof, a class catalogue, a `ClassLoader`, JVM mounting, Minecraft
execution, EULA acceptance, listener operation, or a genuine `Done` marker.

## Reproducible artifact

Build/check from this directory:

```sh
npm ci --ignore-scripts --no-audit --no-fund
npm run build
npm run check
go test ./jvmevm/artifactstore/as0/runtime   # from repository root
```

The build requires solc `0.8.30+commit.73712a01.Emscripten.clang`, optimizer 200,
via-IR, Cancun, and disabled metadata (`appendCBOR=false`, `bytecodeHash=none`). It
checks the exact ABI surface and event indexing, absence of immutables/link references,
and the frozen 49,152-byte init / 24,576-byte runtime caps. Generated files are:

- `AS0ArtifactStore.init.hex`: constructor bytecode; 3166 bytes, binary SHA-256
  `b792253995eafb2ecbc6d7c6c6f28fc0fc03ad0d5073a97f4c62b4ea93dd0f88`.
- `AS0ArtifactStore.runtime.hex`: fixed deployed code; 2831 bytes, binary SHA-256
  `e7f8e95b0af80bf15e89a01ceb635d8ae858560c606cc86ac3877d8f0de69b13`,
  Keccak-256 `c8cec283e80fd82b15254bd50a9f2aea3a91305ba71f756f834439280600f896`.
- `AS0ArtifactStore.abi.json`: pinned ABI.
- `artifacts/AS0ArtifactStore.json`: combined ABI, constructor/deployed bytecode,
  compiler settings, source hash, code hashes, empty immutable references, and
  storage layout. Go callers receive an independent embedded copy through
  `runtimeassets.Artifact()`; there is no source-tree fallback.

Solidity source: 7012 bytes, SHA-256
`2483cd1fadd424773beb4ba1698b79ce36e4aebe26454e2b50c80e50a8a55be1`.

## Actual unmodified-EVM replay

An ignored runtime-worker control built the final combined artifact and used
`core/vm/runtime.Create`/`Call` with Cancun dev context and zero value. A generated
32 MiB input (4096 ordinary append calls) reproduced the preflight commitments:

- controller `CREATE`: 611,673 gas;
- append calls: min 1,765,626, max 1,825,326, mean 1,765,691 gas;
- append aggregate across 4096 separate calls: 7,232,273,796 gas;
- seal: 31,394 gas;
- final-boundary cross-page 4096-byte read: 24,835 gas;
- chain: `4b50e19eba3a5a2c8d7ebe0c67a93ef44cd82b006479cab9399970b60bacd5f4`;
- content: `006e3ee443de0bf7f1f9afe36ad821d847cb28a81e17e555a8ed62b26b295801`.

Thus 7.232B is aggregate data/code-deposit gas over 4096 calls, not one-call gas or
that many computational instructions. Every operation remained below the unchanged
100M ordinary-call limit; 1B/120s remains an explicit boundary-only limit, with the
20min/4GiB full-gate watchdog unchanged.

Final-artifact controls also passed constructor/owner/cursor/length/seal/read/page
errors, fixed runtime identity across different owner/length deployments, exact
`STOP || raw` page code, post-`CREATE` wrong-commitment rollback and same-child retry,
end-offset empty reads, and the corrected full-before-seal empty append rejection
without nonce/page/state/log changes. The full replay took 0.656s; its auxiliary
prototype committed trie state every 256 pages and reopened in a new process, so it
is **not** evidence of production per-call durable publication. The disjoint Go
transport must publish every successful append/seal and pass its disk-failure and
new-process gates before parent acceptance.
