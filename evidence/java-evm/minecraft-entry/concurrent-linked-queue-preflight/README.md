# ConcurrentLinkedQueue bounded bootstrap source

Append-only LOCAL384 preflight source for the raw26 cap profile.  The strict verifier
rebuilds all Java 8 images from a stripped bootclasspath, proves the accepted 79-image
tail byte-identical, and permits only `Queue` at index79 plus
`ConcurrentLinkedQueue` at index80.  The latter is a single-guest-thread `Object[]`
copy/publish FIFO subset: no host/native queue, scheduler, locking, or broader Queue API.

The generated-only gate uses trusted Java8 fixtures only.  It exercises queue hierarchy,
FIFO duplicates, null NPE, poll/size/inherited isEmpty, COW iterator snapshot/exhaustion,
q1/q7/direct/reopen canonical roots, both raw-replacement refusals, and a retained lock
focused control.  It intentionally does not access original Minecraft artifacts or worlds.
