# Result

- Image83 only: Java 8 non-null `PrintStream.println(String)` directly stores
  its exact guest String reference in private `println`; null is outside this
  bounded profile and no other output overload exists.
- Image: 239 bytes, SHA-256
  `0fda0bcbb7ca6f8aae2dc8e38494fc75df623712dfef520520a1bdbd4f4ecd5b`;
  keccak256 `ffdfe270a5c4faeeff544874a0a181720d4a29abce5385d400b8749a204fe271`.
  The root retains dynamic Object and all historical leaves; only leaf83 is
  `DBOOT_PRINT_STREAM`.
- The three bounded-slice source-layout placements lower the measured
  393217-byte direct-store candidate to 393200/393216 bytes (16-byte headroom),
  SHA-256 `d99183c8e4ce289ad0cc50f9d4c68791a474b87425be5113ea3f29e6b960ef34`.
- Focused non-null empty/ASCII/surrogate/replacement q1/q7/direct/reopen chains
  preserve machine/checkpoint equality and read-only heap reference identity;
  omitted print/println forms refuse atomically.
- Full focused-plus-retained generated gate: 597.792s, 9818 canonical receipts.

No original/JAR/resource/provider/world/Done input or claim; no host output or
other `PrintStream` overload is added.
