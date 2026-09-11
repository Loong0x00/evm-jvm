# MC-DI0 production runtime candidate evidence

This directory records runtime-writer verification of the exact embedded final
candidate, not DI0 acceptance. Inputs are generated fixtures only. No official JAR
was uploaded, inflated, or executed; no Java/ClassLoader/Minecraft/EULA/listener/
`Done` claim is made.

`replay.sh` reconstructs a fresh ignored workspace from the tracked final artifact
and archived parent generated-fixture drivers, changes only artifact field mapping,
production `MC-DI0/*/v1` oracle domains, the final-artifact 90,000-gas changed-write
probe, and three constructor name/root-priority controls. It checks 37 baseline
cases, 29 tree/Java8 cases, four 64-header cases, six same-binding q1/q128 pairs,
five complete q1..128 sweeps including 64/129 dynamic headers and mixed cache
transitions, 60-publication fresh-process persistence, and rollback/retry controls.

The initial final-artifact 70,000-gas trial is deliberately retained. It had a real
OOG and exact EVM frame rollback, but did not prove a completed changed SSTORE after
the added production dependency checks, so it is not counted. At 90,000 gas the
allowed opcode diagnostic observed the changed SSTORE before real OOG; roots matched
before any host restoration, and ordinary retry succeeded. The page-CREATE rollback
also removed code/state/nonce effects and retried at the same child address.

`verification-summary.json` gives exact compiler/artifact/dependency pins, caps,
measured sizes/gas, report hashes, and separately labels the DI0 resource final root
and EVM trie state root. Raw reports are preserved alongside it. Largest observed
step gas is a generated-fixture measurement, not a universal claim.
