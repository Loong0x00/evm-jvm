# Read-only scope review: is `LinkError(5,28)` enough to authorize ACC_ENUM admission only?

Isolated reviewer. Worktree `/home/user/evm-jvm/mc-enum-review-ds`, HEAD
`3785c26958e58cc9724e90fe867b1aabd3713dce`, branch `mc-enum-review-ds`, clean.
No parent directory, other worktree, network, original JAR, host `classes/` or world was
read. No tracked file, build, commit or push was touched. Inputs read:
`JAVA_EVM_MC_ENUM_FLAG_PREPARATION.md`, `JAVA_EVM_MC_CLASSCOUNT29_PARENT_PREFLIGHT.md`,
`JAVA_EVM_MC_CLASSCOUNT29_PREPARATION.md`,
`evidence/java-evm/minecraft-entry/parent-17e21d664/{javap-StandardLevel.log,
original29-bindings.json,original29-frontier.json,rebuilt.py,generated_gate.py}`,
`classcount29-preflight/{engine/MCEntryInterpreter.sol,tools/verify_source.py,
tools/generate_fixtures.py,pins.json}` and the tracked
`jvmevm/runtime/JVMSubsetInterpreter.sol`.

## 0. Measured blocker, re-verified from archived evidence

- q1/q7 terminal is `execution reverted`, selector `0x427cfac5`, words `[5, 28]`
  (`original29-frontier.json`). I recomputed the selectors: `0x427cfac5` is
  `LinkError(uint256,uint256)` (control: `CallError` = `0xd631c3a4`, matching the
  historical logs), so the revert is exactly `_requireSupportedClass -> LinkError(5,28)`.
- Binding index 28 (0-based) of `original29-bindings.json` is
  `org/apache/logging/log4j/spi/StandardLevel.class`, so detail `28` is that class,
  not a bootstrap image.
- Archived `javap-StandardLevel.log` shows
  `flags: ACC_PUBLIC, ACC_FINAL, ACC_SUPER, ACC_ENUM` (0x4031); 0x4000 is the only bit
  of `0xe000` present.
- Engine line 3003 of the archived parent artifact is the whole policy:
  `if ((c.accessFlags & 0x0200) == 0 && (c.accessFlags & 0xe000) != 0) c.unsupportedSemantics = true;`
  and line 3051-3053 turns that into `LinkError(5, classIndex)`.

## 1. Verdict

**Conditionally yes.** The measurement is sufficient to authorize *only* the ACC_ENUM
parser-policy sub-step (removing 0x4000 from the reject mask for non-interface classes)
at the existing cap of 29 raw classes / 262144 bytes. It is **not** sufficient to:

- authorize any cap/coordinator/driver widening,
- authorize ACC_ANNOTATION (0x2000) or ACC_MODULE (0x8000),
- assert that StandardLevel links, initializes or executes,
- predict what the parent's next original run will report.

Two preconditions must hold before acceptance:

1. **Raw-flag precondition.** `javap` is a host convenience dump and cannot prove the
   *absence* of undefined/other 0xe000 bits (it prints the flags it knows). Since the
   original JAR is out of scope here, the parent must independently re-read the 2-byte
   `access_flags` of the hash-pinned StandardLevel bytes and assert
   `(flags & 0xa000) == 0` **and** `(flags & 0x4000) != 0`. If `0xa000` is non-zero the
   proposed mask still rejects the class and "ACC_ENUM-only" would be insufficient.
2. **Implementation-form precondition.** The change must be the negative mask in §2,
   not a "contains 0x4000" or "== 0x4000" test (see §3, the E+A / E+M leaking forms).

## 2. Minimal safe boolean condition

Replace the single condition at `_parseBundleClass` (archived engine line 3003; the same
line is at tracked `jvmevm/runtime/JVMSubsetInterpreter.sol:483`):

```solidity
// current
if ((c.accessFlags & 0x0200) == 0 && (c.accessFlags & 0xe000) != 0) {
    c.unsupportedSemantics = true;
}

// minimal safe change: drop only 0x4000 from the rejected set
if ((c.accessFlags & 0x0200) == 0 && (c.accessFlags & 0xa000) != 0) {
    c.unsupportedSemantics = true;
}
```

`0xa000 = 0xe000 & ~0x4000 = ACC_ANNOTATION(0x2000) | ACC_MODULE(0x8000)`. This is the
smallest safe edit: the interface bypass `(accessFlags & 0x0200) == 0`, the field,
the `_requireSupportedClass` site and every other parser byte stay identical. ACC_ENUM
stays a *marker only*: no Enum is fabricated, no hierarchy step is skipped, no
initializer is faked, no enum method is implemented.

Do not use any of these (all are holes or over-rejections):

- `(flags & 0xe000) != 0 && (flags & 0x4000) == 0` → admits `E|A` (0x6000) and `E|M`
  (0xc000), because the E bit suppresses the whole test.
