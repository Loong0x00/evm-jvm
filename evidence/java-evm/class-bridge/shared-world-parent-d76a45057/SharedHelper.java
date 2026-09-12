public class SharedHelper {
    static int base;
    static { base = init(11); }
    static int init(int x) { return (x * 3) ^ 5; }
    static int mix(int x) { return ((x + base) * 7) ^ (x << 2); }
}
