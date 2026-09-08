package bundle.m4c.signatures;

/** Virtual methods with integer, void, ordinary-reference, Object, and int[] signatures. */
public class SignatureRoot {
    private static int combineAtSite(SignatureBase receiver, int a, int b) {
        return receiver.combine(a, b);
    }

    private static void writeAtSite(SignatureBase receiver, int value) {
        receiver.write(value);
    }

    private static SignatureCell cellAtSite(SignatureBase receiver, SignatureCell value) {
        return receiver.echoCell(value);
    }

    private static Object objectAtSite(SignatureBase receiver, Object value) {
        return receiver.echoObject(value);
    }

    private static int[] arrayAtSite(SignatureBase receiver, int[] value) {
        return receiver.echoArray(value);
    }

    private static SignatureBase baseAtSite(SignatureBase receiver, SignatureBase value) {
        return receiver.echoBase(value);
    }

    public static int intArgsBase(int a, int b) {
        return combineAtSite(new SignatureBase(), a, b);
    }

    public static int intArgsChild(int a, int b) {
        return combineAtSite(new SignatureChild(), a, b);
    }

    public static int voidBase(int value) {
        SignatureBase receiver = new SignatureBase();
        writeAtSite(receiver, value);
        return receiver.state;
    }

    public static int voidChild(int value) {
        SignatureBase receiver = new SignatureChild();
        writeAtSite(receiver, value);
        return receiver.state;
    }

    public static int cellArgumentBase(int value) {
        SignatureCell cell = new SignatureCell(value);
        return cellAtSite(new SignatureBase(), cell).value;
    }

    public static int cellArgumentChild(int value) {
        SignatureCell cell = new SignatureCell(value);
        return cellAtSite(new SignatureChild(), cell).value;
    }

    public static int objectArgumentIdentity(int yes) {
        SignatureCell cell = new SignatureCell(1);
        Object result = objectAtSite(new SignatureChild(), cell);
        return result == cell ? yes : -1;
    }

    public static int objectArrayIdentity(int yes) {
        int[] array = new int[1];
        Object result = objectAtSite(new SignatureChild(), array);
        return result == array ? yes : -1;
    }

    public static int arrayArgumentBase(int value) {
        int[] array = new int[1];
        arrayAtSite(new SignatureBase(), array)[0] = value;
        return array[0];
    }

    public static int arrayArgumentChild(int value) {
        int[] array = new int[1];
        arrayAtSite(new SignatureChild(), array)[0] = value;
        return array[0];
    }

    public static int ordinaryReferenceReturn(int value) {
        SignatureBase supplied = new SignatureBase();
        supplied.state = value;
        SignatureBase result = baseAtSite(new SignatureChild(), supplied);
        return result.state;
    }

    public static int nullReferenceArgument(int yes) {
        SignatureCell result = cellAtSite(new SignatureChild(), null);
        return result == null ? yes : -1;
    }

    public static int alternatingSignatures(int value) {
        SignatureBase base = new SignatureBase();
        SignatureBase child = new SignatureChild();
        writeAtSite(base, value);
        writeAtSite(child, value);
        return combineAtSite(base, base.state, 1) + combineAtSite(child, child.state, 1);
    }
}

class SignatureBase {
    int state;

    int combine(int a, int b) { return a * 10 + b; }
    void write(int value) { state = value; }
    SignatureCell echoCell(SignatureCell value) { return value; }
    Object echoObject(Object value) { return value; }
    int[] echoArray(int[] value) { return value; }
    SignatureBase echoBase(SignatureBase value) { return value; }
}

class SignatureChild extends SignatureBase {
    int combine(int a, int b) { return a * 100 + b; }
    void write(int value) { state = value + 5; }
    SignatureCell echoCell(SignatureCell value) {
        if (value != null) value.value += 3;
        return value;
    }
    Object echoObject(Object value) { return value; }
    int[] echoArray(int[] value) { return value; }
    SignatureBase echoBase(SignatureBase value) { return value; }
}

class SignatureCell {
    int value;
    SignatureCell(int value) { this.value = value; }
}
