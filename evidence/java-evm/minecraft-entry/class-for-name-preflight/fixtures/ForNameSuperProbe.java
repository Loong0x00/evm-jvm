public final class ForNameSuperProbe { public static void main(String[] a) throws Exception { try { Class.forName("javax.servlet.Servlet"); } catch (ReflectiveOperationException expected) {} } }
