package bundle.m4fb.supercalls;

/** Legal direct-superinterface invokespecial calls from classes and interfaces. */
public class SuperRoot {
    public static int classParentSuper(int value) { return new SuperDirect().callParent(value); }
    public static int classLeftSuper(int value) { return new SuperDual().callLeft(value); }
    public static int classRightSuper(int value) { return new SuperDual().callRight(value); }
    public static int classBothSupers(int value) { return new SuperDual().both(value); }
    public static int interfaceParentSuper(int value) { return new SuperChildImpl().run(value); }
    public static int interfaceParentRef(int value) { return new SuperChildImpl().make(value).value; }
    public static int interfaceParentVoid(int value) {
        SuperBox box = new SuperBox(value); new SuperChildImpl().change(box); return box.value;
    }
    public static int interfaceGrandChain(int value) { return new SuperGrandImpl().run(value); }
    public static int interfaceTwoParentSupers(int value) { return new SuperJoinImpl().run(value); }
    public static int recursiveParentSuper(int value) { return new SuperRecursiveImpl().total(value); }
    public static int parentDefaultDirect(int value) { return new SuperDirect().run(value); }
    public static int childDefaultDirect(int value) { return new SuperChildImpl().run(value); }
    public static int constructorCallbackDefault(int value) { return new CallbackChild(value).seen; }
    public static int constructorCallbackThenField(int value) {
        CallbackChild child = new CallbackChild(value); return child.seen * 100 + child.after;
    }
    public static int constructorCallbackOverride(int value) { return new CallbackOverride(value).seen; }
}

interface SuperParent {
    default int run(int value) { return value + 10; }
    default SuperBox make(int value) { return new SuperBox(value + 20); }
    default void change(SuperBox box) { box.value = box.value + 30; }
}
class SuperDirect implements SuperParent {
    int callParent(int value) { return SuperParent.super.run(value) + 1; }
}
interface SuperLeft { default int run(int value) { return value + 2; } }
interface SuperRight { default int run(int value) { return value + 3; } }
class SuperDual implements SuperLeft, SuperRight {
    public int run(int value) { return SuperLeft.super.run(value) + SuperRight.super.run(value); }
    int callLeft(int value) { return SuperLeft.super.run(value); }
    int callRight(int value) { return SuperRight.super.run(value); }
    int both(int value) { return callLeft(value) * 100 + callRight(value); }
}
interface SuperChild extends SuperParent {
    default int run(int value) { return SuperParent.super.run(value) + 40; }
    default SuperBox make(int value) { SuperBox box = SuperParent.super.make(value); box.value++; return box; }
    default void change(SuperBox box) { SuperParent.super.change(box); box.value++; }
}
class SuperChildImpl implements SuperChild {}
interface SuperGrand extends SuperChild { default int run(int value) { return SuperChild.super.run(value) + 50; } }
class SuperGrandImpl implements SuperGrand {}
interface SuperJoin extends SuperLeft, SuperRight {
    default int run(int value) { return SuperLeft.super.run(value) * 10 + SuperRight.super.run(value); }
}
class SuperJoinImpl implements SuperJoin {}
interface SuperRecursiveParent { default int total(int value) { return value <= 0 ? 0 : value + total(value - 1); } }
interface SuperRecursiveChild extends SuperRecursiveParent {
    default int total(int value) { return value <= 0 ? 5 : SuperRecursiveParent.super.total(value); }
}
class SuperRecursiveImpl implements SuperRecursiveChild {}
interface CallbackFace { default int callback(int value) { return value + 7; } }
class CallbackBase implements CallbackFace {
    int seen;
    CallbackBase(int value) { seen = callback(value); }
}
class CallbackChild extends CallbackBase { int after = 9; CallbackChild(int value) { super(value); } }
class CallbackOverride extends CallbackBase {
    int offset = 11;
    CallbackOverride(int value) { super(value); }
    public int callback(int value) { return value + offset; }
}
class SuperBox { int value; SuperBox(int value) { this.value = value; } }
