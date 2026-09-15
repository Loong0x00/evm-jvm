# Parent amendment

The worker's Solidity layout repair and source verifier are retained unchanged. The parent corrected the generated gate's StringBuilder quota expectation: the fixture's live 65536-char arrays cannot fit the fixed 1MiB checkpoint, so it must produce an atomic `LC0StateError(1,0)` publication refusal rather than a fabricated catchable terminal OOM. The existing small field-arena fixture continues to prove catchable guest OOM.

Independent optimizer200 source build produced a 386100-byte runtime. The amended full generated gate then passed in 132.045s with 1607 canonically verified receipts, including StringBuilder q1/q7/direct/reopen, bounded-null, uninitialized, honest quota infeasibility, replacement, System.err, failed-init, raw30/31 at all three layers, byte boundaries, EnumSet/ACC_ENUM, queue and retained OOM.
