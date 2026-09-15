# Parent acceptance: bounded ACC_ENUM admission

Parent independently accepts the single semantic mask change `0xe000 -> 0xa000` for
non-interface classes. Domain `MC-ENUM-FLAG-PARENT2`; engine388963B, SHA256
`50c5cd6ffefd559658b7c879bf4763b70b6336d1eaf7f6702fc13b609f5698da`, Keccak
`db5607160a3e035397de19a287fef688e7c34c92d0f5e2d2ee834201815f0f1a`.
Build279.17s/985874432B. Parent Java8 flag matrix gate13.62s and retained cap29 gate
42.65s pass: enum-marker is admitted; annotation/module/E+A/E+M remain refused;
interfaces retain behavior; genuine Java8 enum reaches honest missing-Enum hierarchy.

Fresh unchanged original29 is rerun (no raw class added). q7/q1 return
`HierarchyError(1,28)` after the same3946J/epoch568/34-internal head, proving ACC_ENUM
admission and exposing absent superclass `java/lang/Enum`; Java8 javap pins that exact
superclass. All568 receipts verify canonically. Failed roots unchanged. No enum
initialization/main-body/world/Done claim.
