package bundle.m4fa.bridges;

/** javac-generated public bridge methods live on classes, never as interface default bridges. */
public class BridgeRoot {
    private static int makeAtSite(BridgeFactory<BridgeToken> factory, int value) {
        return factory.make(value).value;
    }

    private static int readAtSite(BridgeFactory<BridgeToken> factory, BridgeToken token) {
        return factory.read(token);
    }

    private static Object covariantAtSite(CovariantBase receiver, int value) {
        return receiver.make(value);
    }

    public static int genericBridgeReturn(int value) {
        return makeAtSite(new BridgeImpl(), value);
    }

    public static int genericBridgeArgument(int value) {
        return readAtSite(new BridgeImpl(), new BridgeToken(value));
    }

    public static int genericBridgeAlternating(int value) {
        return makeAtSite(new BridgeImpl(), value) * 100 + makeAtSite(new BridgeOther(), value);
    }

    public static int genericArgumentAlternating(int value) {
        BridgeToken token = new BridgeToken(value);
        return readAtSite(new BridgeImpl(), token) * 100 + readAtSite(new BridgeOther(), token);
    }

    public static int classCovariantBridge(int value) {
        Object result = covariantAtSite(new CovariantChild(), value);
        return ((BridgeToken) result).value;
    }

    public static int classCovariantGrandchild(int value) {
        Object result = covariantAtSite(new CovariantGrandchild(), value);
        return ((BridgeToken) result).value;
    }

    public static int classCovariantAlternating(int value) {
        Object first = covariantAtSite(new CovariantBase(), value);
        Object second = covariantAtSite(new CovariantChild(), value);
        return ((BridgeToken) first).value * 100 + ((BridgeToken) second).value;
    }

    public static int bridgeReferenceIdentity(int value) {
        BridgeFactory<BridgeToken> factory = new BridgeImpl();
        BridgeToken token = new BridgeToken(value);
        return factory.identity(token) == token ? value : -1;
    }
}

interface BridgeFactory<T> {
    T make(int value);
    int read(T value);
    T identity(T value);
}

class BridgeToken {
    int value;
    BridgeToken(int value) { this.value = value; }
}

class BridgeImpl implements BridgeFactory<BridgeToken> {
    public BridgeToken make(int value) { return new BridgeToken(value + 10); }
    public int read(BridgeToken token) { return token.value + 11; }
    public BridgeToken identity(BridgeToken token) { return token; }
}

class BridgeOther implements BridgeFactory<BridgeToken> {
    public BridgeToken make(int value) { return new BridgeToken(value + 20); }
    public int read(BridgeToken token) { return token.value + 22; }
    public BridgeToken identity(BridgeToken token) { return token; }
}

class CovariantBase {
    public Object make(int value) { return new BridgeToken(value + 30); }
}

class CovariantChild extends CovariantBase {
    public BridgeToken make(int value) { return new BridgeToken(value + 40); }
}

class CovariantGrandchild extends CovariantChild {
}
