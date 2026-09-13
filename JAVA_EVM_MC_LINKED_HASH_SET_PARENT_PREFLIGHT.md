# Parent LinkedHashSet preflight

**In progress; worker result is not acceptance.** Candidate commits6c7a5a950,
4735e71b4,7625023ff integrated. Parent independently found a semantic mismatch:
Java8 HashMap/HashSet duplicate insertion compares the incoming key to the stored
key (`item.equals(old)`), while candidate used `old.equals(item)`. Parent repairs
only that generated guest source/image and adds an asymmetric-equality Java8/EVM
oracle that distinguishes the directions.

Candidate's initial coordinator still referenced the old system-loader engine
address and honestly failed `MR0Error(3)`; candidate preserved and repaired it.
Its earlier host oracle also lacked equal hashes and did not test duplicate equals;
preserved. Final worker generated-only gate is useful but did not actually cover
its documented no-arg constructor or prior system-loader/Thread/etc controls.
Parent fixture covers noarg/int0/int2, two growths, ordered/equal/null/asymmetric
uniqueness, two cursors/exhaustion/NSEE, Collection/Set dispatch and all prior
loader/Thread/PrivilegedAction/System/Properties/arraycopy blockers.

Parent uses new all-nine engine/coordinator domains and addresses under the existing
LOCAL384 cap; accepted320 and every other cap unchanged. It source-compiles all9
images, verifies8 worker-identical and repaired HashSet distinct, then runs one
20min/4GiB build+generated+new-original22 q7/q1 gate. No getResources/fake empty
resource implementation, original payload archive, core/ABI/Makefile/push/Done.
Evidence: `evidence/java-evm/minecraft-entry/parent-7625023ff/`.
