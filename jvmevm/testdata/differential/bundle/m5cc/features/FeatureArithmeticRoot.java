package bundle.m5cc.features;

interface M5ccFloatDefault {
    default float multiply(float left, float right) { return left * right; }
}

interface M5ccDoubleDefault {
    default double remainder(double left, double right) { return left % right; }
}

interface M5ccDirectFloat {
    default float remainder(float left, float right) { return left % right; }
}

class M5ccFeatureParent {
    float divide(float left, float right) { return left / right; }
}

class M5ccFeatureCarrier extends M5ccFeatureParent
        implements M5ccFloatDefault, M5ccDoubleDefault {
    float floatField;
    double doubleField;
    final float constructedFloat;
    final double constructedDouble;

    M5ccFeatureCarrier(float fa, float fb, double da, double db) {
        constructedFloat = fa - fb;
        constructedDouble = da + db;
    }
}

class M5ccDirectCarrier implements M5ccDirectFloat {
    float directRemainder(float left, float right) {
        return M5ccDirectFloat.super.remainder(left, right);
    }
}

strictfp class M5ccStrictWorker {
    static float add(float left, float right) { return left + right; }
    static double multiply(double left, double right) { return left * right; }
}

class M5ccInit {
    static float mutableFloat;

    private static float floatSource(int bits) {
        return Float.intBitsToFloat(bits);
    }

    private static double doubleSource(long bits) {
        return Double.longBitsToDouble(bits);
    }

    // Calls prevent javac constant folding. Both divisions execute in <clinit>;
    // neither floating zero divisor is a Java ArithmeticException.
    static float floatDivision = floatSource(0x3f800000) / floatSource(0x00000000);
    static double zeroDivision = doubleSource(0L) / doubleSource(0L);
}

/** Calls, defaults, constructors, fields, post-increment, and class initialization. */
public class FeatureArithmeticRoot {
    private static long join(int high, int low) {
        return ((long) high << 32) | (low & 0xffffffffL);
    }

    private static float asFloat(int bits) {
        return Float.intBitsToFloat(bits);
    }

    private static double asDouble(int high, int low) {
        return Double.longBitsToDouble(join(high, low));
    }

    private static int fbits(float value) {
        return value != value ? 0x7fc00000 : Float.floatToRawIntBits(value);
    }

    private static long dbits(double value) {
        return value != value ? 0x7ff8000000000000L : Double.doubleToRawLongBits(value);
    }

    public static int strictFloatAdd(int left, int right) {
        return fbits(M5ccStrictWorker.add(asFloat(left), asFloat(right)));
    }

    public static int defaultFloatMultiply(int left, int right) {
        M5ccFloatDefault worker = new M5ccFeatureCarrier(0.0f, 0.0f, 0.0d, 0.0d);
        return fbits(worker.multiply(asFloat(left), asFloat(right)));
    }

    public static int virtualFloatDivide(int left, int right) {
        M5ccFeatureParent worker = new M5ccFeatureCarrier(0.0f, 0.0f, 0.0d, 0.0d);
        return fbits(worker.divide(asFloat(left), asFloat(right)));
    }

    public static int directFloatRemainder(int left, int right) {
        return fbits(new M5ccDirectCarrier().directRemainder(asFloat(left), asFloat(right)));
    }

    public static int constructorFloatSubtract(int left, int right) {
        M5ccFeatureCarrier value = new M5ccFeatureCarrier(
                asFloat(left), asFloat(right), 0.0d, 0.0d);
        return fbits(value.constructedFloat);
    }

    public static int instanceFloatPostIncrement(int bits) {
        M5ccFeatureCarrier value = new M5ccFeatureCarrier(0.0f, 0.0f, 0.0d, 0.0d);
        value.floatField = asFloat(bits);
        value.floatField++;
        return fbits(value.floatField);
    }

    public static int staticFloatCompound(int left, int right) {
        M5ccInit.mutableFloat = asFloat(left);
        M5ccInit.mutableFloat += asFloat(right);
        return fbits(M5ccInit.mutableFloat);
    }

    public static int classInitFloatDivision(int ignored) {
        // Reading both fields proves 1/+0 and 0/0 completed as values in <clinit>.
        double generatedNaN = M5ccInit.zeroDivision;
        return generatedNaN != generatedNaN ? fbits(M5ccInit.floatDivision) : 0;
    }

    private static long constructorDoubleBits(int ah, int al, int bh, int bl) {
        M5ccFeatureCarrier value = new M5ccFeatureCarrier(
                0.0f, 0.0f, asDouble(ah, al), asDouble(bh, bl));
        return dbits(value.constructedDouble);
    }

    public static int constructorDoubleHigh(int ah, int al, int bh, int bl) {
        return (int) (constructorDoubleBits(ah, al, bh, bl) >>> 32);
    }

    public static int constructorDoubleLow(int ah, int al, int bh, int bl) {
        return (int) constructorDoubleBits(ah, al, bh, bl);
    }

    private static long defaultDoubleBits(int ah, int al, int bh, int bl) {
        M5ccDoubleDefault worker = new M5ccFeatureCarrier(0.0f, 0.0f, 0.0d, 0.0d);
        return dbits(worker.remainder(asDouble(ah, al), asDouble(bh, bl)));
    }

    public static int defaultDoubleHigh(int ah, int al, int bh, int bl) {
        return (int) (defaultDoubleBits(ah, al, bh, bl) >>> 32);
    }

    public static int defaultDoubleLow(int ah, int al, int bh, int bl) {
        return (int) defaultDoubleBits(ah, al, bh, bl);
    }

    private static long postIncrementDoubleBits(int high, int low) {
        M5ccFeatureCarrier value = new M5ccFeatureCarrier(0.0f, 0.0f, 0.0d, 0.0d);
        value.doubleField = asDouble(high, low);
        value.doubleField++;
        return dbits(value.doubleField);
    }

    public static int instanceDoublePostIncrementHigh(int high, int low) {
        return (int) (postIncrementDoubleBits(high, low) >>> 32);
    }

    public static int instanceDoublePostIncrementLow(int high, int low) {
        return (int) postIncrementDoubleBits(high, low);
    }

    private static long strictDoubleBits(int ah, int al, int bh, int bl) {
        return dbits(M5ccStrictWorker.multiply(asDouble(ah, al), asDouble(bh, bl)));
    }

    public static int strictDoubleMultiplyHigh(int ah, int al, int bh, int bl) {
        return (int) (strictDoubleBits(ah, al, bh, bl) >>> 32);
    }

    public static int strictDoubleMultiplyLow(int ah, int al, int bh, int bl) {
        return (int) strictDoubleBits(ah, al, bh, bl);
    }
}
