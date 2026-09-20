# Result

- Corrected image83 is a valid 317-byte Java-8 `PrintStream`: private `print:C`
  field and public `print:(C)V` method. Bare method descriptor `C` is rejected
  by the source verifier.
- Corrected leaf: `3731cc740c09a9df0c76d9775252bff86b931e928d443a2e340f9d7076deca45`;
  bootstrap root: `09a9cc5db29c035f2b4ca32375d09f7ac55706628773579449a9bceff612f636`.
- Corrected pre-layout is 393308 bytes (over cap); selected bounded-loop cleanup
  builds at 393185/393216 bytes, 31-byte headroom.
- Full generated-only q1/q7/direct gate plus reopen verification passed:
  607.788s, 591 commands, 180 worlds, and 10007 canonical receipts. NUL, ASCII,
  unpaired surrogate, and U+FFFD all preserve their exact final char cell.

No host output, original artifact, Minecraft execution, world, or Done claim.
