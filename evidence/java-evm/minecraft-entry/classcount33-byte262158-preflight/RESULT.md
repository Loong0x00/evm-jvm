# Result: generated raw33 / byte262158

- Exact parent: `parent-1709f8e18`; only raw selected classes `32→33`, raw
  bytes `262144→262158`, and diagnostic classes `118→119` changed.
- Runtime: 392076 / 393216 bytes, SHA-256
  `24b6fb025503dd2b4e563476f7f2268e9ec6ac1730484be8384ad1c6dd5dd6b9`.
- Raw33 q1/q7/direct/reopen agree at 132 Java / 2 internal steps, epochs
  132/19/1, with identical machine root and opaque payload.
- Raw34 is atomically refused at driver, coordinator (`MR0Error(2)`) and
  engine (`LinkError(1,34)`). Exact 262158-byte input is coordinator-admitted
  and reaches engine reads; 262159 is atomically rejected (`MR0Error(12)`).
- One source build and generated gate passed in 105.847 s (cap 1200), with 77
  rows, 258 commands and 750 canonical receipts.

No original artifact/JAR/class/resource was opened. Parent alone runs original33;
no Provider construction, factory, world or Done claim is made.
