package bundle.m3c.init;

public class SelfPrepared {
    static int first = SelfPrepared.second + 5;
    static int second = 11;
    static int third = first + second;

    public static int encoded(int addend) {
        return first * 100 + second * 10 + third + addend;
    }
}
