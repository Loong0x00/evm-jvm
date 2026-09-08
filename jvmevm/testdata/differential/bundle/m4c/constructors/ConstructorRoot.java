package bundle.m4c.constructors;

/** Constructor-time virtual callbacks observe derived prepared defaults. */
public class ConstructorRoot {
    public static int childSeesZero(int value) {
        ConstructorChild child = new ConstructorChild(value);
        return child.observedNumber;
    }

    public static int childSeesNull(int yes) {
        ConstructorChild child = new ConstructorChild(1);
        return child.observedNull == 1 ? yes : -1;
    }

    public static int callbackWriteThenInitializer(int value) {
        ConstructorChild child = new ConstructorChild(value);
        return child.childValue;
    }

    public static int callbackObservedWrite(int value) {
        ConstructorChild child = new ConstructorChild(value);
        return child.observedWrite;
    }

    public static int initializedAfterCallback(int value) {
        ConstructorChild child = new ConstructorChild(value);
        return child.childValue + child.childToken.value;
    }

    public static int grandSeesDefaults(int value) {
        ConstructorGrand grand = new ConstructorGrand(value);
        return grand.observedNumber;
    }

    public static int grandInitializedAfterCallback(int value) {
        ConstructorGrand grand = new ConstructorGrand(value);
        return grand.childValue + grand.grandValue + grand.childToken.value;
    }
}

class ConstructorBase {
    int observedNumber;
    int observedNull;
    int observedWrite;

    ConstructorBase(int value) {
        observedNumber = readNumber();
        observedNull = readToken() == null ? 1 : 0;
        writeNumber(value);
        observedWrite = readNumber();
    }

    int readNumber() { return -1; }
    ConstructorToken readToken() { return new ConstructorToken(-1); }
    void writeNumber(int value) { observedWrite = value; }
}

class ConstructorChild extends ConstructorBase {
    int childValue = 40;
    ConstructorToken childToken = new ConstructorToken(9);

    ConstructorChild(int value) {
        super(value);
    }

    int readNumber() { return childValue; }
    ConstructorToken readToken() { return childToken; }
    void writeNumber(int value) { childValue = value; }
}

class ConstructorGrand extends ConstructorChild {
    int grandValue = 60;

    ConstructorGrand(int value) {
        super(value);
    }

    int readNumber() { return childValue + grandValue; }
}

class ConstructorToken {
    int value;
    ConstructorToken(int value) { this.value = value; }
}
