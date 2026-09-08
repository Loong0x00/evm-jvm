package bundle.m4fc.basic;

/** Interface static methods called from interfaces, classes, and defaults. */
public class BasicRoot {
    public static int interfaceCall(int value) { return BasicStatics.add(value, 7); }
    public static int interfaceNested(int value) { return BasicStatics.twice(value); }
    public static int interfaceZero(int value) { return BasicStatics.constant() + value; }
    public static int interfaceVoid(int value) { BasicBox box = new BasicBox(value); BasicStatics.adjust(box, 4); return box.value; }
    public static int classToInterface(int value) { return BasicClass.callsInterface(value); }
    public static int interfaceToClass(int value) { return BasicStatics.callsClass(value); }
    public static int interfaceToInterface(int value) { return OtherStatics.callsBasic(value); }
    public static int twoInterfaces(int value) { return BasicStatics.add(value, 1) + OtherStatics.offset(value); }
    public static int defaultCallsStatic(int value) { return new BasicImpl().fromDefault(value); }
    public static int defaultCallsOtherStatic(int value) { return new BasicImpl().fromOtherDefault(value); }
    public static int repeatedSite(int value) { return BasicStatics.add(value, 1) + BasicStatics.add(value, 2); }
    public static int recursiveStatic(int value) { return BasicStatics.sumDown(value); }
    public static int negativeRecursiveBase(int value) { return BasicStatics.sumDown(value); }
    public static int callerPrefix(int value) { return value * 100 + BasicStatics.add(value, 3); }
    public static int publicRootViaClass(int value) { return PublicStatics.root(value); }
    public static int publicRootNested(int value) { return PublicStatics.nested(value); }
}

interface BasicStatics {
    static int add(int first, int second) { return first + second; }
    static int constant() { return 23; }
    static int twice(int value) { return add(value, value); }
    static void adjust(BasicBox box, int delta) { box.value = box.value + delta; }
    static int callsClass(int value) { return BasicClass.ordinary(value); }
    static int sumDown(int value) { return value <= 0 ? 0 : value + sumDown(value - 1); }
}

interface OtherStatics {
    static int offset(int value) { return value + 30; }
    static int callsBasic(int value) { return BasicStatics.add(value, 9); }
}

interface BasicDefault {
    default int fromDefault(int value) { return BasicStatics.add(value, 40); }
    default int fromOtherDefault(int value) { return OtherStatics.offset(value) + 1; }
}

class BasicImpl implements BasicDefault {}
class BasicBox { int value; BasicBox(int value) { this.value = value; } }
class BasicClass {
    static int ordinary(int value) { return value * 3; }
    static int callsInterface(int value) { return BasicStatics.add(value, 50); }
}
