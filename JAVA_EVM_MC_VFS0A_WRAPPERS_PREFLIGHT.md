# VFS0a Java-wrapper pins preflight

Status: **candidate evidence only, not an implementation freeze or acceptance**. Based on
`b5f2c5b` and accepted IOE0 runtime 233286B/SHA256
`507ed54d56d4cbe5e559013fbf5a3e598d75a28c0ffe33735573f646eac659a0`.
This document owns only Java-wrapper evidence. It does not implement the EVM VFS,
change any accepted image/artifact/budget, execute Minecraft/JAR/EULA code, open a
listener, or establish startup/readiness. All new pins remain parent-reviewable.

## Candidate eight-image set

Sources and classes are in ignored
`build/java-diff-mc-vfs0a-wrappers/{bootstrap-src,bootstrap-classes}/`. Compile all
sources together, in sorted path order, with OpenJDK `javac 1.8.0_504`:

```text
_JAVA_OPTIONS='-Xmx512m -XX:MaxMetaspaceSize=256m' \
  javac -source 8 -target 8 -g:none -d bootstrap-classes <eight sorted sources>
```

| image | bytes | source SHA256 | class SHA256 |
|---|---:|---|---|
| java/lang/AutoCloseable |145|3520639a2c4c5e9c43b1cd6dc6ea269058d787d436be4dbeac38a1323fbe8d08|cafa160ddd47f90df802399cbd3ea0f4a62dc0d382c77fde7917b8b84fa51ea8|
| java/io/Closeable |170|c00f4d65711c584a549245e5e56bcefcdff748fab8c616602cdd249431128a28|79fae4d62aee6a6f46bd7483265bb3a19ba9fcc89c3f6dc8a14d5814a10ed86f|
| java/io/Flushable |139|38590df5c917ae27beb7e264449a6ce617950ef8a28e648cf15f0428798cbff1|b5679864201f2fe3eb8e7fad6a7121790281ad1ca87391d928ca9c1bc9277513|
| java/io/File |965|f8734eb6a963342b76ad47097dae489285c30d9b62c5928d75100e7372a4cc78|10bbaa2a0173f55a03514ec03c9e5cd26f7a7ac53c1e9ec9d9a5c7df382c2c20|
| java/io/InputStream |345|5b320b38efca9955c0cfb4062333dd558d8f11b4f5371405143f15cecda9985b|d7f89988eac8708f8efd6939430477d738f82652e24e98c2c677ba5ff30c7578|
| java/io/OutputStream |455|08c300f2e6d0a7c6bd2aba4dba982b90a81e941894c7f7429fb5f13322263c23|d0b420e13fcaaff169a4b695187667f48005870879f573ff6421aa7cb016bc57|
| java/io/FileInputStream |1478|dfe7fdd545d48c5fdacaa57985e3a5a839ebfe6ea929adc9338dbe3c7e34d78b|68fd8bf1cdb48a5309b60a28ec9573dd68b5cc96318487b82f93cfce058e4545|
| java/io/FileOutputStream |1581|18d546ad0458c82df99aa2762171e76fff7ed6f287277a7b98123ea8e77e7768|4e5175528984798d6da3ef9c3cd58395e0f66788be9e11ed1a2a35fb2015f6a8|

The images total 5,278 bytes. This is not an additive whole-runtime estimate and does
not prove fit in IOE0's 28,858-byte headroom or the candidate 256KiB ceiling.

## Graph, fields and exact Java/native surface

Graph: `AutoCloseable`; `Closeable extends AutoCloseable`; `Flushable`;
`File extends Object implements Serializable`; `InputStream extends Object implements
Closeable`; `OutputStream extends Object implements Closeable,Flushable`;
`FileInputStream extends InputStream`; `FileOutputStream extends OutputStream`.
`Serializable`, Object, String, NPE, IOOBE, IOE and FNFE are the unchanged accepted
IOE0/SC0 identities. File deliberately omits Comparable in this bounded candidate;
comparison and all other omitted APIs retain normal link/call failure.

Fields are exactly `File.private final path:String`, `FIS.private handle:I`, and
`FOS.private handle:I`; the other five images have none. `File.final path0()String`
is package-private ordinary Code solely for the two pinned wrappers' message loops.
There are no descriptor/message side fields.

