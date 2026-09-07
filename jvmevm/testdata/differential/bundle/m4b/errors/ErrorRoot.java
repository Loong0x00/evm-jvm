package bundle.m4b.errors;

/** Exact ordinary-constructor/field/special-call failures and initializer wrapping. */
public class ErrorRoot {
    private int secret(int value) { return value + 1; }

    public static int constructorArithmetic(int value, int divisor) {
        ErrorCell cell = new ErrorCell(value, divisor);
        return cell.value;
    }

    public static int constructorNullRead(int value) {
        NullReadingCtor cell = new NullReadingCtor(value);
        return cell.value;
    }

    public static int superConstructorArithmetic(int value, int divisor) {
        FailingChild child = new FailingChild(value, divisor);
        return child.value;
    }

    public static int nullGetField(int value) {
        ErrorCell cell = null;
        return cell.value + value;
    }

    public static int nullPutField(int value) {
        ErrorCell cell = null;
        cell.value = value;
        return value;
    }

    public static int nullReferenceGetField(int value) {
        ErrorCell cell = null;
        return cell.next.value + value;
    }

    public static int nullPrivateSpecial(int value) {
        ErrorRoot root = null;
        return root.secret(value);
    }

    public static int validPrivateSpecial(int value) {
        ErrorRoot root = new ErrorRoot();
        return root.secret(value);
    }

    public static int clinitConstructorArithmetic(int value) {
        return ArithmeticInit.CELL.value + value;
    }

    public static int clinitConstructorNpe(int value) {
        return NullInit.CELL.value + value;
    }

    public static int constructorAfterAllocation(int value) {
        ErrorCell first = new ErrorCell(value, 1);
        ErrorCell second = new ErrorCell(value + 1, 1);
        return second.value - first.value;
    }
}

class ErrorCell {
    public int value;
    public ErrorCell next;

    ErrorCell() {}
    ErrorCell(int value, int divisor) { this.value = value / divisor; }
}

class NullReadingCtor {
    public int value;
    NullReadingCtor(int add) {
        ErrorCell cell = null;
        value = cell.value + add;
    }
}

class FailingParent {
    public int value;
    FailingParent(int value, int divisor) { this.value = value / divisor; }
}

class FailingChild extends FailingParent {
    FailingChild(int value, int divisor) { super(value, divisor); }
}

class ArithmeticInit {
    static ErrorCell CELL = new ErrorCell(1, 0);
}

class NullInit {
    static NullReadingCtor CELL = new NullReadingCtor(1);
}
