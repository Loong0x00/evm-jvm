# Reproducer repair history

These are harness/reproducer failures, not guest successes and not evidence of
original execution. Fresh ignored build directories retain their file-backed
logs for this worker checkout; the durable details are recorded here.

1. The first run stopped before solc because `NODE_PATH` was incorrectly formed
   from this worker root. The gate now pins the required
   `/home/user/evm-jvm/geth/jvmevm/runtime/node_modules`.
2. The next run compiled the engine but stopped before coordinator compilation:
   a malformed copied engine-address literal made the narrow coordinator
   replacement non-unique. The corrected literal is asserted exactly once.
3. The next run stopped before generated Java/EVM execution because the
   caller-replacement fixture was not in its Java package-path filename. It is
   now `fixtures/java/security/PrivilegedAction.java`.
4. The next run reached a valid q1 VOID terminal head (226 Java/4 internal) but
   the gate looked for driver receipts beneath the world rather than the
   driver's sibling `reports/<world>` directory. No guest result was altered;
   the final run checks and archives the actual report location.

No original JAR/class/world was read in any run.
