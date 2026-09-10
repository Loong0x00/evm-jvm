# ZI0 persistent-parent probes

Measurement only: **not frozen, accepted, or Minecraft readiness evidence**. This
worker copied the committed `2bb841b0c` Go driver and changed only its workspace
to `build/java-diff-mc-zi0-parent-probes`; the Solidity and artifact are untouched.
No official JAR, host index/extraction, class loading, MC execution, EULA, listener,
or production installer was used.

## Reproduction and pins

```sh
cp evidence/java-evm/zi0/persistence-parent-probes/main.go.txt \
  build/java-diff-mc-zi0-parent-probes/main.go
gofmt -w build/java-diff-mc-zi0-parent-probes/main.go
go build -o build/java-diff-mc-zi0-parent-probes/probe \
  build/java-diff-mc-zi0-parent-probes/main.go
python3 evidence/java-evm/watchdog.py \
  evidence/java-evm/zi0/persistence-parent-probes/replay-final-2.log \
  evidence/java-evm/zi0/persistence-parent-probes/watchdog-final-2.json \
  build/java-diff-mc-zi0-parent-probes/probe
```

The run exited 0 in 18.506 s under the unchanged 20-minute/4 GiB watchdog;
peak process-group RSS was 292,483,072 bytes. It retained the copied 54-control
suite and added seven ordinary runs plus 12 independent probes. Durable hashes:

| item | SHA-256 |
|---|---|
| Solidity source | `ab85fdb4f8710c4d58c639de191c62873ee26f29fc87b92223f0e476700f8b85` |
| prototype artifact | `6885dd02ecb833360dc111cb8c6d9da2dc44d963bcfcd49541c456b798510894` |
| runtime | `808ef488ad768c3a5082db37bf6ec4735f4d2c2d2f74b43887a09069896ef974` |
| Go driver source | `ad59ba94242310f210f1a0c94897799cc1c7be70b6acccbbc0d331662ca97c4b` |
| report | `61f7b6db63191775276290792908961e1616740641c49370411790b8570d2cb7` |
| final replay log | `61f7b6db63191775276290792908961e1616740641c49370411790b8570d2cb7` |
| final watchdog | `f2029b84cb8c63ae84cd59574057bd32c077dfa1dc3f3ce65e1fac68a0adbb17` |

Compiler storage-layout evidence is `storage-layout.json` (SHA-256
`b5a0fa0fc6cd9643ea724c85c56395e48eaeac5f210b0f689fb6fd51a284b4ed`). The
pinned slots are owner 0, store 1, content 2; packed header slot 3
(length offset 0, phase 4, EOCD 5, CD offset 9, CD size 13, count 17,
next-entry 21, cursor 25); previous-local/end packed in slot 4; rolling 5;
final root 6; `records` mapping slot 7; `nameIndex` mapping slot 8.

## Probe outcomes

- Zero-owner constructor was **observed accepted**, explicitly recorded as
  `observed-accepted-not-pass` (no policy pass is claimed).
- Empty-before-finish and at-EOF scans succeeded as unchanged-state no-ops,
  recorded as observations.
- Geometry-specific fixtures reached ZI0Error 27 (local overlap/order) and
  23 (data range), after changing both LOC and CEN stored compressed/plain sizes.
- Direct 100,000-gas scan returned OOG after reaching one SSTORE. Before host
  reload, committed root, storage root, mapping entries, record slot, nonces, and
  logs were equal; an immediate valid retry matched a fresh binding/state.
- TEST-only committed `nameIndex` redirect to another existing record returned
  exact ZI0Error 19; restoring the slot preserved the original valid lookup.
- Sixty-four records with 256-byte names, 1024-byte comments, and **256
  zero-length TLVs** (not one aggregate TLV) used 47,225,700 gas for the scan.
- Dense valid-ending EOCD candidates across the maximum tail window returned
  exact ambiguity ZI0Error 6 at 69,172,720 gas.
- Binary/NUL/non-ASCII/dot/slash names had exact byte hits and distinct absent
  normalization-looking controls; no VFS normalization was applied.
- Final entry/index and lookup length bounds returned exact codes 31 and 32;
  copied CAS/unit controls retained exact codes 10 and 11.

All results are disposable-probe observations for parent replay. A cap failure,
new semantic failure, or unresolved publication/error policy remains a blocker;
no cap increase or ZI0 acceptance follows from this run.
