package bundle.m4fc.init;

/** Active use initializes the declaring interface only; ordinary class default prerequisites stay distinct. */
public class InitRoot {
    public static int childStaticSkipsParent(int value) { return NoChild.work(value) + InitProbe.trace * 100; }
    public static int childFieldSkipsParent(int value) { return NoChild.CHILD + value + InitProbe.trace * 100; }
    public static int defaultChildStaticSkipsParent(int value) { return DefaultChild.work(value) + InitProbe.trace * 100; }
    public static int defaultChildFieldSkipsParent(int value) { return DefaultChild.CHILD + value + InitProbe.trace * 100; }
    public static int grandchildStaticSkipsAncestors(int value) { return GrandChild.work(value) + InitProbe.trace * 100; }
    public static int parentFieldThroughChild(int value) { return FieldChild.PARENT + value + InitProbe.trace * 100; }
    public static int grandFieldThroughChild(int value) { return FieldChild.GRAND + value + InitProbe.trace * 100; }
    public static int ownFieldOnly(int value) { return FieldChild.CHILD + value + InitProbe.trace * 100; }
    public static int explicitParentThenChild(int value) { int first = NoParent.work(value); int second = NoChild.work(value); return first + second + InitProbe.trace * 100; }
    public static int childThenParent(int value) { int first = NoChild.work(value); int second = NoParent.work(value); return first + second + InitProbe.trace * 100; }
    public static int repeatedStaticOnce(int value) { return NoChild.work(value) + NoChild.work(value + 1) + InitProbe.trace * 100; }
    public static int classDefaultPrerequisite(int value) { return ClassDefault.run(value) + InitProbe.trace * 100; }
    public static int interfaceCallsClass(int value) { return BridgeFace.callClass(value) + InitProbe.trace * 100; }
    public static int classCallsInterface(int value) { return InitCaller.callChild(value) + InitProbe.trace * 100; }
    public static int reentrantPreparedRead(int value) { return ReentrantFace.VALUE + InitProbe.seen * 100 + InitProbe.trace * 1000 + value; }
    public static int crossInterfaceCycle(int value) { return CycleA.VALUE * 100 + CycleB.VALUE + InitProbe.trace * 10000 + value; }
    public static int interfaceOrder(int value) { return OrderA.callB(value) + InitProbe.trace * 100; }
    public static int failingParentNotInitialized(int value) { return SafeChild.work(value) + InitProbe.trace * 100; }
    public static int failingDefaultParentNotInitialized(int value) { return SafeDefaultChild.work(value) + InitProbe.trace * 100; }
    public static int typeUseDoesNotInitialize(int value) { Object object = new PlainObject(value); return object instanceof TypeOnly ? InitProbe.trace : value; }
    public static int arrayUseDoesNotInitialize(int value) { TypeOnly[] values = new TypeOnly[1]; return values[0] == null ? value + InitProbe.trace : -1; }
}

class InitProbe {
    static int trace;
    static int seen;
    static int mark(int digit) { trace = trace * 10 + digit; return digit; }
    static int fail() { return 1 / zero(); }
    static int zero() { return 0; }
    static int reentrant() { mark(8); seen = ReentrantFace.peek(); return 81; }
    static int cycleA() { mark(1); return CycleB.readA() + 10; }
    static int cycleB() { mark(2); return CycleA.peek() + 20; }
}
interface NoParent { int PARENT = InitProbe.mark(1); static int work(int value) { return value + PARENT; } }
interface NoChild extends NoParent { int CHILD = InitProbe.mark(2); static int work(int value) { return value + CHILD; } }
interface DefaultParent { int PARENT = InitProbe.mark(3); default int defaultValue(int value) { return value + 3; } }
interface DefaultChild extends DefaultParent { int CHILD = InitProbe.mark(4); static int work(int value) { return value + CHILD; } }
interface GrandParent { int PARENT = InitProbe.mark(1); default int value(int value) { return value; } }
interface GrandMiddle extends GrandParent { int MIDDLE = InitProbe.mark(2); }
interface GrandChild extends GrandMiddle { int CHILD = InitProbe.mark(4); static int work(int value) { return value + CHILD; } }
interface FieldGrand { int GRAND = InitProbe.mark(6); }
interface FieldParent extends FieldGrand { int PARENT = InitProbe.mark(5); }
interface FieldChild extends FieldParent { int CHILD = InitProbe.mark(7); }
class ClassDefault implements DefaultParent {
    static int TOKEN = InitProbe.mark(5);
    static int run(int value) { return value + TOKEN; }
}
interface BridgeFace {
    int TOKEN = InitProbe.mark(6);
    static int callClass(int value) { return ClassDefault.run(value) + TOKEN; }
}
class InitCaller {
    static int TOKEN = InitProbe.mark(7);
    static int callChild(int value) { return NoChild.work(value) + TOKEN; }
}
interface ReentrantFace {
    int VALUE = InitProbe.reentrant();
    static int peek() { return VALUE; }
}
interface CycleA {
    int VALUE = InitProbe.cycleA();
    static int peek() { return VALUE; }
}
interface CycleB {
    int VALUE = InitProbe.cycleB();
    static int readA() { return CycleA.peek(); }
}
interface OrderA {
    int TOKEN = InitProbe.mark(1);
    static int callB(int value) { return OrderB.work(value) + TOKEN; }
}
interface OrderB {
    int TOKEN = InitProbe.mark(2);
    static int work(int value) { return value + TOKEN; }
}
interface FailingParent { int BAD = InitProbe.fail(); }
interface SafeChild extends FailingParent { int TOKEN = InitProbe.mark(9); static int work(int value) { return value + TOKEN; } }
interface FailingDefaultParent { int BAD = InitProbe.fail(); default int value(int value) { return value; } }
interface SafeDefaultChild extends FailingDefaultParent { int TOKEN = InitProbe.mark(9); static int work(int value) { return value + TOKEN; } }
interface TypeOnly { int BAD = InitProbe.fail(); }
class PlainObject implements TypeOnly { int value; PlainObject(int value) { this.value = value; } }
