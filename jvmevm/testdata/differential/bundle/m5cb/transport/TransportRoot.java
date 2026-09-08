package bundle.m5cb.transport;

class ScalarInit {
    static int trace;

    static float initializeDefaultFloat() {
        trace = trace * 10 + 3;
        return Float.intBitsToFloat(0x00000001);
    }
}

interface ScalarDefault {
    float INTERFACE_FLOAT = 0x1.fffffep23f;
    double INTERFACE_DOUBLE = 0x1.0000000000001p53;
    float INITIALIZED_FLOAT = ScalarInit.initializeDefaultFloat();

    float passFloat(float value);
    double passDouble(double value);

    default float defaultFloat(float value) { return value; }
    default double defaultDouble(double value) { return value; }

    static float staticFloat(float value) { return value; }
    static double staticDouble(double value) { return value; }
}

interface DirectScalar {
    default double direct(double value) { return value; }
}

class ScalarParent {
    static float hiddenFloat = Float.intBitsToFloat(0x3f012345);
    static double hiddenDouble = Double.longBitsToDouble(0x400123456789abcdL);
    float instanceFloat;
    double instanceDouble;
}

class ScalarCarrier extends ScalarParent implements ScalarDefault {
    static float hiddenFloat = Float.intBitsToFloat(0x7fc12345);
    static double hiddenDouble = Double.longBitsToDouble(0x7ff8123456789abcL);

    final float finalFloat;
    final double finalDouble;

    ScalarCarrier(float f, double d) {
        finalFloat = f;
        finalDouble = d;
    }

    public float passFloat(float value) { return value; }
    public double passDouble(double value) { return value; }
    float virtualFloat(float value) { return value; }
    double virtualDouble(double value) { return value; }

    private float privateFloat(float value) { return value; }
    private double privateDouble(double value) { return value; }
    float callPrivateFloat(float value) { return privateFloat(value); }
    double callPrivateDouble(double value) { return privateDouble(value); }
}

class DirectCarrier implements DirectScalar {
    double callDirect(double value) { return DirectScalar.super.direct(value); }
}

class ScalarState {
    static int trace;
    static float preparedFloat;
    static double preparedDouble;
    static final float CONSTANT_FLOAT = 0x1.000002p0f;
    static final double CONSTANT_DOUBLE = 0x1.0000000000001p0;
    static float initializedFloat = initializeFloat();
    static double initializedDouble = initializeDouble();

    private static float initializeFloat() {
        trace = trace * 10 + 1;
        return Float.intBitsToFloat(0x80000000);
    }

    private static double initializeDouble() {
        trace = trace * 10 + 2;
        return Double.longBitsToDouble(0x0000000000000001L);
    }
}

