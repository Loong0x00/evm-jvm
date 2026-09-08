package bundle.m5bb.calls;

public class CallRoot {
    private static int fold(long value) {
        return (int) (value ^ (value >>> 32));
    }

    private static long[] privateSpecial(long[] values, long scalar, int index) {
        values[index] ^= scalar;
        return values;
    }

    public static int staticCall(int seed) {
        long[] values = CallHelpers.make(seed);
        return fold(CallHelpers.staticMixed(0x1234567887654321L, values, seed));
    }

    public static int privateSpecialCall(int seed) {
        CallRoot root = new CallRoot();
        long[] values = new long[] { 0x7fffffff00000000L, seed };
        return fold(root.privateSpecial(values, 0x80000000ffffffffL, 1)[1]);
    }

    public static int virtualBase(int seed) {
        CallBase base = new CallBase();
        return fold(base.mixed(0x100000002L, new long[] { seed, -seed }, 3));
    }

    public static int virtualOverride(int seed) {
        CallBase base = new CallChild();
        return fold(base.mixed(0x100000002L, new long[] { seed, -seed }, 3));
    }

    public static int interfaceBase(int seed) {
        ArrayCallFace face = new CallBase();
        return fold(face.mixed(0x700000008L, new long[] { seed, Long.MIN_VALUE }, 5));
    }

    public static int interfaceOverride(int seed) {
        ArrayCallFace face = new CallChild();
        return fold(face.mixed(0x700000008L, new long[] { seed, Long.MAX_VALUE }, 5));
    }

    public static int defaultCall(int seed) {
        ArrayCallFace face = new DefaultOnly();
        long[] values = face.defaultBump(new long[] { 0x123456789abcdef0L, seed }, 0x100000001L);
        return fold(values[0]) * 31 + fold(values[1]);
    }

    public static int interfaceDefaultSite(int seed) {
        ArrayCallFace face = new DefaultOnly();
        return fold(face.defaultDigest(new long[] { seed }, 0x8000000000000001L));
    }

    public static int directInterfaceSuper(int seed) {
        DirectDefault call = new DirectDefault();
        return fold(call.direct(new long[] { seed, 9L }, 0x200000003L));
    }

    public static int interfaceStatic(int seed) {
        long[] input = new long[] { seed, Long.MIN_VALUE };
        long[] values = ArrayCallFace.staticArray(0x1234567887654321L, input, seed);
        return fold(values[0]) * 31 + fold(values[1]);
    }

    public static int constructorArguments(int seed) {
        ArrayConstructed value = new ArrayConstructed(
            new long[] { 0x123456789abcdef0L, seed }, 0x700000008L, seed + 1);
        return fold(value.value);
    }

    public static int constructorChain(int seed) {
        ArrayConstructedChild value = new ArrayConstructedChild(
            new long[] { Long.MIN_VALUE, seed }, 0x100000001L, seed + 2);
        return fold(value.value);
    }

    public static int arrayReturnTransport(int seed) {
        long[] input = new long[] { 0x1111111122222222L, seed };
        long[] output = CallHelpers.bounce(input);
        output[0] += output[1];
        return fold(output[0]) + (input == output ? 100 : 200);
    }

    public static int mixedArgumentOrder(int seed) {
        long[] values = new long[] { seed, 0x3333333344444444L };
        long[] output = CallHelpers.order(seed, 0x5555555566666666L, values, seed + 7);
        return fold(output[0]) * 31 + fold(output[1]);
    }

    public static int voidMutation(int seed) {
        long[] values = new long[] { seed, Long.MAX_VALUE };
        CallHelpers.mutate(values, 1, 0x100000001L);
        return fold(values[1]);
    }

    public static int arrayIdentityAcrossInterface(int seed) {
        ArrayCallFace face = new CallBase();
        long[] values = new long[] { seed };
        return face.bounce(values) == values ? seed + 701 : seed + 907;
    }
}

interface ArrayCallFace {
    long mixed(long scalar, long[] values, int bias);
    long[] bounce(long[] values);

    default long[] defaultBump(long[] values, long delta) {
        values[0] += delta;
        return values;
    }

    default long defaultDigest(long[] values, long delta) {
        return defaultBump(values, delta)[0];
    }

    static long[] staticArray(long scalar, long[] values, int seed) {
        values[0] += scalar;
        values[1] ^= seed;
        return values;
    }
}

class CallBase implements ArrayCallFace {
    public long mixed(long scalar, long[] values, int bias) {
        return scalar + values[0] - values[1] + bias;
    }

    public long[] bounce(long[] values) {
        return values;
    }
}

class CallChild extends CallBase {
    public long mixed(long scalar, long[] values, int bias) {
        return scalar ^ values[0] ^ values[1] ^ bias;
    }
}

class DefaultOnly implements ArrayCallFace {
    public long mixed(long scalar, long[] values, int bias) {
        return scalar + values[0] + bias;
    }

    public long[] bounce(long[] values) {
        return values;
    }
}

class DirectDefault implements ArrayCallFace {
    public long mixed(long scalar, long[] values, int bias) {
        return scalar - values[0] + bias;
    }

    public long[] bounce(long[] values) {
        return values;
    }

    long direct(long[] values, long delta) {
        return ArrayCallFace.super.defaultDigest(values, delta);
    }
}

class CallHelpers {
    static long[] make(int seed) {
        return new long[] { ((long) seed << 40) ^ 0x00000000fedcba98L, -seed };
    }

    static long staticMixed(long scalar, long[] values, int bias) {
        return scalar + values[0] * 3L + values[1] + bias;
    }

    static long[] bounce(long[] values) {
        return values;
    }

    static long[] order(int prefix, long scalar, long[] values, int suffix) {
        values[0] += scalar + prefix;
        values[1] ^= suffix;
        return values;
    }

    static void mutate(long[] values, int index, long delta) {
        values[index] += delta;
    }
}

class ArrayConstructed {
    final long value;

    ArrayConstructed(long[] values, long scalar, int bias) {
        value = values[0] + values[1] + scalar + bias;
    }
}

class ArrayConstructedChild extends ArrayConstructed {
    ArrayConstructedChild(long[] values, long scalar, int bias) {
        super(values, scalar, bias);
        values[0] ^= value;
    }
}
