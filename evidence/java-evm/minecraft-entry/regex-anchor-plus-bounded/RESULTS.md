# Results: P41 regex anchor/plus and `Matcher.matches`

## Implementation

Only `Pattern.java` and `Matcher.java` class images changed among the ordered 105 EVM bootstrap leaves. PAT1 remains the exact prior fixed-width program representation. PAT2 is an eager private int[] format with flags, absolute start/end-anchor bits, and existing literal/class tokens plus one greedy `+` opcode. To bound execution without inventing backtracking, `+` is admitted only when it quantifies the sole literal or character-class atom (optional `^`/`$` and existing `(?i)` modifier). Existing fixed-width literal/class sequences remain supported. `Matcher.matches()` calls the genuine compiled matcher at start zero and requires returned end == input length. `replaceAll` still uses its existing Java replacement parser and match advancement; anchor handling is inside `matchAt`.

Java 8 `$` recognizes the final line terminator boundary (LF, CR, CRLF as a unit, NEL, LS, PS); `matches()` still requires full region consumption. Surrogate-bearing pattern/input retain the prior conservative refusal. Valid constructs outside this subset retain the existing unbound unsupported-profile branch; malformed trailing escape, unclosed class and leading quantifier keep PatternSyntaxException behavior. No new operational native or helper bootstrap was added. No interpreter dispatch, heap, clone, checkpoint, VFS, quota, core/vm or core/state code changed.

Only interpreter source image bodies for Pattern and Matcher were changed. The coordinator has the one required authenticated engine-codehash update; its other source is identical to P41. ABI/storage layout are unchanged for both fresh artifacts.

## Baseline / artifacts

`source-baseline.txt` records all 13 source snapshot hashes/lengths and the exact P41 four-class javac-to-materializer matches. Build: `tools/build-profile.sh`; Java 8 compiler `/usr/lib/jvm/java-8-openjdk`, solc `0.8.30+commit.73712a01.Emscripten.clang`, NODE_PATH pinned to the repository node_modules.

| item | P41 | regex build |
|---|---:|---:|
| Pattern image | 4,834 B, SHA256 `483c47a95edd6abdaa4eacc751e0cb36986f60cdaf3e911f6bc4a6ae13242fe9` | 6,199 B, SHA256 `0743ca2495f3fe8ee2e1aa9c1d62638d1da21cfb194c4e261e12bbdc6f9cd85e` |
| Matcher image | 1,703 B, SHA256 `5232a8d6198b7ef56a8fbbdbc03f4e790aedb28cf9ad8b2df729691d5f9350ea` | 1,795 B, SHA256 `b700a9132adb459780c42b5930c6e10c17b550565962180d0c6f33d7c17547de` |
| String / PSE | 2,198 B / 967 B | byte-identical |
| interpreter runtime | 418,986 B, SHA256 `32a16b78a9cec4b72835eaab094c715e3a5f310ed9f2b211d49e29237c5b5f02` | 420,866 B, SHA256 `8895b9e496571f83033c99b3816ae6376d3b450ac93b0efcd048df600a5bf7e4`, Keccak `736da9ef054438e79f27c2992358f3af0c54218a9fa4c5a6358fefa8e102dd58` |
| coordinator runtime | 5,411 B | 5,411 B, SHA256 `e5e28662d676a495e4411bf98c645a12fe7ca2076f04555755f67ab49a2e4e27`, Keccak `fcb66f09e4964c87045301d39f0a7f9a94ace1e5977f19d74c895dd96ab551ac` |
| bootstrap root | P41 `ca3049ae9ad4e09e893a897c34ef016939d1595c01d090c5ee3e9699ac349fbd` | `2a19bc0c9507de1ff8b30e0eb10e050aae92ff6f22b33bb16e4a8f1cd9ea2290` |

The full 105-leaf ordered root was reconstructed from actual Solidity image bytes. Only leaf slots 101 (Pattern) and 103 (Matcher) differ. Bootstrap count=105, native bindings=21, engine runtime=420,866 B (<1 MiB). Actual source hashes/artifact and root pins are in `pins.json` and the generated engine/coordinator JSON files. ABI and storage layout compare byte-for-byte equal to the source-only P41 artifacts.

## Generated tests

