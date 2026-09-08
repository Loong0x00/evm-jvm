package bundle.m4c.dispatch;

/** Basic virtual selection and receiver-class cache fixtures. */
public class DispatchRoot {
    private static int call(DispatchBase receiver, int value) {
        return receiver.select(value);
    }

    public static int baseReceiver(int value) {
        return call(new DispatchBase(), value);
    }

    public static int childReceiver(int value) {
        return call(new DispatchChild(), value);
    }

    public static int grandReceiver(int value) {
        return call(new DispatchGrand(), value);
    }

    public static int inheritedReceiver(int value) {
        return call(new DispatchInherited(), value);
    }

    public static int finalReceiver(int value) {
        FinalChild child = new FinalChild();
        return child.fixed(value);
    }

    public static int alternatingBaseChild(int value) {
        DispatchBase first = new DispatchBase();
        DispatchBase second = new DispatchChild();
        return call(first, value) * 100 + call(second, value);
    }

    public static int alternatingChildBase(int value) {
        DispatchBase first = new DispatchChild();
        DispatchBase second = new DispatchBase();
        return call(first, value) * 100 + call(second, value);
    }

    public static int alternatingGrandInherited(int value) {
        DispatchBase first = new DispatchGrand();
        DispatchBase second = new DispatchInherited();
        return call(first, value) * 100 + call(second, value);
    }

    public static int repeatedAlternation(int value) {
        DispatchBase base = new DispatchBase();
        DispatchBase child = new DispatchChild();
        return call(base, value) + call(child, value) + call(base, value + 1) + call(child, value + 1);
    }

    public static int selectedState(int value) {
        DispatchBase receiver = new DispatchChild();
        receiver.state = value;
        return receiver.readState(3);
    }

    public static int inheritedState(int value) {
        DispatchBase receiver = new DispatchInherited();
        receiver.state = value;
        return receiver.readState(4);
    }

    public static int nullVirtual(int value) {
        DispatchBase receiver = null;
        return receiver.select(value);
    }
}

class DispatchBase {
    int state;

    int select(int value) { return value + 1; }
    int readState(int add) { return state + add; }
}

class DispatchChild extends DispatchBase {
    int select(int value) { return value + 10; }
    int readState(int add) { return state * 2 + add; }
}

class DispatchGrand extends DispatchChild {
    int select(int value) { return value + 100; }
}

class DispatchInherited extends DispatchChild {
}

class FinalBase {
    final int fixed(int value) { return value + 700; }
}

class FinalChild extends FinalBase {
}
