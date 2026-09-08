package bundle.m5cd.fields;

public strictfp class FieldRoot {
    private static long join(int high, int low) {
        return ((long) high << 32) | (low & 0xffffffffL);
    }

    private static float f(int bits) { return Float.intBitsToFloat(bits); }
    private static double d(int high, int low) { return Double.longBitsToDouble(join(high, low)); }
    private static int fr(float value) { return Float.floatToRawIntBits(value); }
    private static long dr(double value) { return Double.doubleToRawLongBits(value); }
    private static int fa(float value) { return value != value ? 0x7fc00000 : fr(value); }
    private static long da(double value) { return value != value ? 0x7ff8000000000000L : dr(value); }

    public static int staticPreparedNull(int seed) {
        return ArrayFields.floats == null && ArrayFields.doubles == null ? seed + 101 : seed + 202;
    }

    public static int staticFloatWrite(int bits) {
        ArrayFields.floats = new float[] { f(bits) };
        return fr(ArrayFields.floats[0]);
    }

    private static long staticDoubleWriteBits(int high, int low) {
        ArrayFields.doubles = new double[] { d(high, low) };
        return dr(ArrayFields.doubles[0]);
    }

    public static int staticDoubleWriteHigh(int high, int low) {
        return (int) (staticDoubleWriteBits(high, low) >>> 32);
    }

    public static int staticDoubleWriteLow(int high, int low) {
        return (int) staticDoubleWriteBits(high, low);
    }

    public static int instanceFloatField(int bits) {
        ArrayFields fields = new ArrayFields();
        fields.floatValues = new float[] { f(bits) };
        return fr(fields.floatValues[0]);
    }

    private static long instanceDoubleFieldBits(int high, int low) {
        ArrayFields fields = new ArrayFields();
        fields.doubleValues = new double[] { d(high, low) };
        return dr(fields.doubleValues[0]);
    }

    public static int instanceDoubleFieldHigh(int high, int low) {
        return (int) (instanceDoubleFieldBits(high, low) >>> 32);
    }

    public static int instanceDoubleFieldLow(int high, int low) {
        return (int) instanceDoubleFieldBits(high, low);
    }

    public static int finalFloatElementMutation(int bits) {
        FinalArrays values = new FinalArrays(new float[] { f(bits) }, new double[1]);
        values.floats[0] = -values.floats[0];
        return fr(values.floats[0]);
    }

    private static long finalDoubleElementBits(int high, int low) {
        FinalArrays values = new FinalArrays(new float[1], new double[] { d(high, low) });
        values.doubles[0] = -values.doubles[0];
        return dr(values.doubles[0]);
    }

    public static int finalDoubleElementHigh(int high, int low) {
        return (int) (finalDoubleElementBits(high, low) >>> 32);
    }

    public static int finalDoubleElementLow(int high, int low) {
        return (int) finalDoubleElementBits(high, low);
    }

    public static int staticFinalFloatCompound(int bits) {
        StaticFinalArrays.floats[0] += f(bits);
        return fa(StaticFinalArrays.floats[0]);
    }

    public static int initializedFloatPayload(int ignored) {
        return fr(InitializedArrays.floats[0]);
    }

    private static long initializedDoublePayloadBits() {
        return dr(InitializedArrays.doubles[0]);
    }

    public static int initializedDoublePayloadHigh(int ignored) {
        return (int) (initializedDoublePayloadBits() >>> 32);
    }

    public static int initializedDoublePayloadLow(int ignored) {
        return (int) initializedDoublePayloadBits();
    }

    public static int reentrantPreparedNull(int seed) {
        return ReentrantArrays.sawNull * 1000 + fr(ReentrantArrays.floats[0]) + seed;
    }

    private static long interfaceDoubleBits() {
        return dr(ArrayFieldFace.doubles[0]);
    }

    public static int interfaceDoubleHigh(int ignored) {
        return (int) (interfaceDoubleBits() >>> 32);
    }

    public static int interfaceDoubleLow(int ignored) {
        return (int) interfaceDoubleBits();
    }

    public static int inheritedFloatField(int bits) {
        InheritedChild.floats[0] = f(bits);
        return fr(InheritedBase.floats[0]);
    }

    private static long hiddenDoubleBits(int high, int low) {
        HiddenBase.doubles[0] = d(high, low);
        HiddenChild.doubles[0] = -d(high, low);
        return dr(HiddenBase.doubles[0]) ^ dr(HiddenChild.doubles[0]);
    }

    public static int hiddenDoubleHigh(int high, int low) {
        return (int) (hiddenDoubleBits(high, low) >>> 32);
    }

    public static int hiddenDoubleLow(int high, int low) {
        return (int) hiddenDoubleBits(high, low);
    }

    public static int initializedArithmeticFloat(int ignored) {
        return fa(ArithmeticArrays.floats[0]);
    }

    private static long initializedArithmeticDoubleBits() {
        return da(ArithmeticArrays.doubles[0]);
    }

    public static int initializedArithmeticDoubleHigh(int ignored) {
        return (int) (initializedArithmeticDoubleBits() >>> 32);
    }

    public static int initializedArithmeticDoubleLow(int ignored) {
        return (int) initializedArithmeticDoubleBits();
    }
}

class ArrayFields {
    static float[] floats;
    static double[] doubles;
    float[] floatValues;
    double[] doubleValues;
}

class FinalArrays {
    final float[] floats;
    final double[] doubles;

    FinalArrays(float[] floats, double[] doubles) {
        this.floats = floats;
        this.doubles = doubles;
    }
}

class StaticFinalArrays {
    static final float[] floats = new float[] { 1.0f };
}

class InitializedArrays {
    static final float[] floats = makeFloats();
    static final double[] doubles = makeDoubles();

    static float[] makeFloats() {
        return new float[] { Float.intBitsToFloat(0x7fc12345) };
    }

    static double[] makeDoubles() {
        return new double[] { Double.longBitsToDouble(0x7ff8123456789abcL) };
    }
}

class ReentrantArrays {
    static int sawNull;
    static float[] floats = make();

    static float[] make() {
        if (floats == null) sawNull = 1;
        return new float[] { Float.intBitsToFloat(0x80000000) };
    }
}

class InheritedBase {
    static float[] floats = new float[1];
}

class InheritedChild extends InheritedBase {
}

class HiddenBase {
    static double[] doubles = new double[1];
}

class HiddenChild extends HiddenBase {
    static double[] doubles = new double[1];
}

interface ArrayFieldFace {
    double[] doubles = ArrayFieldMaker.make();
}

class ArrayFieldMaker {
    static double[] make() {
        return new double[] { Double.longBitsToDouble(0xfff8123456789abcL) };
    }
}

class ArithmeticArrays {
    static final float[] floats = makeFloats();
    static final double[] doubles = makeDoubles();

    static float sourceFloat(int bits) { return Float.intBitsToFloat(bits); }
    static double sourceDouble(long bits) { return Double.longBitsToDouble(bits); }

    static float[] makeFloats() {
        return new float[] { sourceFloat(0x00000000) / sourceFloat(0x00000000) };
    }

    static double[] makeDoubles() {
        return new double[] { sourceDouble(0x3ff0000000000000L) / sourceDouble(0x8000000000000000L) };
    }
}
