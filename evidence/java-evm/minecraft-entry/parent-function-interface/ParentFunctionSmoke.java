import java.util.function.Function;
import java.util.regex.Pattern;

/** Generated-only direct, inherited-SAM, bridge, null and captured-state witness. */
public final class ParentFunctionSmoke {
    interface Tagged<T, R> extends Function<T, R> { }
    static final class Captured implements Tagged<Object, Object> {
        final Object state;
        Captured(Object state) { this.state = state; }
        public Object apply(Object value) { return value == null ? state : value; }
    }
    static final class Strings implements Function<String, String> {
        public String apply(String value) { return value; }
    }
    private static void check(boolean ok) { if (!ok) throw new ArithmeticException(); }
    public static void main(String[] args) {
        Object token = new Object();
        Function<Object, Object> fn = new Captured(token);
        check(fn.apply(null) == token && fn.apply(token) == token);
        check(fn instanceof Tagged && fn instanceof Function);
        Function<String, String> strings = new Strings();
        check(strings.apply("bridge") == "bridge" && strings.apply(null) == null);
        try { ((Function) strings).apply(token); throw new ArithmeticException(); }
        catch (ClassCastException expected) { }
        try { ((Function) null).apply(token); throw new ArithmeticException(); }
        catch (NullPointerException expected) { }
        check(Pattern.compile("^[a-z0-9_]+$").matcher("fn_1").matches());
        check("x\r\n".replaceAll("^x\r$", "X").equals("x\r\n"));
        Object[] source = new Object[] {fn, token};
        Object[] copy = source.clone();
        check(copy != source && copy[0] == fn && copy[1] == token);
    }
}