- `(flags & 0xe000) == 0x4000` (equality) → rejects the real StandardLevel (0x4031),
  which also carries FINAL/SUPER.
- dropping the `(flags & 0x0200) == 0` guard → changes interface-path classification for
  0x2000/0x8000 interfaces (currently they are rejected later by
  `_validateInterfaceHeaderAndMethods` via `(flags & 0xe010) != 0`; keep that path
  byte-identical).
- widening to "admit 0xe000" or removing the check.

Hardening beyond the mask (e.g. requiring `super == java/lang/Enum`) is *not*
recommended: constant-specific-body enums have anonymous subclasses whose super is the
enum type, not `java/lang/Enum`. Structural validity is already enforced later by
hierarchy resolution (`HierarchyError(1, ...)` for a missing super), so the flag policy
should remain a pure marker filter.

## 3. Flag matrix (class access_flags only; FINAL/SUPER/ABSTRACT/SYNTHETIC ignored)

Legend: `I`=0x0200 interface, `A`=0x2000 annotation, `E`=0x4000 enum, `M`=0x8000 module.
"link" = downstream path once `unsupportedSemantics` is false; `IE1` =
`InterfaceError(1, idx)` (selector `0x069163bc`), `LE5` = `LinkError(5, idx)`
(`0x427cfac5`), `HE1` = `HierarchyError(1, idx)` (`0xa52e829f`).

| flags (semantic bits) | current | proposed | notes |
|---|---|---|---|
| — (plain class) | pass | pass | unchanged |
| E (0x4031 StandardLevel) | `LE5` | pass → next link step | intended change |
| A | `LE5` | `LE5` | unchanged |
| M | `LE5` | `LE5` | unchanged |
| A+E | `LE5` | `LE5` | mask keeps this rejected |
| M+E | `LE5` | `LE5` | mask keeps this rejected |
| A+M | `LE5` | `LE5` | unchanged |
| A+E+M | `LE5` | `LE5` | unchanged |
| I alone | pass | pass | interface validation path |
| I+E (0x4200) | `IE1` | `IE1` | caught by `(flags & 0xe010)` |
| I+A (0x2200) | `IE1` | `IE1` | annotation-interface rejected |
| I+M (0x8200) | `IE1` | `IE1` | rejected |
| I+A+E(+M) | `IE1` | `IE1` | rejected |

Consequences to record, not to "fix":

- **E without a reachable superclass.** A plain class patched to set E but not extending
  `java/lang/Enum` is now admitted and treated as an ordinary class. ACC_ENUM is a
  permission marker, not a semantic capability; the profile gains no enum behaviour.
- **Reachability matters.** `unsupportedSemantics` is set at parse time but only
  *checked* for the root and for hierarchy-reachable classes (`_validateHierarchy`) and
  for interfaces (`_validateInterfaceHeaderAndMethods` via `_validateInterfaceClosure`).
  An unreachable class carrying A/E/M is never rejected today and still is not after the
  change. Every negative fixture below must therefore force resolution of the class.
- **Enum interfaces are already rejected** by the interface header check, so the change
  does not need a new interface-side branch.

## 4. Required generated tests (no original input)

### 4.1 Java-8 generated enum fixture (admission hand-off, not success)

Mirror StandardLevel's shape with `javac -source 8 -target 8 -g:none`:

```java
public enum TestLevel { OFF, FATAL, ERROR, WARN, INFO, DEBUG, TRACE, ALL; }
public final class EnumMain {
    public static void main(String[] a) { if (TestLevel.values().length != 8) throw new Error(); }
}
```

`TestLevel` is 0x4031 (PUBLIC|FINAL|SUPER|ENUM), exactly the measured shape. Bundle
`[EnumMain.class, TestLevel.class]`; entry `EnumMain`. Deterministic gate:

- pre-change control: selector `0x427cfac5`, words `[5, 1]` (TestLevel index 1);
- post-change: selector `0xa52e829f`, words `[1, 1]` (missing `java/lang/Enum` super —
  the engine has no `_bootstrapEnum`; `Enumeration` is a different image).
- assert under q1/q7/direct that the terminal is the same selector+words and that the
  terminal bytes/decoded frame are quantum-invariant. Because this terminal is a link
  refusal there is no committed checkpoint, so this fixture proves parser hand-off only
  and must **not** be used as the canonical/reopen gate.
- The fixture must call `TestLevel` so the class is actually resolved; otherwise the flag
  check never runs and the test is vacuous.

### 4.2 Byte-patch negative fixtures

Patch the 2-byte `access_flags` (offset: `8 + 2` bytes header then parse constant pool).
Reference parser (validated against 50 tracked `.class` files, offsets and values match):

