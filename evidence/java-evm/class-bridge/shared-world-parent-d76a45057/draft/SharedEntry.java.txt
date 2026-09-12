public class SharedEntry {
    static int bias;
    static { bias = SharedHelper.init(3); }
    public static int run(int x) { return SharedHelper.mix(x) + bias; }
}
