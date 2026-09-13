# LOCAL Class defining-loader evidence

This source-only generated-fixture preflight derives from the committed
Thread-context source archive and never opens an original Minecraft JAR/class,
world, payload page, or LevelDB database. `gate.py` uses a fresh ignored
`build/java-diff-mc-class-defining-loader-*` directory and locally compiled
fixtures only.

The engine binds exactly one ordinary guest `java/lang/VMClassLoader` object to
all literal-created raw input mirrors. `java/lang/Class` carries ordinary
`name` and `definingLoader` fields; checkpoint validation reconstructs identity
by scanning heap objects. Bootstrap mirrors have a null loader. This does not
implement `ClassLoader` resource or loading APIs.