`RegexSemanticsProbe.java` is oracle-only, run separately with stock Java 8 and with the generated Pattern/Matcher images prepended; output is saved in `results/oracle.txt` and `results/custom-jvm.txt`. Exact outputs agree for distinct literals/classes/ranges/negated classes, anchors/plus, minimum-one/empty, greedy replacement and `$0`, identity on no match, ASCII case-folding, start/end behavior, escaped punctuation, LF/CR/CRLF/NEL/LS/PS, nulls, malformed classes/escape/replacement. `RegexAnchorPlusGuestProbe.java` is a trusted generated EVM guest fixture and passed under both host Java 8 and the genuine P41-derived EVM.

The EVM fixture's q4096 world completed lifecycle 2 with 22,117 Java / 12 internal steps; total engine gas 2,774,043,766, peak external EVM call 555,117,880 (ordinary test budget 1B). q65536 completed the same Java fixture and exact machine/VFS roots with 22,117 / 12 steps; engine gas 5,129,923,032, peak call 5,095,096,575 (test-only external gas budget 8B). Distinct setup and completion OS processes reopened normal persisted checkpoint state; each complete world was then independently passed through the public driver `verify` route.

The small one-plus guest witness passed at q1 and q7 under the ordinary 1B test budget, with exactly 515 Java / 2 internal steps. Machine root `840795981e707f3a7fcf5d2db7b713b1191e6eb0df9a699db94cf06cb6209c12` and VFS root `df1b03248fa6c150f72b216960d2ffe0388f1f240cf06a93248f714643095de8` match exactly across quanta. The broader q4096/q65536 fixture likewise has identical machine/VFS roots, Java/internal steps, result/lifecycle and artifact/config roots. Transport gas, call/commit counts and epochs are expected to vary by quantum.

## Preserved budget failures / test-driver caveat

q65536 initially failed at ordinary external test budgets 1B, 2B and 4B with typed `LC0ControlError(7)` after measured gas of 960,802,779; 1,944,354,944; and 3,913,880,032 respectively, with root/Head unchanged. The test-only driver now accepts `MC_REGEX_TEST_GAS` from 1B to 8B (default 1B); q65536 passed at 8B. This changes no EVM rule, opcode, accepted runtime quota or guest result. Each shortage world and receipt remains under `results/world-q65536*` / `results/reports/world-q65536*`. A preliminary generated ZIP binding used dotted rather than path entry name and was refused by DI0 with code 4; that world is retained, and the proper path binding is used in passing worlds. A first fixture iteration accidentally used a two-backslash regex (valid literal backslash) where a trailing-escape malformed case was intended; host-Java failure was corrected in the fixture and all subsequent passes use the actual trailing escape. Valid unsupported alternation (`a|b`) was exercised as a separate generated guest: it produced the existing raw `CallError` refusal (selector `0xd631c3a4`, code 3, PC 4), no checkpoint, and unchanged Head/root; no synthetic match or guest exception. A separate surrogate-input guest likewise retained the existing raw `CallError(3,61)` conservative refusal, with no checkpoint and unchanged Head/root. Historical mislabeled P41 copied-driver receipts are preserved; fresh driver receipts now label the actual finite test budget.

## P42 parent-generated-review correction

The P41 results above remain historical candidate evidence. The parent supplied a verified generated-only 60-case Java 8 fixture; 25 differences identified two real issues, corrected in P42: admitted greedy `+` now backtracks only the consumed CR at the final CRLF boundary for `$`, and valid quantified zero-width anchors (`^+`, `^*`, `^?`, `^+$`) take the raw unsupported-profile refusal rather than an invented syntax error. Mutable `CharSequence` input is revalidated for surrogates at every `matches()`/`replaceAll()` call. No generalized regex backtracking was added.

See `P42_REVIEW_FIX.md` and `p42-generated-receipts.json` for verified manifest hashes, fresh authenticated build/root/ABI/storage results, q1/q7/q4096/q65536 exact machine/VFS equivalence and fresh-process reopen, and Head/root-atomic raw-refusal receipts. Build tooling now uses computed repository paths and a new unique output directory; the old artifact JSON/hex and worlds were preserved. Current pins record only Pattern/Matcher leaf deltas; P41's false all-105-unchanged claim is retained only in `legacySourceInvariants`. This remains unaccepted pending parent independent review. No original input was accessed or executed.

## Explicit non-claims

No original Minecraft class/JAR/resource, parent input or evidence was read. Parent alone owns any original replay. This is a bounded regex subset, not full Java regex; no original caller execution, Minecraft startup, EULA/world/Done or general Pattern conformance is claimed. Parent independent review is still required before acceptance.
