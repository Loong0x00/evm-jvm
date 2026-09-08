package bundle.m4fc.errors;

/** Direct interface-static failures and failures escaping active interface initializers. */
public class ErrorRoot {
    public static int directArithmetic(int value) { return ErrorStatics.divide(value); }
    public static int directNullCall(int value) { return ErrorStatics.nullCall(value); }
    public static int directNullField(int value) { return ErrorStatics.nullField(value); }
    public static int directStackOverflow(int value) { return ErrorStatics.recurse(value); }
    public static int initArithmeticWrapped(int value) { return ArithmeticFace.BAD + value; }
    public static int initNullWrapped(int value) { return NullFace.BAD + value; }
    public static int initStackOverflowUnwrapped(int value) { return StackFace.BAD + value; }
    public static int crossInitFailureWrapped(int value) { return CallerFace.call(value); }
    public static int arithmeticNormal(int value) { return ErrorStatics.divideNormal(value); }
    public static int nullBranchNormal(int value) { return ErrorStatics.nullBranch(value); }
}

class ErrorTarget { int value; ErrorTarget(int value) { this.value = value; } int run(int delta) { return value + delta; } }
interface ErrorStatics {
    static int zero() { return 0; }
    static int divide(int value) { return value / zero(); }
    static int divideNormal(int value) { return value / 2; }
    static int nullCall(int value) { ErrorTarget target = null; return target.run(value); }
    static int nullField(int value) { ErrorTarget target = null; return target.value + value; }
    static int nullBranch(int value) { ErrorTarget target = null; return target == null ? value : target.value; }
    static int recurse(int value) { return recurse(value + 1); }
}
class ErrorHelper {
    static int arithmetic() { return ErrorStatics.divide(1); }
    static int nullFailure() { return ErrorStatics.nullCall(1); }
    static int stackFailure() { return ErrorStatics.recurse(1); }
}
interface ArithmeticFace { int BAD = ErrorHelper.arithmetic(); }
interface NullFace { int BAD = ErrorHelper.nullFailure(); }
interface StackFace { int BAD = ErrorHelper.stackFailure(); }
interface CallerFace { int TOKEN = 7; static int call(int value) { return ArithmeticFace.BAD + value; } }
