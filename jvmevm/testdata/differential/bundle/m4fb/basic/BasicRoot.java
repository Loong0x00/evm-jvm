package bundle.m4fb.basic;

/** Source-level defaults with only int/reference/void profiles already supported by the guest. */
public class BasicRoot {
    private static int viaBasic(BasicFace receiver, int value) { return receiver.value(value); }
    private static int viaParent(BasicParent receiver, int value) { return receiver.value(value); }

    public static int directInterface(int value) { return viaBasic(new BasicImpl(), value); }
    public static int directClass(int value) { return new BasicImpl().value(value); }
    public static int inheritedDefault(int value) { return viaBasic(new BasicInherited(), value); }
    public static int childMostSpecific(int value) { return viaBasic(new BasicChildImpl(), value); }
    public static int childSymbolicOwner(int value) { return new BasicChildImpl().value(value); }
    public static int parentSymbolicMostSpecific(int value) { return viaParent(new BasicChildImpl(), value); }
    public static int diamondSharedDefault(int value) { return viaParent(new BasicDiamond(), value); }
    public static int diamondLeafDefault(int value) { return viaParent(new BasicLeafImpl(), value); }
    public static int classWinsInterfaceSite(int value) { return viaBasic(new BasicClassWins(), value); }
    public static int classWinsClassSite(int value) { return new BasicClassWins().value(value); }
    public static int superclassWins(int value) { return viaBasic(new BasicClassChild(), value); }
    public static int finalClassWins(int value) { return viaBasic(new BasicFinalWins(), value); }
    public static int twoIntArguments(int value) { return new BasicImpl().combine(value, value + 2); }
    public static int zeroIntArguments(int value) { return new BasicImpl().constant() + value; }
    public static int defaultCallsDefault(int value) { return new BasicImpl().twice(value); }
    public static int voidDefault(int value) {
        BasicBox box = new BasicBox(value);
        new BasicImpl().adjust(box, 3);
        return box.value;
    }
    public static int referenceIdentity(int value) {
        BasicBox box = new BasicBox(value);
        return new BasicImpl().identity(box) == box ? box.value : -1;
    }
    public static int referenceReturn(int value) { return new BasicImpl().make(value).value; }
    public static int objectRoundTrip(int value) {
        Object token = new BasicImpl().asObject(new BasicBox(value));
        return ((BasicBox) token).value;
    }
    public static int recursiveDefault(int value) { return new BasicImpl().sumDown(value); }
    public static int recursiveThroughInterface(int value) { return viaRecursive(new BasicImpl(), value); }
    private static int viaRecursive(BasicFace receiver, int value) { return receiver.sumDown(value); }
    public static int negativeRecursiveBase(int value) { return new BasicImpl().sumDown(value); }
    public static int defaultArrayArgument(int value) {
        int[] values = new int[2]; values[0] = value; values[1] = value + 1;
        return new BasicImpl().sumArray(values);
    }
    public static int defaultReferenceArray(int value) {
        BasicBox[] values = new BasicBox[2]; values[0] = new BasicBox(value); values[1] = new BasicBox(value + 2);
        return new BasicImpl().sumBoxes(values);
    }
}

interface BasicFace {
    default int value(int value) { return value + 10; }
    default int combine(int first, int second) { return first * 10 + second; }
    default int constant() { return 7; }
    default int twice(int value) { return value(value) + value(value + 1); }
    default void adjust(BasicBox box, int delta) { box.value = box.value + delta; }
    default BasicBox identity(BasicBox box) { return box; }
    default BasicBox make(int value) { return new BasicBox(value + 20); }
    default Object asObject(BasicBox box) { return box; }
    default int sumDown(int value) { return value <= 0 ? 0 : value + sumDown(value - 1); }
    default int sumArray(int[] values) { return values[0] + values[1]; }
    default int sumBoxes(BasicBox[] values) { return values[0].value + values[1].value; }
}

interface BasicParent extends BasicFace {}
interface BasicChild extends BasicParent { default int value(int value) { return value + 30; } }
interface BasicLeft extends BasicParent {}
interface BasicRight extends BasicParent {}
interface BasicDiamondFace extends BasicLeft, BasicRight {}
interface BasicLeaf extends BasicLeft, BasicRight { default int value(int value) { return value + 40; } }

class BasicImpl implements BasicFace {}
class BasicInherited implements BasicParent {}
class BasicChildImpl implements BasicChild {}
class BasicDiamond implements BasicDiamondFace {}
class BasicLeafImpl implements BasicLeaf {}
class BasicClassWins implements BasicFace { public int value(int value) { return value + 50; } }
class BasicClassBase { public int value(int value) { return value + 60; } }
class BasicClassChild extends BasicClassBase implements BasicFace {}
final class BasicFinalWins implements BasicFace { public int value(int value) { return value + 70; } }
class BasicBox { int value; BasicBox(int value) { this.value = value; } }
