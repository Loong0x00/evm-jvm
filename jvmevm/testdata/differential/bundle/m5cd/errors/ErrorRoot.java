package bundle.m5cd.errors;

public strictfp class ErrorRoot {
    private static int trace;
    private static float[] tracedArray;

    private static long join(int high, int low) {
        return ((long) high << 32) | (low & 0xffffffffL);
    }

    private static float f(int bits) { return Float.intBitsToFloat(bits); }
    private static double d(int high, int low) { return Double.longBitsToDouble(join(high, low)); }
    private static int fr(float value) { return Float.floatToRawIntBits(value); }

    public static int nullFloatRead(int index) {
        float[] values = null;
        return fr(values[index]);
    }

    public static int nullFloatWrite(int index, int bits) {
        float[] values = null;
        values[index] = f(bits);
        return bits;
    }

    public static int nullDoubleRead(int index) {
        double[] values = null;
        return (int) Double.doubleToRawLongBits(values[index]);
    }

    public static int nullDoubleWrite(int index, int high, int low) {
        double[] values = null;
        values[index] = d(high, low);
        return low;
    }

    public static int boundsFloatRead(int index) {
        return fr((new float[2])[index]);
    }

    public static int boundsFloatWrite(int index, int bits) {
        float[] values = new float[2];
        values[index] = f(bits);
        return bits;
    }

    public static int boundsDoubleRead(int index) {
        return (int) Double.doubleToRawLongBits((new double[2])[index]);
    }

    public static int boundsDoubleWrite(int index, int high, int low) {
        double[] values = new double[2];
        values[index] = d(high, low);
        return low;
    }

    public static int negativeFloatLength(int length) {
        return new float[length].length;
    }

    public static int negativeDoubleLength(int length) {
        return new double[length].length;
    }

    public static int integerFailureBeforeNullFloat(int numerator, int denominator) {
        float[] values = null;
        values[-1] = numerator / denominator;
        return numerator;
    }

    public static int integerFailureBeforeNullDouble(int numerator, int denominator) {
        double[] values = null;
        values[99] = numerator / denominator;
        return numerator;
    }

    public static int fpValueThenNullFloat(int left, int right) {
        float[] values = null;
        values[-1] = f(left) / f(right);
        return left;
    }

    public static int fpValueThenNullDouble(int ah, int al, int bh, int bl) {
        double[] values = null;
        values[99] = d(ah, al) / d(bh, bl);
        return al;
    }

    private static float[] arrayExpression() {
        trace = trace * 10 + 1;
        return tracedArray;
    }

    private static int indexExpression(int index) {
        trace = trace * 10 + 2;
        return index;
    }

    private static float valueExpression(int bits) {
        trace = trace * 10 + 3;
        return f(bits);
    }

    public static int storeLeftToRight(int bits) {
        trace = 0;
        tracedArray = new float[1];
        arrayExpression()[indexExpression(0)] = valueExpression(bits);
        return trace * 100000 + (fr(tracedArray[0]) & 0xffff);
    }

    public static int compoundArrayEvaluatedOnce(int bits) {
        trace = 0;
        tracedArray = new float[] { f(bits) };
        arrayExpression()[0] += 1.0f;
        return trace * 100000 + (fr(tracedArray[0]) & 0xffff);
    }

    public static int initializerArithmeticFailure(int seed) {
        return fr(FailingArithmeticInit.values[0]) + seed;
    }

    public static int initializerNegativeFailure(int seed) {
        return FailingNegativeInit.values.length + seed;
    }
}

class FailingArithmeticInit {
    static float[] values = make();

    static float[] make() {
        float[] target = null;
        int zero = 0;
        target[-1] = 1 / zero;
        return target;
    }
}

class FailingNegativeInit {
    static double[] values = make();

    static double[] make() {
        int negative = -1;
        return new double[negative];
    }
}
