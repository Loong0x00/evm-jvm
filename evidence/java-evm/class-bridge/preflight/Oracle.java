public final class Oracle {
    public static void main(String[] args) throws Exception {
        Class<?> c = Class.forName(args[0]);
        Object value = c.getMethod("run", int.class).invoke(null, Integer.valueOf(args[1]));
        System.out.println(args[0] + "(" + args[1] + ")=" + value);
    }
}
