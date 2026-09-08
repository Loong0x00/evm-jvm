package bundle.m4fb.bridges;

/** Covariant class bridges and javac-generated concrete interface bridges. */
public class BridgeRoot {
    private static Object classSite(BridgeClassBase receiver, int value) { return receiver.make(value); }
    private static Object interfaceSite(BridgeCovariant receiver, int value) { return receiver.make(value); }
    private static <T> T genericSite(BridgeGeneric<T> receiver, T value) { return receiver.identity(value); }

    public static int classCovariantBridge(int value) { return ((BridgeToken) classSite(new BridgeClassChild(), value)).value; }
    public static int classCovariantInherited(int value) { return ((BridgeToken) classSite(new BridgeClassGrandchild(), value)).value; }
    public static int classBridgePolymorphic(int value) {
        return ((BridgeToken) classSite(new BridgeClassBase(), value)).value * 100
            + ((BridgeToken) classSite(new BridgeClassChild(), value)).value;
    }
    public static int interfaceCovariantBridge(int value) { return ((BridgeToken) interfaceSite(new BridgeDefaultImpl(), value)).value; }
    public static int interfaceCovariantInherited(int value) { return ((BridgeToken) interfaceSite(new BridgeDefaultChild(), value)).value; }
    public static int interfaceBridgePolymorphic(int value) {
        return ((BridgeToken) interfaceSite(new BridgeBaseImpl(), value)).value * 100
            + ((BridgeToken) interfaceSite(new BridgeDefaultImpl(), value)).value;
    }
    public static int genericDefaultIdentity(int value) {
        BridgeToken token = new BridgeToken(value); return genericSite(new BridgeGenericImpl(), token) == token ? value : -1;
    }
    public static int genericOverrideBridge(int value) {
        BridgeToken token = new BridgeToken(value); return ((BridgeToken) genericSite(new BridgeGenericOverride(), token)).value;
    }
    public static int genericBridgePolymorphic(int value) {
        BridgeToken token = new BridgeToken(value);
        return ((BridgeToken) genericSite(new BridgeGenericImpl(), token)).value * 100
            + ((BridgeToken) genericSite(new BridgeGenericOverride(), token)).value;
    }
    public static int abstractSourceBridgeDispatch(int value) {
        BridgeAbstractSource receiver = new BridgeAbstractImpl(); return receiver.make().value + value;
    }
    public static int abstractSourceErasedDispatch(int value) {
        BridgeAbstractParent<?> receiver = new BridgeAbstractImpl(); return ((BridgeToken) receiver.make()).value + value;
    }
    public static int bridgeReferenceIdentity(int value) {
        BridgeToken token = new BridgeToken(value); BridgeGeneric<BridgeToken> receiver = new BridgeGenericImpl();
        return receiver.identity(token) == token ? value + 1 : -1;
    }
}

class BridgeToken { int value; BridgeToken(int value) { this.value = value; } }
class BridgeClassBase { public Object make(int value) { return new BridgeToken(value + 1); } }
class BridgeClassChild extends BridgeClassBase { public BridgeToken make(int value) { return new BridgeToken(value + 2); } }
class BridgeClassGrandchild extends BridgeClassChild {}
interface BridgeCovariant { default Object make(int value) { return new BridgeToken(value + 3); } }
interface BridgeCovariantChild extends BridgeCovariant {
    default BridgeToken make(int value) { return new BridgeToken(value + 4); }
}
class BridgeBaseImpl implements BridgeCovariant {}
class BridgeDefaultImpl implements BridgeCovariantChild {}
class BridgeDefaultChild extends BridgeDefaultImpl {}
interface BridgeGeneric<T> { default T identity(T value) { return value; } }
class BridgeGenericImpl implements BridgeGeneric<BridgeToken> {}
class BridgeGenericOverride implements BridgeGeneric<BridgeToken> {
    public BridgeToken identity(BridgeToken value) { return new BridgeToken(value.value + 5); }
}
interface BridgeAbstractParent<T> { T make(); }
interface BridgeAbstractSource extends BridgeAbstractParent<BridgeToken> { BridgeToken make(); }
class BridgeAbstractImpl implements BridgeAbstractSource { public BridgeToken make() { return new BridgeToken(6); } }
