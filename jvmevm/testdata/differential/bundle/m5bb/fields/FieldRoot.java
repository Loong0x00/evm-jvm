package bundle.m5bb.fields;

public class FieldRoot {
    private static int fold(long value) {
        return (int) (value ^ (value >>> 32));
    }

    public static int staticPreparedNull(int seed) {
        return ArrayFields.mutable == null ? seed + 101 : seed + 202;
    }

    public static int staticWrite(int seed) {
        ArrayFields.mutable = new long[] { 0x123456789abcdef0L, seed };
        return fold(ArrayFields.mutable[0]) + fold(ArrayFields.mutable[1]);
    }

    public static int staticReplace(int seed) {
        ArrayFields.mutable = new long[] { seed };
        long[] old = ArrayFields.mutable;
        ArrayFields.mutable = new long[] { ((long) seed << 32) };
        return fold(old[0]) * 31 + fold(ArrayFields.mutable[0]);
    }

    public static int instanceDefault(int seed) {
        ArrayFields fields = new ArrayFields();
        return fields.values == null ? seed + 303 : seed + 404;
    }

    public static int instanceWrite(int seed) {
        ArrayFields fields = new ArrayFields();
        fields.values = new long[] { Long.MIN_VALUE, seed };
        return fold(fields.values[0] + fields.values[1]);
    }

    public static int finalConstructor(int seed) {
        FinalArray holder = new FinalArray(new long[] { 0x700000008L, seed });
        return fold(holder.values[0] + holder.values[1]);
    }

    public static int finalElementMutation(int seed) {
        FinalArray holder = new FinalArray(new long[] { seed });
        holder.values[0] += 0x100000001L;
        return fold(holder.values[0]);
    }

    public static int staticFinalElementMutation(int seed) {
        StaticFinalArray.values[0] += seed;
        return fold(StaticFinalArray.values[0]);
    }

    public static int initializedArray(int seed) {
        return fold(InitializedArray.values[0] + InitializedArray.values[1]) + seed;
    }

    public static int initializerOnce(int seed) {
        long[] first = InitializedArray.values;
        long[] second = InitializedArray.values;
        return (first == second ? 500 : 700) + InitializedArray.runs + seed;
    }

    public static int reentrantPreparedNull(int seed) {
        return ReentrantArray.sawNull * 1000 + fold(ReentrantArray.values[0]) + seed;
    }

    public static int inheritedOwner(int seed) {
        InheritedChild.values[0] = ((long) seed << 32) | (seed & 0xffffffffL);
        return fold(InheritedBase.values[0]) + (InheritedChild.values == InheritedBase.values ? 17 : 29);
    }

    public static int hiddenFields(int seed) {
        HiddenBase.values[0] = seed;
        HiddenChild.values[0] = ((long) seed << 40);
        return fold(HiddenBase.values[0]) * 31 + fold(HiddenChild.values[0]);
    }

    public static int interfaceFinalMutation(int seed) {
        ArrayFieldFace.values[0] += seed;
        return fold(ArrayFieldFace.values[0]);
    }
}

class ArrayFields {
    static long[] mutable;
    long[] values;
}

class FinalArray {
    final long[] values;

    FinalArray(long[] values) {
        this.values = values;
    }
}

class StaticFinalArray {
    static final long[] values = new long[] { 0x123456789abcdef0L };
}

class InitializedArray {
    static int runs;
    static final long[] values = make();

    static long[] make() {
        runs++;
        return new long[] { Long.MIN_VALUE, 0x7fffffff00000001L };
    }
}

class ReentrantArray {
    static int sawNull;
    static long[] values = make();

    static long[] make() {
        if (values == null) {
            sawNull = 1;
        }
        return new long[] { 0x1122334455667788L };
    }
}

class InheritedBase {
    static long[] values = new long[1];
}

class InheritedChild extends InheritedBase {
}

class HiddenBase {
    static long[] values = new long[1];
}

class HiddenChild extends HiddenBase {
    static long[] values = new long[1];
}

interface ArrayFieldFace {
    long[] values = ArrayFieldMaker.make();
}

class ArrayFieldMaker {
    static long[] make() {
        return new long[] { 0xfedcba9876543210L };
    }
}
