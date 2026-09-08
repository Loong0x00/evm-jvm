package bundle.m5ba.dispatch;

/** Public interface root retaining the exact (I)I ABI while its helpers use J. */
public interface PublicLongApi {
    static long widen(int value) { return ((long) value << 32) | ((long) value & 0xffffffffL); }
    static long combine(long wide, int value) { return wide + (long) value * 0x100000001L; }
    static int interfaceRoot(int value) {
        long result = combine(widen(value), value + 1);
        return (int) (result ^ (result >>> 32));
    }
}
