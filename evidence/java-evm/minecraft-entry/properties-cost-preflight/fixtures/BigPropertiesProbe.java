import java.util.Dictionary;
import java.util.Hashtable;
import java.util.Properties;

/** TEST-only Java 8 guest oracle for the bounded Properties storage surface. */
public final class BigPropertiesProbe {
    private static void check(boolean value) {
        if (!value) {
            int[] zero = new int[1];
            int ignored = 1 / zero[0];
        }
    }

    public static void main(String[] ignored) {
        Properties defaults = new Properties();
        check(defaults instanceof Hashtable);
        check(defaults instanceof Dictionary);
        check(defaults.setProperty("fall", "default") == null);
        check(defaults.setProperty("nonstring", "default-nonstr") == null);

        Properties p = new Properties(defaults);
        check(p.size() == 0);
        check(p.getProperty("fall").equals("default"));
        check(p.getProperty("absent", "fallback").equals("fallback"));
        check(p.setProperty("key", "one") == null);
        check(p.setProperty("key", "two").equals("one"));
        check(p.getProperty("key").equals("two"));
        check(p.size() == 1);

        p.put("nonstring", new Object());
        check(p.getProperty("nonstring").equals("default-nonstr"));
        check(p.getProperty("nonstring", "fallback").equals("default-nonstr"));

        String alias = new String(new char[] {'a', 'l', 'i', 'a', 's'});
        check(p.setProperty(alias, "alias-value") == null);
        check(p.getProperty("alias").equals("alias-value"));

        check(p.setProperty("g0", "v0") == null);
        check(p.setProperty("g1", "v1") == null);
        check(p.setProperty("g2", "v2") == null);
        check(p.setProperty("g3", "v3") == null);
        check(p.setProperty("g4", "v4") == null);
        check(p.getProperty("g4").equals("v4"));
        check(p.remove("key").equals("two"));
        check(p.getProperty("key") == null);
        check(p.getProperty("fall").equals("default"));

        boolean sawGetNPE = false;
        try {
            p.get(null);
        } catch (NullPointerException expected) {
            sawGetNPE = true;
        }
        check(sawGetNPE);
        boolean sawPutNPE = false;
        try {
            p.put("null-value", null);
        } catch (NullPointerException expected) {
            sawPutNPE = true;
        }
        check(sawPutNPE);
    }
}
