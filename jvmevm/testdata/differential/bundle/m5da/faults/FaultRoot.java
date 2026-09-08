package bundle.m5da.faults;

/** Source-reachable implicit faults caught by exact and canonical super types. */
public final class FaultRoot {
    interface ValueFace { int get(); }
    static class Base implements ValueFace { int value; public int get() { return value; } }
    static final class Child extends Base { }

    private int privateValue() { return 1; }
    private static int divide(int value) { return 100 / value; }
    private static int remainder(int value) { return 100 % value; }
    private static int nullArray() { int[] value = null; return value.length; }
    private static int nullField() { Base value = null; return value.value; }
    private static int badIndex(int index) { return (new int[1])[index]; }
    private static int badStore() { Base[] values = new Child[1]; values[0] = new Base(); return 0; }
    private static int badCast() { Base value = new Base(); return ((Child) value).value; }
    private static int badSize(int size) { return new int[size].length; }
    private static int badRefSize(int size) { return new Base[size].length; }
    private static int badMultiSize(int size) { return new int[1][size].length; }

    public static int arithmeticExact(int value) {
        try { return divide(value); } catch (ArithmeticException e) { return 101; }
    }
    public static int remainderExact(int value) {
        try { return remainder(value); } catch (ArithmeticException e) { return 102; }
    }
    public static int arithmeticRuntime(int value) {
        try { return divide(value); } catch (RuntimeException e) { return 103; }
    }
    public static int arithmeticException(int value) {
        try { return divide(value); } catch (Exception e) { return 104; }
    }
    public static int arithmeticThrowable(int value) {
        try { return divide(value); } catch (Throwable e) { return 105; }
    }
    public static int nullArrayExact(int seed) {
        try { return nullArray(); } catch (NullPointerException e) { return seed + 106; }
    }
    public static int nullFieldRuntime(int seed) {
        try { return nullField(); } catch (RuntimeException e) { return seed + 107; }
    }
    public static int boundsExact(int index) {
        try { return badIndex(index); } catch (ArrayIndexOutOfBoundsException e) { return 108; }
    }
    public static int boundsIndexSuper(int index) {
        try { return badIndex(index); } catch (IndexOutOfBoundsException e) { return 109; }
    }
    public static int boundsRuntime(int index) {
        try { return badIndex(index); } catch (RuntimeException e) { return 110; }
    }
    public static int storeExact(int seed) {
        try { return badStore(); } catch (ArrayStoreException e) { return seed + 111; }
    }
    public static int storeException(int seed) {
        try { return badStore(); } catch (Exception e) { return seed + 112; }
    }
    public static int castExact(int seed) {
        try { return badCast(); } catch (ClassCastException e) { return seed + 113; }
    }
    public static int castThrowable(int seed) {
        try { return badCast(); } catch (Throwable e) { return seed + 114; }
    }
    public static int negativeExact(int size) {
        try { return badSize(size); } catch (NegativeArraySizeException e) { return 115; }
    }
    public static int negativeRefRuntime(int size) {
        try { return badRefSize(size); } catch (RuntimeException e) { return 116; }
    }
    public static int negativeMultiException(int size) {
        try { return badMultiSize(size); } catch (Exception e) { return 117; }
    }

    public static int longDivideExact(int seed) {
        long zero = 0L;
        try { return (int) (100L / zero); } catch (ArithmeticException e) { return seed + 118; }
    }
    public static int longRemainderExact(int seed) {
        long zero = 0L;
        try { return (int) (100L % zero); } catch (ArithmeticException e) { return seed + 119; }
    }
    public static int nullArrayLoad(int seed) {
        int[] value = null;
        try { return value[0]; } catch (NullPointerException e) { return seed + 120; }
    }
    public static int nullArrayStore(int seed) {
        int[] value = null;
        try { value[0] = seed; return -1; } catch (NullPointerException e) { return seed + 121; }
    }
    public static int nullPutField(int seed) {
        Base value = null;
        try { value.value = seed; return -1; } catch (NullPointerException e) { return seed + 122; }
    }
    public static int nullVirtualCall(int seed) {
        Base value = null;
        try { return value.get(); } catch (NullPointerException e) { return seed + 123; }
    }
    public static int nullInterfaceCall(int seed) {
        ValueFace value = null;
        try { return value.get(); } catch (NullPointerException e) { return seed + 124; }
    }
    public static int nullPrivateSpecialCall(int seed) {
        FaultRoot value = null;
        try { return value.privateValue(); } catch (NullPointerException e) { return seed + 125; }
    }
    public static int boundsStore(int seed) {
        int[] value = new int[1];
        try { value[1] = seed; return -1; } catch (ArrayIndexOutOfBoundsException e) { return seed + 126; }
    }
    public static int boundsLongLoad(int seed) {
        long[] value = new long[1];
        try { return (int) value[-1]; } catch (IndexOutOfBoundsException e) { return seed + 127; }
    }
    public static int negativeObjectArray(int size) {
        try { return new Base[size].length; } catch (NegativeArraySizeException e) { return 128; }
    }
    public static int negativeMultiOuter(int size) {
        try { return new int[size][1].length; } catch (NegativeArraySizeException e) { return 129; }
    }
    public static int negativeMultiInner(int size) {
        try { return new int[1][size].length; } catch (NegativeArraySizeException e) { return 130; }
    }
    public static int primitiveArrayCast(int seed) {
        Object value = new int[1];
        try { return ((long[]) value).length; } catch (ClassCastException e) { return seed + 131; }
    }

    public static int uncaughtArithmetic(int value) { return divide(value); }
    public static int uncaughtNull(int seed) { return nullArray() + seed; }
    public static int uncaughtBounds(int index) { return badIndex(index); }
    public static int uncaughtStore(int seed) { return badStore() + seed; }
    public static int uncaughtCast(int seed) { return badCast() + seed; }
    public static int uncaughtNegative(int size) { return badRefSize(size); }
}
