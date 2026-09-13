import java.util.Dictionary;
import java.util.Hashtable;
import java.util.Properties;

/** TEST-only direct allocation/constructor-chain control. */
public final class PropertiesConstructionProbe {
    private static void fail() {
        int[] zero = new int[1];
        int ignored = 1 / zero[0];
    }

    public static void main(String[] ignored) {
        Properties p = new Properties();
        Object[] source = new Object[] {"tail"};
        Object[] destination = new Object[1];
        System.arraycopy(source, 0, destination, 0, 1);
        if (!(p instanceof Hashtable) || !(p instanceof Dictionary) || p.size() != 0
                || !Properties.class.getName().equals("java.util.Properties")
                || !destination[0].equals("tail")) {
            fail();
        }
    }
}
