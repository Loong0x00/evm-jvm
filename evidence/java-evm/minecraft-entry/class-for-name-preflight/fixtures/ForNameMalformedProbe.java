public final class ForNameMalformedProbe { public static void main(String[] a) throws Exception { try { Class.forName("bad/name"); } catch (ClassNotFoundException expected) {} } }
