package bundle.m3c.errors;

public class InitStackOverflow {
    static int value = recurse(0);

    private static int recurse(int depth) {
        return recurse(depth + 1) + 1;
    }

    public static int entry(int addend) {
        return value + addend;
    }
}
