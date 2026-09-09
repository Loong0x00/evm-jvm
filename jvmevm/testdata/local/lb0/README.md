# MC-LB0 trusted local catalogue

This directory is the frozen **64-row positive** MC-LB0 harness catalogue. It is
test-only: host JVMs execute only their normal Java libraries, while EVM calls
receive the exact checked-in opaque class bytes. The minimal EVM bootstrap
replacements are not put on either host JVM class path.

`catalogue.json` pins every invocation and Java result. It has 62 ordinary rows
(`100,000,000` gas, 30-second EVM watchdog) and two explicitly labelled boundary
rows (`1,000,000,000` gas, 120-second EVM watchdog). `reset-between-run` is invoked
twice as two independent EVM calls. Historical gas limits are not changed.

The sources intentionally contain no `new String`, guest `main`, `Class`/
`getClass`, formatting or printing path. `MCLB0RawStatic` and
`MCLB0RawInstance` are the only raw profiles: the rebuild script changes only the
single field's access flags after javac emits a String `ConstantValue`. This gives
a non-final static field that must prepare its constant and an instance field
whose attribute must be ignored. Each raw owner and its independently compiled
consumer are passed unchanged to both JVMs and EVM.

## Rebuild and inspection

The recorded fixture compiler is `javac 21.0.9`; rebuilding with another version
is rejected.

```sh
python3 jvmevm/testdata/local/lb0/build_fixtures.py
javap -classpath /tmp/mclb0-oracle -c -p MCLB0Root
```

The checked inspection showed retained `ldc` + `invokevirtual` for String calls,
`getstatic` for non-final String fields, `invokeinterface` for CharSequence and
Comparable, and real `new`, `newarray`, and implicit-fault handlers in mixed
cases. `TestMCLB0HarnessPinnedCatalogueFixturesAndBytecode` enforces those facts,
the raw field flags/attributes, MUTF-8 NUL/surrogate payloads, exact
`public static root(I...)I` descriptors, and all hashes. `manifest.json` pins nine
raw class images, eleven reviewed source inputs, and catalogue SHA-256
`55b1634732096151efb5a1c4df33ac37b7f4eee3a6075b5220d0b8a51e2a63e9`.

## Recorded commands and results at the harness base

```sh
go test ./jvmevm -run '^TestMCLB0HarnessPinnedCatalogueFixturesAndBytecode$' -count=1
# ok github.com/ethereum/go-ethereum/jvmevm

JAVA_EVM_JAVA8=/usr/lib/jvm/java-8-openjdk/bin/java \
JAVA_EVM_JAVA21=/usr/lib/jvm/jdk-21.0.9/bin/java \
JAVA_EVM_JAVAC21=/usr/lib/jvm/jdk-21.0.9/bin/javac \
go test ./jvmevm -run '^TestMCLB0HarnessJava8And21Catalogue$' -count=1
# ok github.com/ethereum/go-ethereum/jvmevm
```

Both host VMs independently returned every integer pinned in `catalogue.json`.
The pre-delivery EVM probe is deliberately not reported green:

```sh
go test ./jvmevm -run '^TestMCLB0HarnessEVMMatchesPinnedJavaCatalogue$/empty-length$' -count=1
# FAIL: old runtime SHA-256 dfc81dbbea8253c644be2532a809a417bb40cd07eaca8ab5be72a84721eae929
# reverted with existing BytecodeError code 13 at pc 0; gas 971064
```

That failure is the expected integration dependency on the runtime worker, not a
waiver, skipped test, synthesized result, or EVM success claim. After runtime
integration, run `TestMCLB0HarnessEVMMatchesPinnedJavaCatalogue`; every row uses a
fresh watchdog subprocess and the production `Run` or `RunClasses` ABI.
