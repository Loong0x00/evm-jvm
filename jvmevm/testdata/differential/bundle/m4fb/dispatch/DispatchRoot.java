package bundle.m4fb.dispatch;

/** Repeated calls deliberately share one b9 or b6 constant-pool call site. */
public class DispatchRoot {
    private static int interfaceSite(DispatchFace receiver, int value) { return receiver.run(value); }
    private static int classSite(DispatchBase receiver, int value) { return receiver.run(value); }
    private static int parentSite(DispatchParent receiver, int value) { return receiver.run(value); }

    public static int b9InheritedThenOverride(int value) {
        return interfaceSite(new DispatchBase(), value) * 100 + interfaceSite(new DispatchOverride(), value);
    }
    public static int b9OverrideThenInherited(int value) {
        return interfaceSite(new DispatchOverride(), value) * 100 + interfaceSite(new DispatchBase(), value);
    }
    public static int b9MostSpecificThenClass(int value) {
        return interfaceSite(new DispatchSpecific(), value) * 100 + interfaceSite(new DispatchOverride(), value);
    }
    public static int b9ThreeReceivers(int value) {
        return interfaceSite(new DispatchBase(), value) * 10000
            + interfaceSite(new DispatchSpecific(), value) * 100
            + interfaceSite(new DispatchOverride(), value);
    }
    public static int b9SameReceiverTwice(int value) {
        DispatchFace receiver = new DispatchSpecific();
        return interfaceSite(receiver, value) * 100 + interfaceSite(receiver, value + 1);
    }
    public static int b9DiamondAndSpecific(int value) {
        return interfaceSite(new DispatchDiamond(), value) * 100 + interfaceSite(new DispatchSpecific(), value);
    }
    public static int b6InheritedThenOverride(int value) {
        return classSite(new DispatchBase(), value) * 100 + classSite(new DispatchOverride(), value);
    }
    public static int b6OverrideThenInherited(int value) {
        return classSite(new DispatchOverride(), value) * 100 + classSite(new DispatchBase(), value);
    }
    public static int b6SpecificThenOverride(int value) {
        return classSite(new DispatchSpecific(), value) * 100 + classSite(new DispatchOverride(), value);
    }
    public static int b6ThreeReceivers(int value) {
        return classSite(new DispatchBase(), value) * 10000
            + classSite(new DispatchSpecific(), value) * 100
            + classSite(new DispatchOverride(), value);
    }
    public static int parentOwnerSpecific(int value) { return parentSite(new DispatchSpecific(), value); }
    public static int parentOwnerDiamond(int value) { return parentSite(new DispatchDiamond(), value); }
    public static int subclassInheritsDefault(int value) { return classSite(new DispatchChild(), value); }
    public static int subclassInheritsOverride(int value) { return classSite(new DispatchOverrideChild(), value); }
    public static int sameSiteSigns(int value) {
        return interfaceSite(new DispatchBase(), value) + interfaceSite(new DispatchOverride(), -value);
    }
    public static int sameSiteOverflow(int value) {
        return interfaceSite(new DispatchSpecific(), value) * 100000001 + interfaceSite(new DispatchBase(), value);
    }
}

interface DispatchFace { default int run(int value) { return value + 1; } }
interface DispatchParent extends DispatchFace {}
interface DispatchLeft extends DispatchParent {}
interface DispatchRight extends DispatchParent {}
interface DispatchDiamondFace extends DispatchLeft, DispatchRight {}
interface DispatchMoreSpecific extends DispatchParent { default int run(int value) { return value + 2; } }
class DispatchBase implements DispatchFace {}
class DispatchChild extends DispatchBase {}
class DispatchOverride extends DispatchBase { public int run(int value) { return value + 3; } }
class DispatchOverrideChild extends DispatchOverride {}
class DispatchSpecific extends DispatchBase implements DispatchMoreSpecific {}
class DispatchDiamond extends DispatchBase implements DispatchDiamondFace {}
