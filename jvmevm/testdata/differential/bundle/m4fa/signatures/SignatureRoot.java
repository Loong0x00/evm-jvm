package bundle.m4fa.signatures;

/** Category-1 integer, void, ordinary-reference, Object, and int-array interface calls. */
public class SignatureRoot {
    private static SignatureOps make(int value) {
        return new SignatureImpl(value);
    }

    public static int zeroArguments(int value) {
        return make(value).read();
    }

    public static int threeIntegers(int value) {
        return make(value).combine(value + 1, value + 2, value + 3);
    }

    public static int voidMutation(int value) {
        SignatureOps receiver = make(0);
        receiver.set(value);
        return receiver.read();
    }

    public static int discardedIntegerResult(int value) {
        SignatureOps receiver = make(value);
        receiver.combine(1, 2, 3);
        return receiver.read();
    }

    public static int referenceArgument(int value) {
        SignatureOps receiver = make(1);
        return receiver.readCarrier(new SignatureCarrier(value));
    }

    public static int referenceReturn(int value) {
        SignatureOps receiver = make(value);
        return receiver.makeCarrier(value + 7).value;
    }

    public static int referenceIdentity(int value) {
        SignatureOps receiver = make(0);
        SignatureCarrier carrier = new SignatureCarrier(value);
        return receiver.identity(carrier) == carrier ? carrier.value : -1;
    }

    public static int interfaceReferenceReturn(int value) {
        SignatureOps receiver = make(value);
        SignatureReadable readable = receiver.asReadable();
        return readable.read();
    }

    public static int interfaceReferenceArgument(int value) {
        SignatureOps receiver = make(3);
        SignatureReadable readable = new SignatureCarrier(value);
        return receiver.readReadable(readable);
    }

    public static int objectArgument(int value) {
        SignatureOps receiver = make(4);
        Object object = new SignatureCarrier(value);
        return receiver.objectIsCarrier(object) != 0 ? value : -1;
    }

    public static int objectReturnIdentity(int value) {
        SignatureOps receiver = make(value);
        return receiver.asObject() == receiver ? value : -1;
    }

    public static int arrayArgument(int value) {
        SignatureOps receiver = make(5);
        int[] values = new int[] { value, value + 1 };
        return receiver.sum(values);
    }

    public static int arrayReturn(int value) {
        SignatureOps receiver = make(value);
        int[] values = receiver.makeArray(value + 1);
        return values[0] + values[1];
    }

    public static int mixedReferenceArguments(int value) {
        SignatureOps receiver = make(6);
        SignatureCarrier carrier = new SignatureCarrier(value);
        int[] values = new int[] { value + 2 };
        return receiver.mixed(carrier, values, value + 3);
    }
}

interface SignatureReadable {
    int read();
}

interface SignatureOps extends SignatureReadable {
    int combine(int first, int second, int third);
    void set(int value);
    int readCarrier(SignatureCarrier carrier);
    SignatureCarrier makeCarrier(int value);
    SignatureCarrier identity(SignatureCarrier carrier);
    SignatureReadable asReadable();
    int readReadable(SignatureReadable readable);
    int objectIsCarrier(Object value);
    Object asObject();
    int sum(int[] values);
    int[] makeArray(int value);
    int mixed(SignatureCarrier carrier, int[] values, int add);
}

class SignatureCarrier implements SignatureReadable {
    int value;
    SignatureCarrier(int value) { this.value = value; }
    public int read() { return value; }
}

class SignatureImpl implements SignatureOps {
    int value;
    SignatureImpl(int value) { this.value = value; }

    public int read() { return value; }
    public int combine(int first, int second, int third) { return value + first + second + third; }
    public void set(int value) { this.value = value; }
    public int readCarrier(SignatureCarrier carrier) { return carrier.value + value; }
    public SignatureCarrier makeCarrier(int value) { return new SignatureCarrier(this.value + value); }
    public SignatureCarrier identity(SignatureCarrier carrier) { return carrier; }
    public SignatureReadable asReadable() { return this; }
    public int readReadable(SignatureReadable readable) { return readable.read() + value; }
    public int objectIsCarrier(Object object) { return object instanceof SignatureCarrier ? 1 : 0; }
    public Object asObject() { return this; }
    public int sum(int[] values) { return value + values[0] + values[1]; }
    public int[] makeArray(int value) { return new int[] { this.value, value }; }
    public int mixed(SignatureCarrier carrier, int[] values, int add) {
        return value + carrier.value + values[0] + add;
    }
}
