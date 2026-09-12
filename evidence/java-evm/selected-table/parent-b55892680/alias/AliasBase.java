public class AliasBase implements AliasFace {
    static int seed = 5;
    static { seed += 2; }
    protected int value;
    public AliasBase(int x) { value = x + seed; }
    public int v(int x) { return value + x; }
    private int own(int x) { return x * 2; }
    public int special(int x) { return own(x) + 3; }
    public long wide(long x) { return x + 100L; }
}
