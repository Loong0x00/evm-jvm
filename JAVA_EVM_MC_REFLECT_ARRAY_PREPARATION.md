# P53 frozen scope — measured one-dimensional reference Array.newInstance

P52 independently accepted commit98ca72b9853aa6d02d028c730c9f9f907ebf17bb. Exact original ew.b(Class,int) PC2 invokes `java/lang/reflect/Array.newInstance(Class,int):Object`; successful authenticated checkpoint holds canonical mirror8273 for java.lang.Iterable and length0. The diagnostic is evidence only, never execution input. Original new ew$b object remains uninitialized during argument preparation.

Ordinary anewarray uses a constant-pool class, so arbitrary runtime component mirrors cannot be implemented truthfully as a hostless Java-only wrapper. P53 may add ONE versioned Solidity-JVM native binding22 behind Java8's ordinary public wrapper and private static native `newArray(Class,int)`. This is an explicit semantic inventory extension (21 old bindings retained), NOT a resource-quota/gas/consensus relaxation or host native/precompile. String-local12 and all resource bounds remain unchanged. P52/archive baseline remains21.

## Admitted subset

- Bootstrap-owned `java.lang.reflect.Array` minimal public final utility, private constructor, ordinary Java8 public static `newInstance(Class<?>,int)` forwarding to exact private static native `newArray(Class<?>,int)`. Native flags/arity/descriptor must be exact, raw owner replacement forbidden.
- Only canonical VM-owned mirrors of ordinary non-array reference classes/interfaces in the authenticated Program; any supported nonnegative length within existing anewarray admission/quotas. This is NOT zero-only or original-class-special-cased. Allocate a new real eager array, preserve exact component identity/rank/null cells/aliasing/astore checks/clone/checkpoint semantics.
- Null component -> genuine NPE before negative-length handling; valid supported component with negative length -> genuine NegativeArraySizeException. Reuse exact existing Java fault/quota/rollback machinery; no invented capacity or Java error.
- Allocate no component objects, invoke no constructor, and DO NOT initialize the component class. Canonical mirror/type/loader identity is checked by existing mirror machinery, not caller names, raw forged metadata or host Class lookup.
- Primitive/void mirrors, array-valued component mirrors, multidimensional overload, getLength/get/set/accessors and other reflection remain valid-outside-subset raw refusals. Do not fabricate component-correct results for them.

## Fixed boundaries

All116 existing image bytes/order unchanged; append only Array image116 ->117. Existing native1..21 behavior, String-local1..12, bytecode semantics, array codec and capacities stay unchanged. All9 engine/4 coordinator domains and actual engine hash updated. Tail parser105..109 preserved: count-12..-8 at newcount117. Raw150+117=267 is not coordinator uint8 raw150; no index/schema/storage/ABI widening.

Arrays8192, objects4096, elements262144, handles12545, raw150/1063930B, CP2MiB, artifact1MiB, frames128, q65536/internal4096, reserve25M. Underlying geth core/vm/core/state/params must match95665d570; LOCAL SetCode ordinary Call only, no CREATE/chain deployability claim.

## Required evidence

Worker source-only isolation, one guest-semantic writer and one heavy compiler/EVM process at a time. Test generated-only stock Java8 oracle (never execution input). Fresh EVM: Object/String/interface/private and uninitialized-component classes, zero/nonzero independent dense arrays, real cells/aliases/exact casts/ASE/clone, NPE/negative precedence, existing quota outcomes and atomic unsupported overload/raw owner/forged mirror rejection. Exact signature/flags/return stack, real array/root/counter/heap equality q1/q7/coarse and separate-process reopen. Retain old mirror/Class/EnumSet/arraycopy and all-bootstrap assembly probes. Report inventory22 explicitly, no hidden native alias.

Initial generated1B/30s; finite coherent doubling only after measured shortages, with failures preserved; outer1200s is separate. Original uint64.max/60s remains a separately authorized driver. Fresh original131 start after independent parent build/gates; never continue P52 CP across code/package. No original host Java/ZIP/class parser, payload rewriting/injection/oracle input, failed-state continuation or fabricated Done.
