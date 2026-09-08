package bundle.m5ba.fields;

/** Scalar long static/instance/interface/final/hidden fields and ConstantValue declarations. */
public class FieldRoot {
    private static int fold(long value) { return (int) (value ^ (value >>> 32)); }

    public static int staticDefault(int salt) { return fold(LongFields.STATIC) + salt; }
    public static int staticWrite(int value) {
        LongFields.STATIC = ((long) value << 40) | ((long) value & 0xffffffffL);
        return fold(LongFields.STATIC);
    }
    public static int staticPostIncrement(int value) {
        LongFields.STATIC = ((long) value << 32) | ((long) value & 0xffffffffL);
        long old = LongFields.STATIC++;
        return fold(old) ^ fold(LongFields.STATIC);
    }
    public static int staticCompound(int value) {
        LongFields.STATIC = 0x7000000000000000L | ((long) value & 0xffffffffL);
        LongFields.STATIC += 0x2000000000000001L;
        LongFields.STATIC ^= 0x0102030405060708L;
        return fold(LongFields.STATIC);
    }
    public static int staticAssignmentExpression(int value) {
        long observed = (LongFields.STATIC = ((long) value << 33) + 7L);
        return fold(observed) ^ fold(LongFields.STATIC);
    }

    public static int instanceDefault(int salt) { return fold(new LongFields().value) + salt; }
    public static int instanceWrite(int value) {
        LongFields fields = new LongFields();
        fields.value = ((long) value << 37) | 0x12345678L;
        return fold(fields.value);
    }
    public static int instancePostIncrement(int value) {
        LongFields fields = new LongFields();
        fields.value = ((long) value << 32) | 0xffffffffL;
        long old = fields.value++;
        return fold(old) ^ fold(fields.value);
    }
    public static int instanceAssignmentExpression(int value) {
        LongFields fields = new LongFields();
        long observed = (fields.value = ((long) value << 41) - 9L);
        return fold(observed) + fold(fields.value);
    }
    public static int chainedInstanceAssignment(int value) {
        LongFields left = new LongFields();
        LongFields right = new LongFields();
        long observed = (left.value = right.value = ((long) value << 39) + 11L);
        return fold(observed) ^ fold(left.value) ^ fold(right.value);
    }

    public static int finalConstructor(int value) {
        FinalLong made = new FinalLong(((long) value << 32) | ((long) ~value & 0xffffffffL));
        return fold(made.value);
    }
    public static int hiddenStatic(int value) {
        HiddenBase.VALUE = ((long) value << 32) | 1L;
        HiddenChild.VALUE = ((long) value << 32) | 2L;
        return fold(HiddenBase.VALUE) * 31 + fold(HiddenChild.VALUE);
    }
    public static int hiddenInstance(int value) {
        HiddenChild child = new HiddenChild(((long) value << 32) | 3L, ((long) value << 32) | 4L);
        return fold(child.parentValue()) * 31 + fold(child.VALUE);
    }
    public static int classConstant(int salt) { return fold(LongConstants.BOUNDARY) ^ fold(LongConstants.PATTERN) ^ salt; }
    public static int interfaceConstant(int salt) { return fold(LongConstantFace.MINIMUM) ^ fold(LongConstantFace.BIT32) ^ salt; }
    public static int interfaceDynamic(int value) { return fold(DynamicLongFace.VALUE) + FieldTrace.trace * 1000 + value; }
    public static int interfaceHidden(int value) {
        return fold(HiddenLongParent.VALUE) * 31 + fold(HiddenLongChild.VALUE) + FieldTrace.trace * 1000 + value;
    }
    public static int inheritedOwnerThroughChild(int value) {
        return fold(InheritedLongChild.VALUE) + FieldTrace.trace * 1000 + value;
    }
}

class LongFields { static long STATIC; long value; }
class FinalLong { final long value; FinalLong(long value) { this.value = value; } }
class HiddenBase { static long VALUE; long value; HiddenBase(long value) { this.value = value; } }
class HiddenChild extends HiddenBase {
    static long VALUE;
    long value;
    HiddenChild(long parent, long child) { super(parent); value = child; }
    long parentValue() { return super.value; }
}
class LongConstants {
    static final long BOUNDARY = 0x0000000100000000L;
    static final long PATTERN = 0x76543210fedcba98L;
}
interface LongConstantFace {
    long MINIMUM = 0x8000000000000000L;
    long BIT32 = 0x0000000100000000L;
}
class FieldTrace {
    static int trace;
    static long mark(int digit, long value) { trace = trace * 10 + digit; return value; }
}
interface DynamicLongFace { long VALUE = FieldTrace.mark(1, 0x1234567887654321L); }
interface HiddenLongParent { long VALUE = FieldTrace.mark(2, 0x2222222211111111L); }
interface HiddenLongChild extends HiddenLongParent { long VALUE = FieldTrace.mark(3, 0x3333333311111111L); }
class InheritedLongBase { static long VALUE = FieldTrace.mark(4, 0x4444444411111111L); }
class InheritedLongChild extends InheritedLongBase {}
