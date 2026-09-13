import java.lang.SecurityManager;
import java.util.Properties;

/** Generated TEST-only Java 8 oracle for the default no-manager branch. */
public final class SecurityGetterProbe {
    private static void fail() {
        int[] zero = new int[1];
        int ignored = 1 / zero[0];
    }

    public static void main(String[] ignored) {
        SecurityManager manager = System.getSecurityManager();
        if (manager != null) {
            // This branch must remain untaken in the VM default state.
            System.setSecurityManager(null);
            fail();
        }
        Object[] source = new Object[] { Properties.class.getName() };
        Object[] target = new Object[1];
        System.arraycopy(source, 0, target, 0, 1);
        if (!"java.util.Properties".equals(target[0])) {
            fail();
        }
    }
}
