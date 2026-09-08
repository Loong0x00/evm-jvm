# Stock S1 independent validation

This directory is the frozen S1 validation slice. It is separate from accepted
Stock S0 and from the oversized M5d-a local interpreter.

`validation_test.go` deliberately does not use S1 harness execution helpers. It
independently reads the four pinned S1 artifact JSON files and uses the accepted
S0 `ArtifactPage` artifact for raw class pages. Missing S1 artifacts are an
honest integration dependency and fail the tests; this directory contains no
substitute bytecode or fabricated committed hashes.

The verifier funds only a deterministic test EOA, signs every transaction,
recovers its sender, keeps nonce and transaction checks enabled, and executes
ordinary `CREATE` and calls through `core.ApplyMessage`. It validates generated
receipts against execution gas and logs. Executable code and contract storage are
never injected through genesis, `SetCode`, or `SetState`.

The bounded class generator creates only trusted, small classfile-shaped inputs.
An independent test decoder derives expected schema-2 metadata from those raw
bytes. That decoder is assertion-only: production registration and execution
receive no host offsets, instruction starts, literals, branch decisions, state,
or expected result.

The tests cover the frozen ABI and roots, six metadata headers and four words per
declared method, literal ordering and caps, parser provenance/canonicality and
idempotence, unused invalid method selection, signed branches and same-PC loops,
0–4 arguments and six locals, exact step-cap semantics, dirty accounting,
rollback/OOG/reserve behavior, all 46 B/O/C negative intents, deterministic
signed replay, artifact/metadata sizes, and the existing EIP-170, EIP-3860 and
EIP-7825 protocol layers. Successful registration and resume gas remain bounded
by 8,000,000 and 2,000,000 respectively, with the coordinator's 800,000 gas
reserve unchanged.

A lifecycle-2 checkpoint is a successful finite `STEP_LIMIT` outcome, not a Java
return, exception, OOM, or fabricated result. `RETURNED` wins when the real
`ireturn` is the instruction at the exact committed cap.

This verifier does **not** establish S1 acceptance by itself. Until parent
integration independently reviews the production runtime, harness, exact code
hashes, gas report, and retained S0 gates, there is no S1 deployment claim. S1
is only a one-class, one-frame integer profile; it is not the 2,231-case M5d-a
profile, a general JVM, a Minecraft startup result, or evidence of client
connectivity. No Minecraft server or EULA is used here.
