# System ClassLoader getter preflight

Scoped LOCAL Minecraft startup COPY from parent basis `6d6b8ea0e` /
`MC-CLASS-DEFINING-LOADER-PARENT1`. The sole proposed semantic addition is
`java.lang.ClassLoader.getSystemClassLoader()Ljava/lang/ClassLoader;`, a public
static native zero-argument getter. It must return the already-existing,
validated concrete `VMClassLoader` that raw `Class` mirrors use. It neither
installs nor creates a loader.

The getter is limited to exact ClassLoader/name/descriptor metadata. Existing
native bindings 1--4 (Float/Double) and 5 (`System.arraycopy`) retain their
existing behavior. Active-use initialization and normal operand-stack capacity
remain in the static invocation path. Missing, duplicate, malformed, or
wrong-state canonical-loader state fails with `LC0StateError`; no resource or
class-loading API is added.

This is an unaccepted LOCAL experiment. It is not a JVM, resource lookup, or
Minecraft readiness/Done claim. The initial compile is measured against the
unchanged 320 KiB cap; only a preserved actual 320 KiB cap failure permits a
separately labeled LOCAL384 KiB build. Other existing LOCAL limits remain
unchanged.
