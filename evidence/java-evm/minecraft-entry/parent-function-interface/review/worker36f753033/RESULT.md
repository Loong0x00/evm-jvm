# Function interface slice — implementation record

Implemented one append-only `java/util/function/Function` bootstrap image (Java 8 classfile, 275 bytes, SHA-256 `0c295ec9f5fcca2672e7b39bb33639dcf5134397eab22909b0ee6b773609bf1a`). It is public/abstract/interface, extends Object, declares only abstract `apply(Object)Object` with generic signature `(TT;)TR;`; no native binding, default/static helper, or dispatch change. Raw bundle replacement is refused by the reserved-name guard.

The P42 105-image leaf list is unchanged at indices 0–104; Function is index 105. P43 bootstrap root is `f9bc0a2e1368e55ca1e9b8f04ce5addf0d8d2427ce73c9996a05c7a1fddec670`. New diagnostic combined-class bound is 256, with highest class index 255; raw count/bytes and every other quota remain fixed. Native binding count remains 21 and String-local binding remains 12.

Pinned solc 0.8.30 engine build: runtime 420227 bytes, SHA-256 `cdd478ced0cd26fe8b51f308041ad546848c5370a06d888e85a9f7259cf10255`, Keccak `2597ed2bbcb45d09ed951eb9a8fd0560538c10e13ebae9b77fce94491706017d`. Coordinator: runtime 5411 bytes, SHA-256 `ea78a31d4f8a5df30f04d9f5f4a324ccddead61db6bf3d10d09861e6ab693a55`, Keccak `54aa45b35f97743caa89d9242aaff45e578e4519e41a73f9f0079cb048f2b90a`.

## Checks run

- Verified all nine P42 source-base manifest file lengths and SHA-256 hashes before editing.
- Pinned Node/solc engine and coordinator builds succeeded.
- Recomputed 106 ordered bootstrap leaf commitments; verified the original 105 source expressions are identical and in the same order, and the new leaf bytes exactly match the Java 8 classfile.
- Generated-only Java fixture compiled to Java 8 classfiles and ran successfully on host as an oracle. It covers generic implementation, bridge invocation, inherited subinterface, state/identity/null values, `instanceof`, and caught null-receiver NPE.
- `go test ./jvmevm/...` passed; `go vet ./jvmevm/...` passed.

## Not claimed

No generated fixture was executed through the new EVM artifacts here; q1/q7/coarse equivalence, real EVM NPE/type/bridge outcomes, fresh-process checkpoint reopen, raw reserved-class refusal, and the protected original115 replay remain for the parent-owned independent gate. The new profile does not claim full `Function` API support: `compose`, `andThen`, and `identity` are omitted and unsupported. No original Minecraft inputs or resources were accessed.
