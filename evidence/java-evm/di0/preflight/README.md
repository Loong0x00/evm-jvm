# MC-DI0 bounded inflation preflight evidence

Status: disposable generated-fixture preflight at `cfa093d94`; **not DI0 frozen or
accepted**. No official JAR bytes, extracted classes, Java execution, Minecraft,
EULA, listener, or Done marker are present. `DI0Inflate.sol` is measurement code,
not production code.

The Go driver creates a synthetic ZIP, uploads it through ordinary accepted AS0
CREATE/pages, builds the accepted ZI0 index, and creates/calls the prototype in the
same unmodified EVM state. The prototype is given only a ZI0 address, asserted FINAL
root, and raw-name query. It checks accepted code pins and derives packed metadata,
compressed range, bit/Huffman/LZ77 decisions, output, length, and CRC in EVM. Go's
`compress/flate` and `hash/crc32` are trusted generated-fixture oracles only.

Durable files:

- `DI0Inflate.sol`: 9,699-byte-runtime prototype source.
- `replay.go.txt`: generated ZIP/oracle/EVM driver; no host decode authority.
- `compile.js.txt`: pinned compiler invocation.
- `execution-report.json`: all EVM roots, bindings, gas, state, outcomes, q1/q128,
  rollback and hashes.
- `artifact-summary.json`: artifact/code hashes and ABI summary (bytecode remains
  reproducible in ignored build output).
- `authoritative-sources.txt`: RFC1951/PKWARE references and downloaded hashes.
- `compile.log`, `execution.log`, `watchdog.txt`, `SHA256SUMS`: run evidence.

Reproduce from repository root into a fresh disposable directory (do not overwrite
this historical report):

```sh
work=build/java-diff-mc-di0-preflight-replay-$(date +%s)
mkdir -p "$work"
cp jvmevm/artifactstore/zi0/runtime/package{,-lock}.json "$work"/
cp evidence/java-evm/di0/preflight/{DI0Inflate.sol,compile.js.txt,replay.go.txt} "$work"/
(cd "$work" && npm ci --ignore-scripts --no-audit --no-fund && \
  cp compile.js.txt compile.js && node compile.js && \
  cp replay.go.txt replay.go && \
  timeout 1200s go run replay.go DI0Inflate.json > execution-report.json)
```

The report is expected to vary in elapsed/RSS values; artifact hashes, fixture ZIP
hash, outcomes, work counts, EVM output hashes, and each paired q1/q128 final/state
root are deterministic at the pinned revision/toolchain.
