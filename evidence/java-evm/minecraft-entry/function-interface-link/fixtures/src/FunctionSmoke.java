import java.util.function.Function;

public final class FunctionSmoke {
    interface Tagged<T, R> extends Function<T, R> {}
    static final class Captured implements Tagged<Object, Object> {
        final Object captured;
        Captured(Object captured) { this.captured = captured; }
        public Object apply(Object value) { return value == null ? captured : value; }
    }
    static final class GenericString implements Function<String, String> {
        public String apply(String value) { return value; }
    }
    public static void main(String[] args) {
        Object token = new Object();
        Function<Object, Object> f = new Captured(token);
        if (f.apply(null) != token || f.apply(token) != token) throw new AssertionError();
        if (!(f instanceof Function) || !(f instanceof Tagged)) throw new AssertionError();
        Function<String, String> bridged = new GenericString();
        if (bridged.apply("x") != "x") throw new AssertionError();
        boolean npe = false;
        try { ((Function<Object, Object>) null).apply(token); }
        catch (NullPointerException expected) { npe = true; }
        if (!npe) throw new AssertionError();
    }
}
