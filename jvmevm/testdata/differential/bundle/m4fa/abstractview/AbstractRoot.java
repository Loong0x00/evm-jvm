package bundle.m4fa.abstractview;

/** invokevirtual resolution through abstract class views whose method comes only from an interface. */
public class AbstractRoot {
    private static int call(AbstractBase receiver, int value) {
        return receiver.apply(value);
    }

    public static int directFallback(int value) {
        AbstractBase receiver = new AbstractChild();
        return call(receiver, value);
    }

    public static int grandchildFallback(int value) {
        AbstractBase receiver = new AbstractGrandchild();
        return call(receiver, value);
    }

    public static int alternatingFallback(int value) {
        return call(new AbstractChild(), value) * 100 + call(new AbstractOther(), value);
    }

    public static int repeatedFallback(int value) {
        AbstractBase first = new AbstractChild();
        AbstractBase second = new AbstractOther();
        return call(first, value) + call(second, value) + call(first, value + 1) + call(second, value + 1);
    }

    public static int interfaceViewOfAbstract(int value) {
        AbstractOperation receiver = new AbstractChild();
        return receiver.apply(value);
    }

    public static int inheritedAbstractImplementation(int value) {
        AbstractOperation receiver = new AbstractInherited();
        return receiver.apply(value);
    }

    public static int constructorVirtualDefault(int value) {
        CallbackChild child = new CallbackChild(value);
        return child.seen * 100 + child.derived;
    }

    public static int constructorInterfaceDefault(int value) {
        InterfaceCallbackChild child = new InterfaceCallbackChild(value);
        return child.seen * 100 + child.derived;
    }

    public static int constructorVirtualAfterFields(int value) {
        CallbackChild child = new CallbackChild(value);
        return child.after();
    }

    public static int constructorInterfaceAfterFields(int value) {
        InterfaceCallbackChild child = new InterfaceCallbackChild(value);
        return child.after();
    }
}

interface AbstractOperation {
    int apply(int value);
}

abstract class AbstractBase implements AbstractOperation {
}

class AbstractChild extends AbstractBase {
    public int apply(int value) { return value + 11; }
}

class AbstractGrandchild extends AbstractChild {
    public int apply(int value) { return value + 111; }
}

class AbstractOther extends AbstractBase {
    public int apply(int value) { return value + 22; }
}

class AbstractImplementationBase {
    public int apply(int value) { return value + 33; }
}

class AbstractInherited extends AbstractImplementationBase implements AbstractOperation {
}

abstract class CallbackBase implements AbstractOperation {
    int seen;
    CallbackBase() { seen = apply(1); }
}

class CallbackChild extends CallbackBase {
    int derived;
    CallbackChild(int value) { derived = value; }
    public int apply(int value) { return derived + value; }
    int after() { return apply(2); }
}

interface InterfaceCallback {
    int callback(int value);
}

abstract class InterfaceCallbackBase implements InterfaceCallback {
    int seen;
    InterfaceCallbackBase() { seen = ((InterfaceCallback) this).callback(1); }
}

class InterfaceCallbackChild extends InterfaceCallbackBase {
    int derived;
    InterfaceCallbackChild(int value) { derived = value; }
    public int callback(int value) { return derived + value; }
    int after() { return callback(2); }
}
