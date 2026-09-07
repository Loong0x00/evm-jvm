import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.lang.reflect.Modifier;

/** HOST TEST ONLY: invokes a fixture method on the reference JVM. */
public final class OracleMain {
    private OracleMain() {}

    public static void main(String[] args) {
        if (args.length < 2) {
            fail("usage: OracleMain <class> <method> [decimal int args...]");
        }

        try {
            Class<?> guestClass;
            try {
                guestClass = Class.forName(args[0]);
            } catch (ExceptionInInitializerError guestFailure) {
                System.out.println("exception=" + guestFailure.getClass().getName());
                return;
            } catch (StackOverflowError guestFailure) {
                System.out.println("exception=" + guestFailure.getClass().getName());
                return;
            }
            Method selected = null;
            for (Method candidate : guestClass.getDeclaredMethods()) {
                if (candidate.getName().equals(args[1])) {
                    if (selected != null) {
                        fail("entry method name is overloaded: " + args[1]);
                    }
                    selected = candidate;
                }
            }
            if (selected == null) {
                fail("entry method not found: " + args[1]);
            }
            if (!Modifier.isStatic(selected.getModifiers())) {
                fail("entry method is not static: " + args[1]);
            }
            if (selected.getReturnType() != int.class) {
                fail("entry method does not return int: " + args[1]);
            }

            Class<?>[] parameterTypes = selected.getParameterTypes();
            if (parameterTypes.length != args.length - 2) {
                fail("wrong argument count for: " + args[1]);
            }
            Object[] values = new Object[parameterTypes.length];
            for (int i = 0; i < parameterTypes.length; i++) {
                if (parameterTypes[i] != int.class) {
                    fail("entry method has a non-int parameter: " + args[1]);
                }
                try {
                    values[i] = Integer.valueOf(Integer.parseInt(args[i + 2]));
                } catch (NumberFormatException badInteger) {
                    fail("argument is not a signed decimal int32: " + args[i + 2]);
                }
            }

            try {
                Object result = selected.invoke(null, values);
                System.out.println("value=" + ((Integer) result).intValue());
            } catch (InvocationTargetException guestFailure) {
                Throwable cause = guestFailure.getCause();
                System.out.println("exception=" + cause.getClass().getName());
            }
        } catch (ClassNotFoundException failure) {
            fail("guest class not found: " + args[0]);
        } catch (IllegalAccessException failure) {
            fail("entry method is not accessible: " + args[1]);
        } catch (SecurityException failure) {
            fail("reflection denied: " + failure.getClass().getName());
        } catch (RuntimeException failure) {
            fail("oracle failure: " + failure.getClass().getName());
        }
    }

    private static void fail(String message) {
        System.err.println("oracle: " + message);
        System.exit(2);
        throw new AssertionError("unreachable");
    }
}