/** Scalar field, initialization, and every accepted call-mode transport. */
public strictfp class TransportRoot {
    private static long join(int high, int low) {
        return ((long) high << 32) | (low & 0xffffffffL);
    }

    private static float asFloat(int bits) { return Float.intBitsToFloat(bits); }
    private static double asDouble(int high, int low) { return Double.longBitsToDouble(join(high, low)); }
    private static int fbits(float value) { return Float.floatToRawIntBits(value); }
    private static long dbits(double value) { return Double.doubleToRawLongBits(value); }

    private static float staticFloat(float value) { return value; }
    private static double staticDouble(double value) { return value; }

    private static double mixedStatic(float f, long j, double d, int i) {
        if (f == f && j == j && i == i) return d;
        return d;
    }

    private static float recursiveFloat(float value, int depth) {
        if (depth == 0) return value;
        return recursiveFloat(value, depth - 1);
    }

    public static int staticFloatCall(int bits) { return fbits(staticFloat(asFloat(bits))); }
    public static int staticDoubleCallHigh(int high, int low) {
        return (int) (dbits(staticDouble(asDouble(high, low))) >>> 32);
    }
    public static int allFloatCallModes(int bits) {
        float value = staticFloat(asFloat(bits));
        ScalarCarrier concrete = new ScalarCarrier(0.0f, 0.0d);
        value = concrete.callPrivateFloat(value);
        value = concrete.virtualFloat(value);
        ScalarDefault view = concrete;
        value = view.passFloat(value);
        value = view.defaultFloat(value);
        value = ScalarDefault.staticFloat(value);
        return fbits(value);
    }
    public static int allDoubleCallModesLow(int high, int low) {
        double value = staticDouble(asDouble(high, low));
        ScalarCarrier concrete = new ScalarCarrier(0.0f, 0.0d);
        value = concrete.callPrivateDouble(value);
        value = concrete.virtualDouble(value);
        ScalarDefault view = concrete;
        value = view.passDouble(value);
        value = view.defaultDouble(value);
        value = new DirectCarrier().callDirect(value);
        value = ScalarDefault.staticDouble(value);
        return (int) dbits(value);
    }
    public static int privateFloatCall(int bits) {
        return fbits(new ScalarCarrier(0.0f, 0.0d).callPrivateFloat(asFloat(bits)));
    }
    public static int privateDoubleCallLow(int high, int low) {
        return (int) dbits(new ScalarCarrier(0.0f, 0.0d).callPrivateDouble(asDouble(high, low)));
    }
    public static int virtualFloatCall(int bits) {
        ScalarCarrier carrier = new ScalarCarrier(0.0f, 0.0d);
        return fbits(carrier.virtualFloat(asFloat(bits)));
    }
    public static int virtualDoubleCallHigh(int high, int low) {
        ScalarCarrier carrier = new ScalarCarrier(0.0f, 0.0d);
        return (int) (dbits(carrier.virtualDouble(asDouble(high, low))) >>> 32);
    }
    public static int interfaceFloatCall(int bits) {
        ScalarDefault carrier = new ScalarCarrier(0.0f, 0.0d);
        return fbits(carrier.passFloat(asFloat(bits)));
    }
    public static int interfaceDoubleCallLow(int high, int low) {
        ScalarDefault carrier = new ScalarCarrier(0.0f, 0.0d);
        return (int) dbits(carrier.passDouble(asDouble(high, low)));
    }
    public static int defaultFloatCall(int bits) {
        ScalarDefault carrier = new ScalarCarrier(0.0f, 0.0d);
        return fbits(carrier.defaultFloat(asFloat(bits)));
    }
    public static int defaultDoubleCallHigh(int high, int low) {
        ScalarDefault carrier = new ScalarCarrier(0.0f, 0.0d);
        return (int) (dbits(carrier.defaultDouble(asDouble(high, low))) >>> 32);
    }
    public static int directDefaultDoubleLow(int high, int low) {
        return (int) dbits(new DirectCarrier().callDirect(asDouble(high, low)));
    }
    public static int interfaceStaticFloat(int bits) {
        return fbits(ScalarDefault.staticFloat(asFloat(bits)));
    }
    public static int interfaceStaticDoubleHigh(int high, int low) {
        return (int) (dbits(ScalarDefault.staticDouble(asDouble(high, low))) >>> 32);
    }
    public static int constructorFinalFloat(int bits) {
        return fbits(new ScalarCarrier(asFloat(bits), 0.0d).finalFloat);
    }
    public static int constructorFinalDoubleLow(int high, int low) {
        return (int) dbits(new ScalarCarrier(0.0f, asDouble(high, low)).finalDouble);
    }
    public static int defaultInstanceFloat(int ignored) { return fbits(new ScalarCarrier(0.0f, 0.0d).instanceFloat); }
    public static int defaultInstanceDoubleHigh(int ignored) {
        return (int) (dbits(new ScalarCarrier(0.0f, 0.0d).instanceDouble) >>> 32);
    }
    public static int preparedStaticFloat(int ignored) { return fbits(ScalarState.preparedFloat); }
    public static int preparedStaticDoubleHigh(int ignored) { return (int) (dbits(ScalarState.preparedDouble) >>> 32); }
    public static int constantFloat(int ignored) { return fbits(ScalarState.CONSTANT_FLOAT); }
    public static int constantDoubleLow(int ignored) { return (int) dbits(ScalarState.CONSTANT_DOUBLE); }
    public static int interfaceConstantFloat(int ignored) { return fbits(ScalarDefault.INTERFACE_FLOAT); }
    public static int interfaceConstantDoubleHigh(int ignored) {
        return (int) (dbits(ScalarDefault.INTERFACE_DOUBLE) >>> 32);
    }
    public static int hiddenParentFloat(int ignored) { return fbits(ScalarParent.hiddenFloat); }
    public static int hiddenChildDoubleLow(int ignored) { return (int) dbits(ScalarCarrier.hiddenDouble); }
    public static int initializationTrace(int ignored) {
        float f = ScalarState.initializedFloat;
        double d = ScalarState.initializedDouble;
        if (f == f && d == d) return ScalarState.trace;
        return -1;
    }
    public static int initializedSignedZero(int ignored) { return fbits(ScalarState.initializedFloat); }
    public static int initializedSubnormalLow(int ignored) { return (int) dbits(ScalarState.initializedDouble); }
    public static int defaultInterfaceInitialization(int ignored) {
        ScalarDefault carrier = new ScalarCarrier(0.0f, 0.0d);
        return carrier == null ? -1 : ScalarInit.trace;
    }
    public static int defaultInterfaceInitializedBits(int ignored) {
        return fbits(ScalarDefault.INITIALIZED_FLOAT);
    }
    public static int mixedCategoryCallHigh(int floatBits, int longHigh, int longLow, int doubleHigh, int doubleLow) {
        double value = mixedStatic(asFloat(floatBits), join(longHigh, longLow), asDouble(doubleHigh, doubleLow), floatBits);
        return (int) (dbits(value) >>> 32);
    }
    public static int recursiveQuietNaN(int bits, int depth) { return fbits(recursiveFloat(asFloat(bits), depth)); }
    public static int referenceSeparated(int bits) {
        Object marker = new ScalarCarrier(0.0f, 0.0d);
        float value = asFloat(bits);
        return marker == null ? 0 : fbits(value);
    }
}