```python
def access_offset(b):
    assert b[:4] == b'\xca\xfe\xba\xbe'
    i = 10                                     # magic(4) minor(2) major(2) cp_count(2)
    count = int.from_bytes(b[8:10], 'big'); j = 1
    while j < count:
        tag = b[i]; i += 1
        if tag == 1: i += 2 + int.from_bytes(b[i:i+2], 'big')
        elif tag in (3,4,9,10,11,12,18): i += 4
        elif tag in (5,6): i += 8; j += 1
        elif tag in (7,8,16,19,20): i += 2
        elif tag == 15: i += 3
        else: raise ValueError(tag)
        j += 1
    return i
```

Cases (idx = patched class index in the binding order):

| base class | OR bits | expected post-change |
|---|---|---|
| plain class (reachable from root) | 0x2000 | `LinkError(5, idx)` |
| plain class | 0x8000 | `LinkError(5, idx)` |
| plain class | 0x2000\|0x4000 (0x6000) | `LinkError(5, idx)`  ← catches the leaking form |
| plain class | 0x8000\|0x4000 (0xC000) | `LinkError(5, idx)` |
| plain class | 0x4000 only | admitted; terminal must be the ordinary-class path, proving E is the *only* newly admitted bit |
| interface class (implemented by root) | 0x4000 (0x4601) | `InterfaceError(1, idx)` |
| interface class | 0x2000 (0x2601) | `InterfaceError(1, idx)` |

Repack each patched class into the same zip layout (`ZipInfo(name, (1980,1,1,0,0,0))`,
deflate) and keep the `MC_ENTRY_BINDINGS` entry list identical to the fixture receipt,
exactly as `classcount29-preflight/tools/generate_fixtures.py` + `generated_gate.py`
already do. Assert selector/words and `rootUnchanged` on refusal.

### 4.3 Retained annotation/interface gate

- Normal interface implemented and invoked by the root: must still succeed with the same
  `machineRoot` / opaque payload as the pre-change classcount gate (the change only
  affects a class that previously hard-failed, so every previously-successful fixture
  must be byte-identical).
- Real Java-8 `@interface` control *and* the guaranteed-reachable interface+0x2000 patch
  of 4.2: must still terminate with `InterfaceError(1, idx)`.
- Re-run the existing generated classcount gate (`28`, `29`, `q1`, `q7`, `direct`,
  `reopen`, `reordered`, canonical equality) and assert unchanged machine/opaque roots,
  counters and limits.

### 4.4 Unchanged limits / boundaries

Re-assert, via the existing generated gate: engine `MAX_RAW_CLASSES = 29`,
`MAX_RAW_BYTES = 262144`, aggregate byte frontier `262144` refusable and `262145`
constructor refusal (`0xab23ed08` words `[12]`), generated 30-class refusal
(engine `0x427cfac5` `[1,30]`), bootstrap image count and hashes unchanged (the embedded
`hex` blobs must be byte-identical), `rawLimits == [29, 262144]` in the pins. The enum
change must not move runtime/deployed size outside the local cap, and if the engine hash
changes that new hash must be re-pinned everywhere (engine pin, coordinator
`ENGINE_CODEHASH`, driver constants) as one reviewed delta.

## 5. `original30` is an observation, not a prediction

- The measured data localizes exactly one refusal and does not bound what happens next.
  The next failure after admission is expected to be in hierarchy/initialization and
  could surface from a different class or `<clinit>` path than the generated fixture;
  do not encode any "next class" name, success, or Done claim from this review.
- The parent's `original30` run is a one-shot observation of whatever the next genuine
  blocker is. Acceptance must record the actual selector/words, and must not pre-commit
  to `HierarchyError`, a missing-class diagnostic, or a specific class name.
- **Cap coupling.** `original29` already occupies all 29 slots (engine guard at archived
  lines 584/709, coordinator `decoders[29]` + `n > 29`, driver `len(Decoders) > 29`).
  Appending a 30th raw class therefore requires a *separate* cap-30 widening that the
  `LinkError(5,28)` measurement does not authorize. The enum step authorizes the parser
  policy at cap 29 only; the cap-30 delta must be gated independently, with its own
  boundary and canonical checks.
- **Parallel policy.** The identical `0xe000` policy exists in the tracked
  `jvmevm/runtime/JVMSubsetInterpreter.sol:483` (the M5d-a profile, not the MC engine).
  The MC engine is a standalone staged `.sol` (not generated from that file). Decide
  explicitly: default is to leave the tracked M5d-a profile untouched; changing it would
  require re-pinning the M5d-a runtime hash and rerunning the `java-*` gates, which is
  out of scope for this authorization.

## 6. Residual uncertainty

1. `javap` cannot prove absence of A/M bits; the raw-flag precondition in §1 is required.
2. Reachability of the flagged class is not enforced by the policy; tests must force it.
3. `ACC_ENUM` alone is a marker permission; it does not imply the class will link,
   initialize or run, and this review makes no such claim.
4. `original30` cannot be run at cap 29 without the separate cap-30 delta; its next
   blocker is unknown by construction.
