/** TEST-ONLY trusted JVM oracle for the checked-in S0 fixture classes. */
public final class StockOracle {
    private StockOracle() {}

    public static void main(String[] args) throws Exception {
        if (args.length != 1) {
            throw new IllegalArgumentException("expected one checked-in fixture class name");
        }
        Object value = Class.forName(args[0]).getMethod("run").invoke(null);
        System.out.println(((Integer) value).intValue());
    }
}
