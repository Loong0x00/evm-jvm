package bundle.m4b.constructors;

/** Constructor chaining, inherited/hidden fields, and ACC_SUPER direct calls. */
public class CtorRoot {
    public static int baseFields(int value) {
        CtorChild child = new CtorChild(value);
        return child.base + child.middle + child.child;
    }

    public static int thisChain(int value) {
        CtorChild child = new CtorChild(value, 4);
        return child.base * 100 + child.middle * 10 + child.child;
    }

    public static int defaultBeforeWrites(int value) {
        DefaultWitness witness = new DefaultWitness(value);
        return witness.observed + witness.after;
    }

    public static int ctorArgumentOrder(int a, int b, int c) {
        CtorChild child = new CtorChild(a, b, c);
        return child.base * 100 + child.middle * 10 + child.child;
    }

    public static int hiddenBase(int value) {
        CtorChild child = new CtorChild(value);
        return ((CtorBase) child).hidden;
    }

    public static int hiddenMiddle(int value) {
        CtorChild child = new CtorChild(value);
        return ((CtorMiddle) child).hidden;
    }

    public static int hiddenChild(int value) {
        CtorChild child = new CtorChild(value);
        return child.hidden;
    }

    public static int hiddenIndependent(int value) {
        CtorChild child = new CtorChild(value);
        ((CtorBase) child).hidden = 3;
        ((CtorMiddle) child).hidden = 5;
        child.hidden = value;
        return ((CtorBase) child).hidden * 100 + ((CtorMiddle) child).hidden * 10 + child.hidden;
    }

    public static int inheritedReference(int value) {
        CtorChild child = new CtorChild(value);
        CoreToken token = new CoreToken(value + 8);
        child.token = token;
        return child.token.value;
    }

    public static int superConstructorPublishes(int value) {
        CtorChild child = new CtorChild(value);
        return child.token.value;
    }

    public static int directSuperSelection(int value) {
        return CtorChild.callDirectSuper(value);
    }

    public static int privateChildHelper(int value) {
        return CtorChild.callPrivate(value);
    }

    public static int inheritedFinalRead(int value) {
        CtorChild child = new CtorChild(value);
        return child.baseFinal;
    }

    public static int ctorAllocatedArgument(int value) {
        ArgumentOwner owner = new ArgumentOwner(new CoreToken(value));
        return owner.token.value;
    }

    public static int nestedAllocation(int value) {
        ArgumentOwner owner = new ArgumentOwner(new CoreToken(value), value + 1);
        return owner.token.value + owner.extra;
    }
}

class CoreToken {
    public int value;
    CoreToken(int value) { this.value = value; }
}

class CtorBase {
    public int base;
    public int hidden;
    public final int baseFinal;
    public CoreToken token;

    CtorBase(int value) {
        base = value;
        hidden = value + 1;
        baseFinal = value + 2;
        token = new CoreToken(value + 3);
    }

    int selected(int value) { return value + 100; }
}

class CtorMiddle extends CtorBase {
    public int middle;
    public int hidden;

    CtorMiddle(int value) {
        super(value);
        middle = value + 4;
        hidden = value + 5;
    }

    int selected(int value) { return value + 200; }
}

class CtorChild extends CtorMiddle {
    public int child;
    public int hidden;

    CtorChild(int value) {
        this(value, value + 6);
    }

    CtorChild(int value, int childValue) {
        super(value);
        child = childValue;
        hidden = value + 7;
    }

    CtorChild(int a, int b, int c) {
        super(a);
        middle = b;
        child = c;
    }

    private int privateSelected(int value) { return value + child; }

    private int directSuper(int value) {
        return super.selected(value);
    }

    static int callDirectSuper(int value) {
        CtorChild child = new CtorChild(1);
        return child.directSuper(value);
    }

    static int callPrivate(int value) {
        CtorChild child = new CtorChild(value);
        return child.privateSelected(9);
    }
}

class DefaultWitness {
    public int observed;
    public int after;

    DefaultWitness(int value) {
        observed = after;
        after = value;
    }
}

class ArgumentOwner {
    public CoreToken token;
    public int extra;

    ArgumentOwner(CoreToken token) {
        this.token = token;
    }

    ArgumentOwner(CoreToken token, int extra) {
        this(token);
        this.extra = extra;
    }
}
