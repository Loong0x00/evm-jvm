package bundle.m5ba.recursion;

/** Bounded and overflowing recursion carrying category-2 arguments and returns. */
public class RecursionRoot {
    private static int fold(long value) { return (int) (value ^ (value >>> 32)); }
    private static long factorial(long accumulator, int n) {
        return n <= 1 ? accumulator : factorial(accumulator * n, n - 1);
    }
    private static long fibonacci(int n) {
        return n <= 1 ? n : fibonacci(n - 1) + fibonacci(n - 2);
    }
    private static long sum(long prefix, int n) {
        return n == 0 ? prefix : sum(prefix + n * 0x100000001L, n - 1);
    }
    private static long mutualA(long value, int depth) {
        return depth == 0 ? value : mutualB(value + depth, depth - 1);
    }
    private static long mutualB(long value, int depth) {
        return depth == 0 ? value : mutualA(value ^ ((long) depth << 32), depth - 1);
    }
    private static long overflow(long value) { return overflow(value + 1L); }

    public static int factorialDigest(int n) { return fold(factorial(1L, n)); }
    public static int fibonacciDigest(int n) { return fold(fibonacci(n)); }
    public static int recursivePrefix(int n) { return fold(sum(0x1234567887654321L, n)); }
    public static int mutualDigest(int n) { return fold(mutualA(0x0102030405060708L, n)); }
    public static int stackOverflow(int value) { return fold(overflow(value)); }
}
