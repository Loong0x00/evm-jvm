# Next actual MC blocker: System.arraycopy

Parent original13-class/184522B unchanged-JAR run now commits364 Java steps;
current actual failure is missing java/lang/System at static callPC29 in original
MarkerManager$Log4jMarker.setParents. Its signature is
`arraycopy(Ljava/lang/Object;ILjava/lang/Object;II)V`. Prior CP/Head survives.
No logging path was replaced. This authorizes only the required arraycopy substrate,
not complete System/JDK, clocks/properties/streams/threads/reflection or Session.

New isolated derivative of marker-map candidate25b1f35a0:
- Minimal non-overridable owned java/lang/System bootstrap with static arraycopy.
  Prefer genuine Java bootstrap bytecode over new native branches if feasible;
  existing interpreter supports ordinary primitive/reference arrays. Private/no
  public constructor, no synthetic host copying or JVM evaluation.
- Correct reference-array copying is required by the observed Marker[] path.
  Generic primitive copies may be included using existing representations; do not
  silently fake unsupported kinds. Keep Boolean/byte/char/short/int/long/float/
  double distinct; preserve primitive raw bits where existing VM allows.
- Same-array overlap must behave like memmove in BOTH directions. Distinct source
  and destination arrays, zero length, exact ends, and nonzero offsets work.
- Null input -> genuine Java NPE. Non-array/type mismatch -> genuine ArrayStore
  exception as appropriate. Negative/range/overflow positions -> genuine array
  bounds exception. Use Java8 TEST oracle for precedence (including zero length).
- Reference element mismatch copies the valid prefix before raising ArrayStore
  on the first incompatible element, rather than rolling back the whole Java
  effect. Bounds/type structural failures do not modify destination. Normal
  EVM failed-call rollback and terminal/caught Java exceptions remain distinct.
- q1/q7/direct/read-only EVM-issued checkpoint/reopen/alias comparisons. Do not
  invent immutable destination invariants between legitimate element writes.
  Current single guest-thread boundary, no new thread/concurrent atomicity claim.
- Retain16/262144COPY/44 old bootstrap indexes (append System), CP4096Code65535,
  heap/VFS/frames/CP1MiB,100M30s,25Mreserve,320KiBengine,20min4GiB whole watcher.
  No automatic budget/quota raise; keep actual refusal if a bound is hit.

Parent Go transport fix `bound_metadata.py` removes unbounded observation history
from authoritative Head while leaving the existing32768B cap unchanged. Use that
corrected driver or equivalent; don't regress to a Head that becomes unreadable
at1291 epochs. This is a necessary execution-path fix, not a new general Session
project. Full per-call receipts remain outside authority.

Generated fixture/oracle tests only for worker; no original JAR/class handling.
Parent independently rebuilds then retries original13 plus actual new missing
JAR bindings as needed. No fake Marker/Log4j/MC code, no host execution authority,
no accepted-profile promotion, no push.
