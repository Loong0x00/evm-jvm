import java.lang.SecurityManager;
import java.security.PrivilegedAction;
import java.util.Properties;

/** Generated Java 8 control for the single guest current Thread profile. */
public final class ThreadContextProbe {
    private static final class MinimalLoader extends ClassLoader {
        protected MinimalLoader() { super(); }
    }
    private static final class StringAction implements PrivilegedAction<String> {
        public String run() { return "privileged-action"; }
    }
    @SuppressWarnings("rawtypes")
    private static Object erased(PrivilegedAction action) { return action.run(); }
    private static String typed(PrivilegedAction<String> action) { return action.run(); }
    private static void fail() { int[] z = new int[1]; int ignored = 1 / z[0]; }

    public static void main(String[] ignored) {
        Thread a = Thread.currentThread();
        Thread b = Thread.currentThread();
        if (a != b || a.getContextClassLoader() != null) fail();
        ClassLoader loader = new MinimalLoader();
        ClassLoader[] loaders = new ClassLoader[] { loader, null };
        Object boxed = loaders;
        ClassLoader[] cast = (ClassLoader[]) boxed;
        String type = ClassLoader.class.getName();
        PrivilegedAction<String> action = new StringAction();
        Object bridge = erased(action);
        String generic = typed(action);
        SecurityManager manager = System.getSecurityManager();
        Properties properties = new Properties();
        properties.setProperty("thread.context", "default-null");
        Object[] source = new Object[] { type, StringAction.class.getName() };
        Object[] target = new Object[2];
        System.arraycopy(source, 0, target, 0, 2);
        if (cast.length != 2 || cast[0] != loader || cast[1] != null
                || !"java.lang.ClassLoader".equals(target[0])
                || !"privileged-action".equals(bridge)
                || !"privileged-action".equals(generic) || manager != null
                || !"default-null".equals(properties.getProperty("thread.context"))) fail();
    }
}
