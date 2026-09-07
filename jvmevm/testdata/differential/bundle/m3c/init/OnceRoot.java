package bundle.m3c.init;

public class OnceRoot {
    public static int repeatedActiveUse(int addend) {
        int first = OnceOwner.readValue();
        int count = OnceOwner.readRuns();
        int second = OnceOwner.value;
        return first * 10000 + count * 1000 + second + addend;
    }

    public static int repeatedGetstatic(int addend) {
        return OnceOwner.value + OnceOwner.value + OnceOwner.runs + addend;
    }
}
