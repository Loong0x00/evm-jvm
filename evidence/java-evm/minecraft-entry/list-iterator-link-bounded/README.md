# P51 parent-corrected ListIterator hierarchy acceptance

The worker candidate below was NOT accepted unchanged. Its increased count left the five historical metadata tail offsets unchanged, overwriting EntrySet110 and shifting old class identities. A real fresh EVM retained Map.entrySet probe refused missing HashMap$EntrySet. Parent preserved it and restored count-10..-6 to actual class slots105..109. The old coordinator still bound P50; parent freshly authenticated the corrected engine, isolated all four coordinator domains and completed the remaining engine domain labels. No existing image byte or execute/native/codec/quota rule changed.

Current engine431159B SHA71488d8912734a80e09a72ac20b560261f80427ea8df37f90d58dee4b23a3ee7; coordinator5411B SHA937fb710a0125c7bda519be0dbcf11ed7c0f360e1f1eac4cf6acf8c17ddbcbce. All114 prior image bytes/order remain exact, new marker188B leaf114,115-image root5e0f1d1ee28e2835cea4a4c583a56e142e59da88ef49e37b0f4451c1e44b74aa. Historical worker gate receipts concern the old assembly, NOT these current artifacts.

Parent source/build/private-tail/array/gates/refusals/separate-process reopen and fresh original130 coordinator proof: `../parent-list-iterator-link/`; root doc `JAVA_EVM_MC_LIST_ITERATOR_PARENT_PREFLIGHT.md`.

---

## Historical unaccepted worker report

# MC ListIterator bounded link marker

Scoped candidate for the measured Java 8 `java/util/ListIterator` interface edge only.
This is a minimal public abstract marker interface extending the pinned guest
`Iterator<E>`; it declares no methods. The implementation does not claim any
ListIterator mutation/traversal API beyond inherited Iterator dispatch.

## Reproduction

From `/home/user/evm-jvm/list-iterator-link`:

```sh
./evidence/java-evm/minecraft-entry/list-iterator-link-bounded/build-bootstrap.sh
./evidence/java-evm/minecraft-entry/list-iterator-link-bounded/build-java-fixtures.sh
NODE_PATH=/home/user/evm-jvm/list-iterator-link/jvmevm/runtime/node_modules \
  node evidence/java-evm/minecraft-entry/list-iterator-link-bounded/engine/build.js
NODE_PATH=/home/user/evm-jvm/list-iterator-link/jvmevm/runtime/node_modules \
  node evidence/java-evm/minecraft-entry/list-iterator-link-bounded/coordinator/build.js
 go test ./evidence/java-evm/minecraft-entry/list-iterator-link-bounded/tests
 go run ./evidence/java-evm/minecraft-entry/list-iterator-link-bounded/tests/gate.go
```

The Java fixture compiler is `/usr/lib/jvm/java-8-openjdk/bin/javac`, `-g:none`,
Java 8 classfile target. `LinkCheck.java` compiles against the stock Java 8 API as
test-only fixture code; those fixtures are executed only by the fresh geth EVM
harness, never by the host JVM. `ListIterator.class` itself is generated against
minimal compiler-only `Object`, `Throwable`, and the existing-shape Iterator stub.

The EVM runner uses only public geth EVM APIs, the candidate's locally preinstalled
interpreter runtime, fresh StateDBs, normal ABI calls, and a finite 1,000,000,000
per-call gas ceiling with a 30-second call watchdog. It does not use a coordinator
session/persistent store; durable process-reopen coverage is therefore not claimed.

See `pins.json`, `source-manifest.json`, `runs/bootstrap-root.json`, the full
leaf/source diff, and `runs/gates-004/full-suite.json`. Failed setup/build attempts
and their disposition are recorded in `runs/attempts.md`. This is an unaccepted
candidate awaiting parent independent review; it is not original Minecraft
execution or a profile acceptance claim.
