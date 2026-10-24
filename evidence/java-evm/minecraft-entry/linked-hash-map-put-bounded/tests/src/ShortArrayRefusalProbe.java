import java.util.LinkedHashMap;

public final class ShortArrayRefusalProbe {
    public static void main(String[] args) {
        LinkedHashMap<Object, Object> map = new LinkedHashMap<Object, Object>();
        map.put("a", "one");
        map.put("b", "two");
        Object[] tooShort = new Object[1];
        tooShort[0] = "sentinel";
        map.entrySet().toArray(tooShort);
    }
}
