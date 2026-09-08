package bundle.m4fb.errors;

/** Direct default failures and failures wrapped while a default-bearing interface initializes. */
public class ErrorRoot {
    public static int defaultArithmetic(int value) { return new ErrorDefaultImpl().divide(value); }
    public static int defaultNegativeArray(int value) { return new ErrorDefaultImpl().negative(value); }
    public static int defaultClassCast(int value) { return new ErrorDefaultImpl().cast(value); }
    public static int defaultArrayStore(int value) { return new ErrorDefaultImpl().store(value); }
    public static int initArithmeticWrapped(int value) { new ErrorArithmeticImpl(); return value; }
    public static int initNegativeArrayWrapped(int value) { new ErrorNegativeImpl(); return value; }
    public static int initClassCastWrapped(int value) { new ErrorCastImpl(); return value; }
    public static int initArrayStoreWrapped(int value) { new ErrorStoreImpl(); return value; }
    public static int defaultArithmeticNormal(int value) { return new ErrorDefaultImpl().divideNormal(value); }
    public static int defaultArrayNormal(int value) { return new ErrorDefaultImpl().arrayNormal(value); }
    public static int defaultCastNormal(int value) { return new ErrorDefaultImpl().castNormal(value); }
    public static int defaultStoreNormal(int value) { return new ErrorDefaultImpl().storeNormal(value); }
}

class ErrorBase { int value; ErrorBase(int value) { this.value = value; } }
class ErrorChild extends ErrorBase { ErrorChild(int value) { super(value); } }
class ErrorOther { int value; ErrorOther(int value) { this.value = value; } }
interface ErrorDefaults {
    default int divide(int value) { return value / 0; }
    default int negative(int value) { return new int[-1].length + value; }
    default int cast(int value) { Object object = new ErrorOther(value); return ((ErrorBase) object).value; }
    default int store(int value) { ErrorBase[] values = new ErrorChild[1]; values[0] = new ErrorBase(value); return value; }
    default int divideNormal(int value) { return value / 2; }
    default int arrayNormal(int value) { return new int[2].length + value; }
    default int castNormal(int value) { Object object = new ErrorBase(value); return ((ErrorBase) object).value; }
    default int storeNormal(int value) { ErrorBase[] values = new ErrorBase[1]; values[0] = new ErrorBase(value); return values[0].value; }
}
class ErrorDefaultImpl implements ErrorDefaults {}
class ErrorHelper {
    static int arithmetic() { return 1 / zero(); }
    static int zero() { return 0; }
    static int[] negative() { return new int[-1]; }
    static ErrorBase cast() { Object object = new ErrorOther(3); return (ErrorBase) object; }
    static ErrorBase[] store() { ErrorBase[] values = new ErrorChild[1]; values[0] = new ErrorBase(4); return values; }
}
interface ErrorArithmeticFace { int TOKEN = ErrorHelper.arithmetic(); default int run(int value) { return value; } }
class ErrorArithmeticImpl implements ErrorArithmeticFace {}
interface ErrorNegativeFace { int[] TOKEN = ErrorHelper.negative(); default int run(int value) { return value; } }
class ErrorNegativeImpl implements ErrorNegativeFace {}
interface ErrorCastFace { ErrorBase TOKEN = ErrorHelper.cast(); default int run(int value) { return value; } }
class ErrorCastImpl implements ErrorCastFace {}
interface ErrorStoreFace { ErrorBase[] TOKEN = ErrorHelper.store(); default int run(int value) { return value; } }
class ErrorStoreImpl implements ErrorStoreFace {}
