package bundle.m5cc.scalar;

/** Bit-exact binary32 arithmetic roots. Operands always arrive as raw int bits. */
public strictfp class FloatArithmeticRoot {
    private static float value(int bits) {
        return Float.intBitsToFloat(bits);
    }

    private static int result(float value) {
        // Generated NaNs have an implementation-dependent payload on reference
        // JVMs. Only arithmetic NaNs are normalized; every non-NaN raw bit is exact.
        return value != value ? 0x7fc00000 : Float.floatToRawIntBits(value);
    }

    public static int add(int leftBits, int rightBits) {
        float left = value(leftBits);
        float right = value(rightBits);
        return result(left + right);
    }

    public static int subtract(int leftBits, int rightBits) {
        float left = value(leftBits);
        float right = value(rightBits);
        return result(left - right);
    }

    public static int multiply(int leftBits, int rightBits) {
        float left = value(leftBits);
        float right = value(rightBits);
        return result(left * right);
    }

    public static int divide(int leftBits, int rightBits) {
        float left = value(leftBits);
        float right = value(rightBits);
        return result(left / right);
    }

    public static int remainder(int leftBits, int rightBits) {
        float left = value(leftBits);
        float right = value(rightBits);
        return result(left % right);
    }

    /** Fixed performance gate: sixteen operations on the same original operands. */
    public static int remainder16(int leftBits, int rightBits) {
        float left = value(leftBits);
        float right = value(rightBits);
        float remainder = 0.0f;
        for (int i = 0; i < 16; i++) remainder = left % right;
        return result(remainder);
    }
}
