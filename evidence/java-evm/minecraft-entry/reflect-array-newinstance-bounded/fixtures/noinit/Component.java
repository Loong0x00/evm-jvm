public final class Component {
    static int marker;
    static { int one = 1; int zero = 0; marker = one / zero; }
}