Abstract/no-Code signatures are `AutoCloseable.close()V throws Exception`,
`Closeable.close()V throws IOException`, `Flushable.flush()V throws IOException`;
InputStream `read()I`, `read([BII)I`, `close()V`; OutputStream `write(I)V`,
`write([BII)V`, `close()V`. Protected Input/Output constructors and these concrete
public methods have ordinary Code: Input `read([B)I`; Output `write([B)V` and
`flush()V`; File constructor plus `exists/isFile/isDirectory/mkdir/mkdirs`; FIS
constructor plus all three reads/close; FOS both File constructors plus all three
writes/close. Each FIS/FOS also has private static ordinary-Code
`errorMessage(File,I)String`. No public method is native.

Private native signatures, all instance methods invoked with Java8 `invokespecial`:

```text
File.stat0()I                 File.mkdir0(Z)I
FIS.open0(File)I              FIS.readOne0()I
FIS.read0([BII)I              FIS.close0()I
FOS.open0(File,Z)I            FOS.writeOne0(I)I
FOS.write0([BII)I             FOS.close0()I
OutputStream.unsupported0()V  // flush hard-profile hook; must never return
```

Bind only the exact reserved class hash, declaring owner, private/native flags,
name, descriptor, nonstatic mode and `invokespecial`. A lookalike, replacement,
wrong descriptor/access/staticness or other invocation follows ordinary link/call
failure. `unsupported0` must hard-fail the deferred flush profile: flush is neither
implemented nor a no-op. Other deferred constructors/methods are absent and may
hard-fail normally; no deferred I/O operation silently succeeds.

## Status and ordinary-wrapper rules

Only these returns may reach Java Code: stat `0 missing,1 file,2 directory`; mkdir
`0 false,1 created`; open `positive descriptor,-1 missing,-2 directory`, plus FOS
`-3 denied`; read-one `0..255,-1 EOF,-2 closed`; nonzero bulk read
`1..requested,-1 EOF,-2 closed`; writes `0 success,-2 closed`; close `0`, including
repeat close. Constructor null File is checked before open. After EVM path-profile
validation/resolution, missing input or output parent maps `-1`; an existing directory
maps `-2` before writable-file checks; FOS read-only regular target/ancestor maps `-3`.
FIS must permit read-only input and may not return denied. Out-of-domain status,
transfer >4096, unsupported mode/path or quota is an EVM hard profile/quota error
before return, never an invented Java outcome. Single write stores low 8 bits.

Public Code maps open failure to real `new FileNotFoundException(String)`, closed
nonzero transfer to real `new IOException("Stream Closed")`, and otherwise returns
EOF/count/boolean or normally returns. It uses accepted IOE0 constructors and SC0
String operations. Native code never creates a Java object/String/Throwable, supplies
message bytes, invokes host logic, or emits an exception ABI payload.

For bulk calls, wrapper `arraylength` gives null-before-bounds-before-closed order;
`offset<0 || length<0 || offset>arraylength-length` is overflow-safe. Bounds are
checked before `length==0`; valid zero length returns 0/no-op before any native call,
even closed. Accepted NPE/IOOBE allocation and unwind remain genuine. Receiver NEW
and super Code necessarily precede constructor argument checks: exhausted ordinary
heap can therefore OOM before a null File/path check; after receiver allocation, NPE
or explicit IOOBE/IOE allocation can itself become accepted emergency OOM. Null bulk
array faults use the existing implicit-fault/arena policy. None of those null,
bounds or valid-zero cases calls native I/O. For nonzero valid slices, the native
4096-byte hard limit precedes descriptor/closed lookup; only then may `-2` reach Code.
A failed open has no inode/descriptor/content effect before message work, so OOM in
char-array, String or FNFE construction remains genuine OOM and leaks no descriptor.

## Path and deterministic messages

`File(String)` executes Object Code, dereferences the argument, collapses consecutive
`/`, and drops a trailing `/` except the sole root. It then copies the exact result
into `char[]` and executes genuine `new String(char[])`; null is a genuine NPE and
normalization allocations can genuinely OOM before `path` is stored. Examples are
`missing//child/ -> missing/child`, `/// -> /`, and `a///b// -> a/b`.
It does not remove `.`/`..`, prepend `/work`, validate ASCII or resolve the VFS; those
are separate EVM operation rules. FNFE prefix comes from this normalized field.

