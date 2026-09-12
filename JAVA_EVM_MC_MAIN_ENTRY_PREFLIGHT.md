# Generated Java8 `main(String[])` launch / link-frontier preflight

Status: **measured generated-only preflight; not accepted production work.** Base
`0fdb9dcf7` CB0 remains unchanged and accepted. This document and
`evidence/java-evm/main-entry/preflight/` are the only changes in this task.

## Question and method

Before proposing any root ABI, test whether the accepted fixed CB0 root can run
an extra guest launcher `public static int run(int mode)` that makes a true guest
`String[]` and invokes a second generated class's public static
`void main(String[])`. The root remains the accepted int-argument/int-result
entry; the generated launcher, not Go, makes arrays and calls the void method.

The exact generated Java8 sources, Java8u504 oracle, deterministic ZIP builder,
public-API Go driver, strict verifier, refusal, output hashes, report, and clean
20-minute/4-GiB sampled watchdog are durable evidence at
`evidence/java-evm/main-entry/preflight/`. The fixture is only `Launcher` and
`TargetMain`, compiled `-source 8 -target 8 -g:none`; it contains no official
JAR/server class or other copyrighted payload.

The driver uses public `cb0.New/Open/Initialization/Head`, AS0/ZI0/DI0 mutation
methods, `CreateCoordinator`, `Start`, `Resume`, and `ReadCheckpoint` only. It
passes the entire opaque ZIP to AS0, has no ZIP/class parser/inflater/catalogue
or raw-class Java input, constructs known-name package assertions from actual
EVM Head metadata with frozen CB0 domains/pins, and leaves FINAL DI0 page reads
and all class assembly to EVM. It uses no reflection, unsafe/private Session
access, StateDB mutation or SetCode.

## Actual result

This fixed two-class package succeeds:

* empty array → 341 in 24 Java/4 internal steps;
* ASCII `{"ASCII", "arg"}` → 381 in 54/4;
* Unicode `{"λ", "☃"}` → 351 in 57/4;
* `TargetMain.main(null)` → terminal ordinary guest canonical kind 6
  `NullPointerException`, 22/5, rather than an EVM failure.

`TargetMain` static initialization sets observable `state=11`, and `Launcher`
returns state only after the `void main` call. Independent Java8 oracle results
match. Mode 1 direct/q1/q7 take 1/54/8 slices and have equal final machine, VFS,
AS0, ZI0, FINAL DI0 resource and frozen-domain package roots. q1 used 54 distinct
Start/Resume processes plus a separate terminal-reopen process; each reopening
asserted no engine installation and every terminal checkpoint was EVM-Keccak and
SHA-256 checked.
Actual Java Start/Resume calls remain ordinary <=100M gas; no 1B boundary call.
The clean watchdog was exit0, 6.133s, 334929920B sampled group peak.

## Limits and next dependency

This does not make the root ABI a direct `void main(String[])` ABI and does not
solve fixed <=4 images/<=65536 package capacity, target-JAR discovery,
transitive/dynamic class loading, class caps, or logging/platform APIs. A future
unchanged target JAR could be invoked by a generated launcher only after a
separate bounded generated transitive/link-loading preflight. It is not an
original Java/Minecraft instruction, EULA, listener, world or Done claim, and it
changes no engine, CB0/profile/quota/artifact/source.
