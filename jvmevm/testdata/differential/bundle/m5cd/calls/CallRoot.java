package bundle.m5cd.calls;

public strictfp class CallRoot {
    private static long join(int high, int low) {
        return ((long) high << 32) | (low & 0xffffffffL);
    }

    private static float f(int bits) { return Float.intBitsToFloat(bits); }
    private static double d(int high, int low) { return Double.longBitsToDouble(join(high, low)); }
    private static int fr(float value) { return Float.floatToRawIntBits(value); }
    private static long dr(double value) { return Double.doubleToRawLongBits(value); }
    private static int fa(float value) { return value != value ? 0x7fc00000 : fr(value); }
    private static long da(double value) { return value != value ? 0x7ff8000000000000L : dr(value); }

    private double[] privateSpecial(double[] values) {
        return values;
    }

    public static int staticFloatTransport(int bits) {
        return fr(CallHelper.floatBounce(new float[] { f(bits) })[0]);
    }

    private static long privateDoubleBits(int high, int low) {
        double[] values = new CallRoot().privateSpecial(new double[] { d(high, low) });
        return dr(values[0]);
    }

    public static int privateDoubleHigh(int high, int low) {
        return (int) (privateDoubleBits(high, low) >>> 32);
    }

    public static int privateDoubleLow(int high, int low) {
        return (int) privateDoubleBits(high, low);
    }

    public static int virtualFloatAdd(int left, int right) {
        FpCallBase call = new FpCallChild();
        return fa(call.floatOperation(new float[] { f(left) }, f(right)));
    }

    private static long interfaceDoubleBits(int ah, int al, int bh, int bl) {
        FpArrayCalls call = new FpCallChild();
        return da(call.doubleOperation(new double[] { d(ah, al) }, d(bh, bl)));
    }

    public static int interfaceDoubleHigh(int ah, int al, int bh, int bl) {
        return (int) (interfaceDoubleBits(ah, al, bh, bl) >>> 32);
    }

    public static int interfaceDoubleLow(int ah, int al, int bh, int bl) {
        return (int) interfaceDoubleBits(ah, al, bh, bl);
    }

    public static int defaultFloatMultiply(int left, int right) {
        FpArrayCalls call = new DefaultCalls();
        return fa(call.defaultFloat(new float[] { f(left) }, f(right)));
    }

    public static int directInterfaceSuperFloat(int left, int right) {
        return fa(new DirectCalls().direct(new float[] { f(left) }, f(right)));
    }

    private static long interfaceStaticBits(int high, int low) {
        return dr(FpArrayCalls.staticDouble(new double[] { d(high, low) })[0]);
    }

    public static int interfaceStaticDoubleHigh(int high, int low) {
        return (int) (interfaceStaticBits(high, low) >>> 32);
    }

    public static int interfaceStaticDoubleLow(int high, int low) {
        return (int) interfaceStaticBits(high, low);
    }

    public static int constructorFloat(int bits) {
        ConstructedArrays value = new ConstructedArrays(new float[] { f(bits) }, new double[1]);
        return fr(value.floats[0]);
    }

    private static long constructorDoubleBits(int high, int low) {
        ConstructedChild value = new ConstructedChild(new float[1], new double[] { d(high, low) });
        return dr(value.doubles[0]);
    }

    public static int constructorDoubleHigh(int high, int low) {
        return (int) (constructorDoubleBits(high, low) >>> 32);
    }

    public static int constructorDoubleLow(int high, int low) {
        return (int) constructorDoubleBits(high, low);
    }

    public static int floatReturnIdentity(int bits) {
        float[] values = new float[] { f(bits) };
        float[] result = CallHelper.floatBounce(values);
        return fr(result[0]) ^ (result == values ? 0 : 1);
    }

    private static long doubleReturnBits(int high, int low) {
        double[] values = new double[] { d(high, low) };
        double[] result = CallHelper.doubleBounce(values);
        return dr(result[0]) ^ (result == values ? 0L : 1L);
    }

    public static int doubleReturnHigh(int high, int low) {
        return (int) (doubleReturnBits(high, low) >>> 32);
    }

    public static int doubleReturnLow(int high, int low) {
        return (int) doubleReturnBits(high, low);
    }

    private static long mixedBits(int prefix, int ah, int al, int bh, int bl, int suffix) {
        double[] values = new double[] { d(ah, al) };
        return da(CallHelper.mixed(prefix, values, d(bh, bl), suffix));
    }

    public static int mixedCategoryHigh(int prefix, int ah, int al, int bh, int bl, int suffix) {
        return (int) (mixedBits(prefix, ah, al, bh, bl, suffix) >>> 32);
    }

    public static int mixedCategoryLow(int prefix, int ah, int al, int bh, int bl, int suffix) {
        return (int) mixedBits(prefix, ah, al, bh, bl, suffix);
    }
}

interface FpArrayCalls {
    float floatOperation(float[] values, float scalar);
    double doubleOperation(double[] values, double scalar);

    default float defaultFloat(float[] values, float scalar) {
        return values[0] * scalar;
    }

    static double[] staticDouble(double[] values) {
        return values;
    }
}

class FpCallBase implements FpArrayCalls {
    public float floatOperation(float[] values, float scalar) {
        return values[0] - scalar;
    }

    public double doubleOperation(double[] values, double scalar) {
        return values[0] - scalar;
    }
}

class FpCallChild extends FpCallBase {
    public float floatOperation(float[] values, float scalar) {
        return values[0] + scalar;
    }

    public double doubleOperation(double[] values, double scalar) {
        return values[0] + scalar;
    }
}

class DefaultCalls implements FpArrayCalls {
    public float floatOperation(float[] values, float scalar) { return values[0]; }
    public double doubleOperation(double[] values, double scalar) { return values[0]; }
}

class DirectCalls implements FpArrayCalls {
    public float floatOperation(float[] values, float scalar) { return values[0]; }
    public double doubleOperation(double[] values, double scalar) { return values[0]; }

    float direct(float[] values, float scalar) {
        return FpArrayCalls.super.defaultFloat(values, scalar);
    }
}

class CallHelper {
    static float[] floatBounce(float[] values) { return values; }
    static double[] doubleBounce(double[] values) { return values; }

    static double mixed(int prefix, double[] values, double scalar, int suffix) {
        return values[0] + scalar + prefix - suffix;
    }
}

class ConstructedArrays {
    final float[] floats;
    final double[] doubles;

    ConstructedArrays(float[] floats, double[] doubles) {
        this.floats = floats;
        this.doubles = doubles;
    }
}

class ConstructedChild extends ConstructedArrays {
    ConstructedChild(float[] floats, double[] doubles) {
        super(floats, doubles);
    }
}