The wrapper chooses an explicit deterministic English C/POSIX-style VFS profile:
`" (No such file or directory)"`, `" (Is a directory)"`, and
`" (Permission denied)"`. Ordinary char-array loops copy normalized path then suffix
and execute SC0 `String(char[])` and IOE0 `FNFE(String)` Code. This deliberately does
not claim host-default-locale behavior or general errno localization.

## Construction and pending bind decision

Choose the explicit **no-callback NEW File/stream-family profile**, rather than
claiming arbitrary escaped default states. For NEW whose dynamic class is File or a
subtype of File/InputStream/OutputStream, require the exact canonical no-callback
Object `()V` Code shape. The Object frame still executes; it is not skipped. Scope
this guard only to those NEW families: String keeps SC0's String-only guard, and all
unrelated IOE0 Throwable/exception objects and constructor behavior remain unchanged.

Normal active constructor states remain real. File may have null path while its
normalization frame is active. FIS/FOS open allocates the descriptor (and FOS may
create/truncate) before Java stores `handle`. Preserve that pending-bind gap across
checkpoints without reopening. In the pinned Code, FIS `open0` invoke PC18 has
pending next-PC corridor `21,22,23,26,27,28` and bind `putfield` PC28; FOS `(File,Z)`
invoke PC19 has corridor `22,23,24,27,28,29` and bind PC29. FOS `(File)` only delegates.

The runtime must derive these PCs anew from the pinned method's parsed Code and exact
`open0`/`handle:I putfield` instructions; serialized bindPC is only checked data, not
authority. At each corridor PC, require the exact constructor frame depth, local0
receiver, returned positive ID in its exact stack/local position, descriptor ownerRef,
and post-super phase. The putfield transition atomically makes it BOUND. Generic ints,
foreign constructors/fields or wrong stack shapes cannot satisfy pending ownership.
No host constructor execution or repair is allowed during validation/resume.

After a stream super-constructor returns, a user subclass can publish `this` and then
fail. Its positive handle and BOUND descriptor remain, reachable or unreachable;
there is no GC/finalizer/implicit close. Failures before successful open have no
native effect and subclass Code has not started. File superclass completion likewise
leaves a normalized path. These effects and active UNINIT/REF states must be encoded,
not erased or replaced with fictitious successful default objects.

## Owned host oracles and limits

`WrapperOracle.java` (SHA256
`06862797ec5ff9ee372f2028f669c1a100355182da285be1d252fc898734aae4`)
used only stock host JDK classes in fresh owned working directories; it never replaced
host Object or executed candidate classes. Its 28 rows cover normalization, null,
bounds/closed/zero precedence, missing/directory/read-only messages, normal/append/
truncate I/O, EOF, repeated close, two writers, post-truncate stale read cursor and
zero-filled gap. Java8 primary and Java21 secondary agree byte-for-byte under C locale:
output SHA256 `1a627ac40b12ed772b18515c4e6fa843a74793b147f4165ef987fa8373d998cc`.
Both default-locale outputs instead use Chinese native suffixes and agree at SHA256
`20536e3d74b2614236b6068ffbf451f20a59eda96e1e4bde84229c564f94c863`.
The C rows include normalized `missing/child (No such file or directory)`, read-only
input=11, output Permission denied, stale read=-1 and final bytes `0,0,0,68`.

`reproduce.sh` runs three compiler and four JVM calls through `limited_run.py`, each
with a 30s timeout, 4GiB RLIMIT_AS, 512MiB heap and 256MiB metaspace, under an outer
1200s bound. All seven exited 0; whole replay took 2s. Observed maximum RSS was
66,540KiB (Java8 candidate compiler), 59,076/115,556KiB (oracle compilers), and
23,660/26,152/40,388/45,140KiB (four JVMs). These are machine observations, not
universal guarantees. No EVM call, integrated runtime-size/gas/checkpoint measurement,
VFS implementation, production freeze or readiness claim follows.
