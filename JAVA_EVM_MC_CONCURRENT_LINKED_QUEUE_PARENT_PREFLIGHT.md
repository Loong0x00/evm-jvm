# Parent acceptance: bounded `ConcurrentLinkedQueue`

The parent independently accepts the measured LOCAL-only queue bootstrap subset. Worker
source commits `7a20245af`/`84be3fb19`/`0e1015624` and evidence `a52f12e54` were
integrated as `9607a2a51`/`7a77f144a`/`bdc6a1e6a`/`854030297`. Parent evidence is
`evidence/java-evm/minecraft-entry/parent-854030297/`.

Two Java8 images append after the accepted79-image tail: 121-byte `java/util/Queue`
SHA256 `1b45b0ad2a3908043584a5fcc7df2b9d3e2e46fb16c573809fdf553ab39d93f0`
and bounded `java/util/concurrent/ConcurrentLinkedQueue` SHA256
`412b445abf63e579a67b2b45bb7cba194ec6dd6320340c7f94af5da1e85d5c23`.
Strict stripped-Java8/reverse-source verification proves all79 prior images identical and
only domain, count79→81/73→75, append and reserved-name changes.

The queue uses ordinary EVM-owned `Object[]` fields. Non-null add and non-empty poll
publish copied FIFO arrays; duplicates are retained; empty poll returns null; null add
raises the existing guest NPE. Iterators reuse the accepted same-package immutable
snapshot iterator. No host/native queue, scheduler, lock or concurrent-progress semantics
exist, and broader Queue APIs remain absent.

Parent domain is `MC-CONCURRENT-LINKED-QUEUE-PARENT1`, engine address
`0x4d432d5145554555452d504152454e5400000001`. Independent solc0.8.30
optimizer200/viaIR/Cancun/metadata-off build produced388963 bytes, SHA256
`815193ba27cd60a152e55278c66ef5cf34f81f6d006f481fc50134776861710b`,
Keccak `34879656a9d14e6d938ab362b0ff12babfcad5a0438784329d7bc1abc884cb54`.
The4146-byte coordinator Keccak is
`cdbde4143dcbe7fab37e00b1b79dba1cd9e5f04c966d0dd130c0b9bc74434285`.
Build took231.60s and peaked at1001463808 bytes group RSS, under LOCAL384.
Raw26/262144, exception14, native11/String-local10 and all safety/accounting limits are
unchanged; diagnostic max class count is107.

Fresh Java8 host and guest q1/q7/direct/reopen/canonical gates pass FIFO, duplicates,
empty/null behavior, size/isEmpty, snapshot isolation/exhaustion and retained locks. A
parent array-count quota gate reaches1024 arrays and proves a non-null add raises catchable
OOM kind7 while queue size remains zero; q1/q7/direct converge with a53709-byte
checkpoint. Raw Queue/ConcurrentLinkedQueue replacement refuses atomically.

A fresh unchanged original26 world uses the pinned JAR SHA256
`fe1f9274e6dad9191bf6e6e8e36ee6ebc737f373603df0946aafcded0d53167e`
and the same26-class/229450-byte package. q7 reaches epoch560/3920 Java/33 internal
steps; q1 immediately reproduces the next refusal. All560 successful receipts verify
canonically. The genuine BoundedQueue and queue superclass constructors execute, their
backing fields publish, `StatusLogger.messages` and `msgLock` are stored, and execution
reaches PC55.

The next measured blocker is same-JAR `org/apache/logging/log4j/simple/SimpleLogger.class`
(10086 bytes, SHA256
`b296921a9bd51352289fcd7950d7816eb3e480bbc2e41c9373dd00e776c88e62`). A raw27
package would total239536 bytes, under262144 and already count-authorized. q7/q1 failed
calls preserve trie/head. No Minecraft main body, world creation or `Done` is claimed.
