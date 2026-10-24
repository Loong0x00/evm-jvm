public final class ParentColdArrayArguments {
    static class Base { }
    static final class Sub extends Base { }
    interface Tag { }
    static final class Tagged extends Base implements Tag { }
    private static void check(boolean ok) { if (!ok) throw new ArithmeticException(); }
    private static void objects(Object[] values) { check(values.length == 1); }
    private static void bases(Base[] values) { check(values.length == 1); }
    private static void tags(Tag[] values) { check(values.length == 1); }
    public static void main(String[] args) {
        objects(new String[1]);
        bases(new Sub[1]);
        tags(new Tagged[1]);
        objects(new int[1][]);
    }
}
