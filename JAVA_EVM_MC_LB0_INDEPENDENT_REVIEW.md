# MC-LB0 independent review

Review target: `f50fe142a7442788179687463d783edaf4dca523`

Runtime: 166,334 bytes, SHA-256
`ff9c9ff093e9d4885d7546e01db7aacd95cf999d5cf9b6d6b130fd43b791b982`.

This is a bounded review of the frozen `JAVA_EVM_MC_LB0_PLAN.md`, not a replay of
the 64-row catalogue and not acceptance of a later Minecraft/platform stage.

## Result

One concrete hard-error ordering defect remains.

### Defect: malformed profile-call descriptors are mislabeled as unsupported String APIs

The frozen contract says malformed constant-pool/descriptors must fail under the
existing call rules before a String profile boundary. A raw classfile mutation of
an otherwise valid call descriptor to a syntactically invalid descriptor instead
returns:

`StringProfileError(1, callPC)` (selector `0x32e310eb`)

at `f50fe14`. This occurs in all three independently checked profile call shapes:

| shape | mutation | call PC | actual gas |
|---|---|---:|---:|
| `invokevirtual java/lang/String.isEmpty` | `()Z` -> `()Q` | 2 | 2,839,609 |
| `invokeinterface java/lang/CharSequence.length` | `()I` -> `()Q` | 4 | 2,661,679 |
| `invokestatic java/lang/String.valueOf` | `(I)Ljava/lang/String;` -> `(Q)Ljava/lang/String;` | 1 | 1,501,923 |

The committed regression expects the existing malformed-callee result
`CallError(4, callPC)`. An ordinary non-profile `invokevirtual` baseline, with its
resolved declaration and call descriptor both mutated from `(I)I` to `(I)Q`, does
already return exact `CallError(4,pc)` (1,299,202 gas). Thus the result is not a
Java semantic mismatch; it is a hard validation/profile taxonomy and ordering
bug. The likely source boundary is profile fallback before descriptor syntax
validation in `_resolveVirtual`, `_resolveInterfaceCall`, and `_resolveCall`.
Production was intentionally not changed by this reviewer.

Exact reproducer:

```sh
timeout 30s go test ./jvmevm \
  -run '^TestMCLB0ReviewMalformedStringDescriptorMustUseExistingCallError$' \
  -count=1 -v
```

At the reviewed revision its three profile subtests fail with exact
`StringProfileError(1,pc)` where `CallError(4,pc)` is required.

## Independent positive coverage

The other 14 independent EVM executions pass (17 total executions including the
three defect reproductions), without reusing catalogue fixture classes:

- pinned artifact size/hash and current production `runtime.Execute` boundary;
- five strict MUTF-8 precedence cases absent from the catalogue/verifier matrix:
  truncated four-byte/invalid leads, continuation-before-overlong checks, and a
  `c1` overlong form, including exact absolute offsets;
- a non-String `CharSequence` implementation dispatching ordinary `length`,
  `charAt`, `subSequence`, and `toString` Code;
- a non-String `Comparable<T>` implementation whose compiler bridge executes
  ordinary bytecode and throws genuine CCE for a wrong object;
- Java 8 interface-default `Interface.super` `invokespecial` dispatch;
- fresh/interned aliases across String `ConstantValue`, `<clinit>`, a static field,
  method argument/return, and a reference array;
- a successfully prepared String constant followed by failing `<clinit>`, then
  exact EIIE/poisoned-class NCDFE behavior;
- unsupported static `String.valueOf` remains a hard String profile error;
- a raw `invokevirtual` -> `invokespecial` mutation cannot select a String native
  and remains an ordinary `ObjectError(3,pc)` boundary.

The non-String dispatch and reference-lifecycle values were compared from the same
Java-8-target class bytes on Java 8 and Java 21 before EVM comparison. Maximum gas
among the passing positive probes was 5,765,577, below the frozen 100,000,000 local
ordinary cap. The whole positive review gate completed in about one second under
a 30-second shell watchdog. No 1,000,000,000 boundary probe was needed.

Source review also covered exact native owner/name/descriptor/flags/no-Code
binding, the ordinary bridge precedence, receiver and argument checks, interface
selection, String layout/backing validation, global content-checked intern lookup,
miss preflight/publication, shared heap aliases, static constant preparation and
poisoning, and strict MUTF-8 decode/offset logic. The inherited
`Object(1023)+String(2)` field-layout fix correctly routes allocation through
catchable OOM rather than `BootstrapProfileError`; no second defect was found in
those bounded paths.

Passing command:

```sh
timeout 30s go test ./jvmevm \
  -run 'TestMCLB0Review(Artifact|MUTF8|NonString|Fresh|Unsupported)' \
  -count=1 -v
```

## Boundary and limitations

All execution evidence uses the checked-in oversized runtime through geth's
unmodified local `runtime.Execute` EVM path. The host only compiles trusted test
fixtures, ABI-packs raw class bytes/entry/int arguments, and checks results; there
is no host Java production fallback or text/metadata injection. The source-boundary
test additionally checks that the current production runner still calls
`runtime.Execute` and contains no process-execution marker.

This does not prove ordinary CREATE/EIP-170 deployability, stock-chain transaction
feasibility, persistent continuation, String construction/composition or complete
Java String/Object APIs. It adds no `main`, VFS, scheduler, thread, output,
listener, server execution, EULA acceptance, Minecraft startup, or ready-marker
evidence. The 64-row catalogue, parent UTF-16 vectors, and broad old gates remain
parent-owned evidence and were not recounted as independent probes here.

## Parent integration resolution

The finding above records historical f50fe14 behavior. Parent reproduced it and
fixed d07c72c, validated every17reviewprobe, rebuilt166385B runtime SHA256
`ea94075540b8b66aa8e85823ee66e9dba4a2be65f29942855a8f59478bca0cbf`, and reran allLB0/2231/stock/Python/artifact/demo/AOT/vet gates successfully.
No malformed-descriptor test was removed or weakened. See JAVA_EVM_MC_LB0_REVIEW.md.
