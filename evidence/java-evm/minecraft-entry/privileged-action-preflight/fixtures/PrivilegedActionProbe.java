import java.lang.SecurityManager;
import java.security.PrivilegedAction;
import java.util.Properties;

/** Generated Java 8 control. The EVM must dispatch the erased interface run(). */
public final class PrivilegedActionProbe {
    private static final class StringAction implements PrivilegedAction<String> {
        public String run() { return "privileged-action"; }
    }

    @SuppressWarnings("rawtypes")
    private static Object erased(PrivilegedAction action) { return action.run(); }

    private static String typed(PrivilegedAction<String> action) { return action.run(); }

    private static void fail() {
        int[] zero = new int[1];
        int ignored = 1 / zero[0];
    }

    public static void main(String[] ignored) {
        PrivilegedAction<String> action = new StringAction();
        Object bridge = erased(action);
        String generic = typed(action);
        SecurityManager manager = System.getSecurityManager();
        Properties properties = new Properties();
        properties.setProperty("privileged.action", "default-null");
        Object[] source = new Object[] { PrivilegedAction.class.getName(), StringAction.class.getName() };
        Object[] target = new Object[2];
        System.arraycopy(source, 0, target, 0, 2);
        if (manager != null || !"privileged-action".equals(bridge)
                || !"privileged-action".equals(generic)
                || !"default-null".equals(properties.getProperty("privileged.action"))
                || !"java.security.PrivilegedAction".equals(target[0])
                || !"PrivilegedActionProbe$StringAction".equals(target[1])) {
            fail();
        }
    }
}
