# MC-ENTRY runtime COPY preflight

Unaccepted isolated candidate based on `3a7407df8`. It is generated-fixture evidence only; it has not accepted any `jvmevm` profile, run an official class/JAR, or executed Minecraft.

* Engine: `MCEntryInterpreter`, LOCAL initial-state install only at `0x4D43454e545259454E47494E4500000000000001`; it is not standard `CREATE` deployable because it exceeds EIP-170.
* Coordinator: ordinary `CREATE`, pinned to engine Keccak `9d4f...a61c`; constructor and runtime remain bounded by its build checks. AS0/ZI0/DI0 controllers/pages remain ordinary `CREATE`.
* Domains: `JVMEVM:MC-ENTRY-PREFLIGHT:{ROOT,ARTIFACT,BOOTSTRAP,CONFIG,MACHINE,SEED,VFS,FILE}:1` plus `MC-ENTRY-PREFLIGHT/{package,resource,vm}/v1` in the coordinator. These are new identities, not accepted MR0 pins.
* Limits: 16 raw images, total raw bytes <=262144 and each coordinator resource <=262144. Existing CP4096, Code65535, frames/heap/VFS/checkpoint1MiB, DI0 read <=4096, 100M ordinary-call budget and 320KiB engine limit remain.

`Runnable.class` is a Java 8 `public interface` with `public abstract run()V`, generated from `bootstrap/java/lang/Runnable.java` by `bootstrap/build_runnable.py`; its SHA-256 is `62b7507db061291cabfd6dfc715f80eeb2fa314f3f03e426be2c321cef48a8ff`. User-supplied Runnable follows the existing supplied-class/duplicate rules; otherwise it appends after the existing fixed 38 bootstrap slots, so historic indexes do not move.

`MCEntryMissingClass(site,context,name)` is diagnostic-only and always reverts. Sites `0x1001` cast, `0x1002` interface edge (context=owner class index), `0x1003` virtual, `0x1004` interface virtual, `0x1006/0x100a` special, `0x100b` static, `0x1007` field, `0x1008` new, and `0x1009` anewarray use PC context except 0x1002. Other existing missing-class paths retain their original errors (handler, array descriptor/reference validation); malformed CP/type/access paths are unchanged.

`RESULTS.json` summarizes fresh opaque ZIP -> AS0 -> ZI0 -> DI0 -> coordinator receipts. The ignored raw worlds were `build/java-diff-mc-entry-runtime-smoke-*`; no raw class was passed directly to the engine. Full phase/Open/CAS/session matrices, capacity/density, and original-JAR probes were deliberately not run here.
