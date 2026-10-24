import java.util.LinkedHashMap;
import java.util.Map;

final class HashThrowKey {
    public int hashCode() { throw new ArithmeticException(); }
    public boolean equals(Object other) { return false; }
}

final class ExistingKey {
    public int hashCode() { return 17; }
    public boolean equals(Object other) { return this == other; }
}

final class EqualsThrowKey {
    public int hashCode() { return 17; }
    public boolean equals(Object other) { throw new ArithmeticException(); }
}

public final class CallbackExceptionProbe {
    public static void main(String[] args) {
        LinkedHashMap<Object, Object> hashMap = new LinkedHashMap<Object, Object>();
        boolean hashThrown = false;
        try { hashMap.put(new HashThrowKey(), "never-inserted"); }
        catch (ArithmeticException expected) { hashThrown = true; }
        if (!hashThrown || hashMap.size() != 0) throw new ArithmeticException();

        LinkedHashMap<Object, Object> equalsMap = new LinkedHashMap<Object, Object>();
        ExistingKey existing = new ExistingKey();
        equalsMap.put(existing, "old");
        boolean equalsThrown = false;
        try { equalsMap.put(new EqualsThrowKey(), "never-replaces"); }
        catch (ArithmeticException expected) { equalsThrown = true; }
        if (!equalsThrown || equalsMap.size() != 1) throw new ArithmeticException();
        Map.Entry<Object, Object> entry = equalsMap.entrySet().iterator().next();
        if (entry.getKey() != existing || !entry.getValue().equals("old"))
            throw new ArithmeticException();
    }
}
