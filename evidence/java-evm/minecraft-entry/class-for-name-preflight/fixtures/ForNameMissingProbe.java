public final class ForNameMissingProbe { public static void main(String[] a) throws Exception { try { Class.forName("javax.servlet.Servlet"); } catch (ClassNotFoundException expected) {} } }
