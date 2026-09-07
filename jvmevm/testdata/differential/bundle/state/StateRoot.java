package bundle.state;

public class StateRoot {
    public static int callerLocals(int first, int second) {
        int savedFirst = first;
        int savedSecond = second;
        int result = StateHelper.rewrite(first, second);
        return savedFirst * 10000 + savedSecond * 100 + result;
    }

    public static int callerPrefix(int prefix, int first, int second) {
        return prefix + StateHelper.mix(first, second) - 7;
    }

    public static int twoCalls(int first, int second) {
        return StateHelper.mix(first, second) - StateHelper.mix(second, first);
    }

    public static int sixArguments(int first, int second, int third, int fourth,
                                   int fifth, int sixth) {
        return StateHelper.mix6(first, second, third, fourth, fifth, sixth);
    }

    public static int voidCall(int value) {
        VoidHelper.consume(value);
        return value - 1;
    }

    public static int nestedVoidCall(int value) {
        VoidHelper.nested(value);
        return value * 2;
    }

    public static int discardExternalResult(int value) {
        StateHelper.ignored(value);
        return value + 9;
    }
}
