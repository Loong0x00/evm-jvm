# ClassLoader.loadClass preflight

Bounded LOCAL preflight from `cb35a61f7`. This sole-writer candidate replaces only the
existing `java/lang/ClassLoader` bootstrap image (index 49), retaining 66 images and
native bindings 1--7. Binding 8 is the exact private static `loadClass0(String)Class`
primitive used by public instance `loadClass(String)Class`.

It resolves a valid guest String name only against immutable parsed Program classes,
returns the existing canonical `Class` mirror without initialization, and preserves
raw VM defining-loader vs bootstrap null-loader identity. Missing/malformed names
remain explicit profile refusals; this does not add `Class.forName` or change Thread
context defaults. Generated fixtures and durable receipts will be archived here.
