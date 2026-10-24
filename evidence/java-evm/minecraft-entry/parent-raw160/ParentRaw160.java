import java.util.*;
import java.util.function.Supplier;
import java.lang.reflect.Array;
/** Generated-only normal and covariant Supplier dispatch; no lambda or fake get result. */
public final class ParentRaw160 {
    interface Child extends Supplier<Object> { }
    static final class Provider implements Child {
        final Object value;
        int calls;
        boolean fail;
        Provider(Object value) { this.value = value; }
        public Object get() { calls++; if (fail) throw new ArithmeticException(); return value; }
    }
    static final class Covariant implements Supplier<String> {
        final String value;
        Covariant(String value) { this.value = value; }
        public String get() { return value; }
    }
    private static void check(boolean ok) { if (!ok) throw new ArithmeticException(); }
    private static void cold(Object[] values) { check(values.length == 1); }
    public static void main(String[] args) {
        cold(new String[1]);
        Object value = new Object();
        Provider provider = new Provider(value);
        Supplier<Object> direct = provider;
        Child child = provider;
        check(direct.get() == value && child.get() == value && provider.calls == 2);
        Provider nil = new Provider(null);
        check(nil.get() == null && nil.calls == 1);
        String unit = String.valueOf((char) 65535);
        Supplier<String> covariant = new Covariant(unit);
        check(covariant.get() == unit);
        provider.fail = true;
        boolean thrown = false;
        try { direct.get(); }
        catch (ArithmeticException expected) { thrown = true; }
        check(thrown && provider.calls == 3);
        try { ((Supplier) null).get(); throw new ArithmeticException(); }
        catch (NullPointerException expected) { }
        try { Supplier bad = (Supplier) new Object(); throw new ArithmeticException(); }
        catch (ClassCastException expected) { }
        Supplier[] refs = (Supplier[]) Array.newInstance(Supplier.class, 2);
        refs[0] = nil; refs[1] = covariant;
        check(refs[0].get() == null && refs[1].get() == unit);
        Supplier[] copy = refs.clone();
        check(copy != refs && copy.length == 2 && copy[1] == covariant);
        check(Supplier.class.getName().equals("java.util.function.Supplier"));
        ArrayList list = new ArrayList();
        list.add(value); list.add(null);
        Iterator cursor = list.iterator();
        check(cursor.next() == value && cursor.next() == null && !cursor.hasNext());
        list.add(unit);
        try { cursor.next(); throw new ArithmeticException(); }
        catch (ConcurrentModificationException expected) { }
        LinkedHashMap map = new LinkedHashMap();
        LinkedHashMap key = new LinkedHashMap();
        check(map.put(key, value) == null && map.size() == 1);
        Map.Entry entry = (Map.Entry) map.entrySet().iterator().next();
        check(entry.getKey() == key && entry.getValue() == value);
        check(!((Object) map instanceof EnumMap));
        Object[] backing = {value};
        Iterator array = Arrays.asList(backing).iterator();
        backing[0] = unit;
        check(array.next() == unit && !array.hasNext());
    }
}
