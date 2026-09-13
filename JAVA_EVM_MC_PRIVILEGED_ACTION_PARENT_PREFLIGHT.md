# Parent PrivilegedAction preflight

**In progress; worker generated result is not parent acceptance.** Worker commits
e0c571c76..a30955bb0 were integrated locally. Parent evidence/recipes:
`evidence/java-evm/minecraft-entry/parent-a30955bb0/`.

Parent review found the worker changed only the engine's DBOOT string to the new
profile; the other eight engine domain strings still used the security-getter
profile. This violates required full domain isolation even though runtime codehash
already differs. `rebuild.py` first reverses the worker semantic delta and proves
byte-for-byte equality with parent-2293e298e, independently compiles the198B
PrivilegedAction image, then applies the same interface delta with **all nine**
engine domains unified as `MC-PRIVILEGED-ACTION-PARENT1`. Coordinator, engine,
owner/other addresses and driver identities are separately replaced. The worker
candidate is retained as generated evidence but is not promoted.

Only `java/security/PrivilegedAction<T> { T run(); }` is appended after prior48
bootstrap images. It grants no privilege. No AccessController, ClassLoader,
SecurityManager, Thread, permission or resource-search API is included.

Parent `run.sh` uses one20min/4GiB outer process group for source-only Java/solc/
Go build, fresh generated q1/q7/direct/reopen and a new original22 q7 world. It
then preserves that failed-call diagnostic and supplies public ResumeMain budget1
against the same successful code/checkpoint, up to256 observations, so original
steps are credited only after successful EVM checkpoints. LOCAL1B,30s/call,
25Mreserve,24/262144,128frames and all other limits remain unchanged. No original
payload archive, accepted/core/ABI/Makefile/push change or Done claim.
