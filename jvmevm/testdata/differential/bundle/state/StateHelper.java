package bundle.state;

public class StateHelper {
    public static int rewrite(int first, int second) {
        int saved = first;
        first = second + 101;
        int scratch = saved * 5;
        second = first - scratch;
        return second + scratch * 2;
    }

    public static int mix(int first, int second) {
        int local = first * 17;
        return local - second * 3;
    }

    public static int mix6(int first, int second, int third, int fourth,
                           int fifth, int sixth) {
        return first - second * 2 + third * 3 - fourth * 4
                + fifth * 5 - sixth * 6;
    }

    public static int ignored(int value) {
        return value * 23 - 9;
    }
}
