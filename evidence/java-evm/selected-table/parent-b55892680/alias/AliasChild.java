public class AliasChild extends AliasBase {
    static int marker = 11;
    static { marker += 2; }
    public AliasChild(int x) { super(x + marker); }
    public int v(int x) { return super.v(x) + 17; }
    public int superV(int x) { return super.v(x); }
}
