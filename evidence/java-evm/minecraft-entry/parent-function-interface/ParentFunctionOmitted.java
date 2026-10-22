import java.util.function.Function;
/** identity is deliberately outside the apply-only interface profile. */
public final class ParentFunctionOmitted {
    static final class Echo implements Function<Object, Object> {
        public Object apply(Object value) { return value; }
    }
    public static void main(String[] args) {
        Object token = new Object();
        Function<Object, Object> fn = new Echo();
        if (fn.apply(token) != token) throw new ArithmeticException();
        Function<Object, Object> identity = Function.identity();
        if (identity.apply(token) != token) throw new ArithmeticException();
    }
}
