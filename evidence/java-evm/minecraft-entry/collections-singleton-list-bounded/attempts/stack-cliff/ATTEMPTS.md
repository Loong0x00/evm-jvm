# Preserved pre-guidance viaIR stack-cliff attempts

These are failed builds from the corrected 120-image source before the supplied ConfigRoot encoding guidance. They are preserved verbatim and are not acceptance evidence.

Pinned solc 0.8.30, optimizer 200, viaIR, Cancun failed with:

```
YulException: Variable size_20 is 1 too deep in the stack [ RET var_runtimeHash size_20 expr var_seedRoot var_entry_mpos size_21 var_entryClass_mpos size_2 size_4 size_13 size_12 var_artifact memPtr_2 expr_96 size_16 size_24 size_23 size_22 ]
```

The attempted, unsuccessful source-only refactors included extracting/splitting bootstrap parsing, changing the count/allocation, packing `_commit` arguments into `CommitContext`, changing `_encodeEnvelope` to `Envelope memory`, and extracting/wrapping `startMain` execution. The error persisted. No failed build output was promoted into the candidate runtime. The last successful 119-layout artifact is archived only as an incorrect-layout attempt; it was never reused for the corrected bootstrap slots.

`SHA256SUMS.txt` pins the untouched logs and both archived sources. Current correct 120-image source and successful build evidence live in the candidate root.
