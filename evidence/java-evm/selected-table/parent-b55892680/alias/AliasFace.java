public interface AliasFace {
    int v(int x);
    default int d(int x) { return x + 31; }
}
