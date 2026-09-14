# Measured raw-class-count26 preparation

Accepted bounded lock execution exhausts all25 raw slots and reaches
`StatusLogger.<init>` PC29, where unchanged bytecode genuinely requires same-JAR
`org/apache/logging/log4j/status/StatusLogger$BoundedQueue.class`. The class is1377
bytes (SHA256 pinned in parent lock evidence); appending it makes26 classes/229450 bytes,
below the unchanged262144-byte cap. q7/q1 failed calls preserve trie/head. The user has
already authorized genuinely measured incremental class-count growth under existing
safety/accounting limits.

Implement **25→26 only**:

* engine `MAX_RAW_CLASSES` and committed count word become26; byte cap stays262144;
* coordinator decoder/root/size/name fixed arrays and constructor guard become26;
* durable driver input/manifest guards become26 and reject27 before world creation;
* read-only diagnostic max class count becomes105 (raw26+bootstrap79);
* original inventory appends only the exact measured same-JAR BoundedQueue. No class bytes
  enter source/evidence and no host execution path is added.

Use fresh LOCAL384 engine/coordinator/address/domain/worlds. Prove the complete lock
engine semantics/bootstrap79 byte-identical except the count/domain changes. Generated
exact25/26 q1/q7/direct/reopen/canonical must pass; exact27 must refuse before mutation;
262145 aggregate bytes must return constructor MR0Error(12) atomically. Record, do not
mislabel, any exact262144/parser or direct retained fixed-1B infeasibility. Retain lock,
COW/OOM, Class.newInstance, Class/asSubclass, Integer/split/CNFE/resource/loader/VFS
controls.

Parent independently source-builds/replays and starts a fresh unchanged original26 q7
then q1. Keep bootstrap79, raw bytes262144, exception14, global native11, String-local10,
frames128, CP4096, Code65535, heap/VFS/checkpoint1MiB, Head32768, LOCAL1B/25M reserve/
30s per call and whole20min/4GiB fixed. Worker must not access original Minecraft
artifacts/worlds. No lazy loader, fabricated class/result, failed-state recovery,
main-body/world/Done claim, broader capacity or push.
