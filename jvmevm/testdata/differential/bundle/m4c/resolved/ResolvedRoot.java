package bundle.m4c.resolved;

/** Resolved unusual declarations with ordinary concrete dynamically selected overrides. */
public class ResolvedRoot {
    private static int abstractAtSite(AbstractBase receiver, int value) {
        return receiver.apply(value);
    }

    private static int nativeAtSite(NativeBase receiver, int value) {
        return receiver.apply(value);
    }

    private static int synchronizedAtSite(SynchronizedBase receiver, int value) {
        return receiver.apply(value);
    }

    public static int resolvedAbstractOverride(int value) {
        return abstractAtSite(new AbstractChild(), value);
    }

    public static int resolvedAbstractGrandOverride(int value) {
        return abstractAtSite(new AbstractGrand(), value);
    }

    public static int resolvedNativeOverride(int value) {
        return nativeAtSite(new NativeChild(), value);
    }

    public static int resolvedNativeGrandInherited(int value) {
        return nativeAtSite(new NativeGrand(), value);
    }

    public static int resolvedSynchronizedOverride(int value) {
        return synchronizedAtSite(new SynchronizedChild(), value);
    }

    public static int resolvedSynchronizedGrandInherited(int value) {
        return synchronizedAtSite(new SynchronizedGrand(), value);
    }

    public static int nullResolvedAbstract(int value) {
        return abstractAtSite(null, value);
    }

    public static int nullResolvedNative(int value) {
        return nativeAtSite(null, value);
    }

    public static int nullResolvedSynchronized(int value) {
        return synchronizedAtSite(null, value);
    }
}

abstract class AbstractBase {
    abstract int apply(int value);
}

class AbstractChild extends AbstractBase {
    int apply(int value) { return value + 11; }
}

class AbstractGrand extends AbstractChild {
    int apply(int value) { return value + 111; }
}

class NativeBase {
    native int apply(int value);
}

class NativeChild extends NativeBase {
    int apply(int value) { return value + 22; }
}

class NativeGrand extends NativeChild {
}

class SynchronizedBase {
    synchronized int apply(int value) { return value + 3; }
}

class SynchronizedChild extends SynchronizedBase {
    int apply(int value) { return value + 33; }
}

class SynchronizedGrand extends SynchronizedChild {
}
