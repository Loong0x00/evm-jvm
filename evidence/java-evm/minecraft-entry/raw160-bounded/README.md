# MC-RAW160-BOUNDED-1 (LOCAL candidate; unaccepted)

This directory contains only the isolated raw-class-count profile candidate and
its generated Java8 fixtures. It is based on `89883b2dc6d47beee80de2c430e3e634f41cf3a4`
with accepted guest commit `0832116b3649833e8930ca4a4eb9ddd9bb6b769e`. The approved
source-only P61 snapshot is preserved separately at
`../raw160-source-base-p61/`; `verify_raw160_source.py` checks its nine-file source
snapshot hashes before checking the candidate delta.

## Scope and exact boundaries

- Raw class admission is 150 → 160; raw byte total remains exactly 1,063,930.
- The guest engine's 9 domain strings and coordinator's 4 domains are fresh
  `MC-RAW160-BOUNDED-1` domains. Config-root schema/order/encoding stays schema 1;
  only the first limits-vector value changes to 160. Other 10 values are preserved.
- Coordinator constructor arrays and count guard are expanded to 160; global
  binding ABI remains uint8. The diagnostic internal count is 288 (160 + 128),
  with maximum internal class index 287. No additional constant-pool class pool
  is implied.
- All 128 bootstrap images and ordered leaves are exact P61 copies; engine global
  native count 22, String-local count 12, engine ABI and engine storage layout are
  unchanged. Bytecode, opcode/gas accounting, checkpoint encoding, entrypoints,
  owner/authentication and geth rules are unchanged. Coordinator private storage
  slots after its four fixed arrays necessarily move with the new array extents;
  this is a newly deployed LOCAL profile, with no cross-profile state migration.
- No original Minecraft input was opened or executed. Generated fixture classes
  are test-only, Java8 classfiles produced by `javac -g:none`.

## Build and source checks

Pinned local solc: `0.8.30+commit.73712a01.Emscripten.clang`, optimizer 200,
viaIR, Cancun, metadata disabled. Rebuild commands:

```sh
NODE_PATH="$PWD/jvmevm/runtime/node_modules" node evidence/java-evm/minecraft-entry/raw160-bounded/engine/build.js
NODE_PATH="$PWD/jvmevm/runtime/node_modules" node evidence/java-evm/minecraft-entry/raw160-bounded/coordinator/build.js
python3 evidence/java-evm/minecraft-entry/raw160-bounded/verify_raw160_source.py
go build -o build/bin/mc-raw160-driver evidence/java-evm/minecraft-entry/raw160-bounded/canonical-driver.go
```

Runtime pins (deployed runtime length, not initcode): engine 455,565 bytes,
SHA256 `b385d221ca1f44fd476e23846aad83d0b3fa1de5d2d19fc62353259501e6f545`, Keccak
`02593391ee49cf1b8b9e67f2f45563cd498b30a93ded342b522300566a3bab33`; coordinator
5,411 bytes, SHA256 `d43bb4a7439494bc8e31e202fbfbe1ab90ba3189936ff81431a0b30ffcd4ff13`,
Keccak `75b40eebc76278e48069620e7e3c56bed92c2e75f13489aee59a626f1d4bce34`.
These remain oversized for ordinary EIP-170/EIP-3860 deployment; this is a LOCAL
preinstalled-code candidate, not a standard CREATE compatibility claim.

## Generated EVM evidence

`fixtures/raw160-empty-main/generate_fixture.py` reproducibly creates a trusted
160-class Java8 package and a one-class quantum-control fixture. Each run uses a
unique persistent directory under `fixtures/raw160-empty-main/runs/`; observer
logs live in sibling `runs/logs/`, never inside the strict world root. Reopen
reports are under sibling `runs/reports/`.

- Genuine generated EVM starts and fresh-process reopens for 150, 151, and 160
  bindings: `raw160-positive-150-q65536-001`, `raw160-positive-151-q65536-001`,
  and `raw160-positive-160-q65536-005`. Each reaches generated empty-main lifecycle
  2 with 150/151/160 authenticated bindings. The 160 root is
  `0xb805c6b9c7fd0e350d58fd67d2251a021c7a5c1523079c78d9b71b778c8f2c1b`.
- Compact one-class q1/q7/coarse runs (`raw160-positive-001-q{1,7,65536}-002`)
  complete in fresh processes and have identical EVM trie, package, config,
  machine and VFS roots: `0xe9fb51cd48037642bf608563f956017bbb90e1ea27feb96f4269c8939a2deae5`.
- Earlier failed attempts are retained, not counted: 001 omitted the `.class` ZIP
  entry suffix; 002 preceded the coordinator's updated engine-codehash pin; 003
  selected an auxiliary class as entry; 004 put observer logs in the strict world
  root and therefore failed fresh reopen. See each attempt's README/log/receipt.

## Remaining gates / handoff

Not run and not accepted here: 161-class typed atomic `LinkError`, 160/161
coordinator constructor boundary, exact-byte-cap/+1 EVM tests, raw160 index-287 /
Supplier and class-mirror/interface-array checks, retained P61 SAM/null/throw/cold
String[] plus P60/P59 tail controls, and parent independent build/replay. A fresh
original 151-resource replay is specifically parent-owned and was not performed.
No profile/world/EULA/Minecraft readiness acceptance is claimed.
