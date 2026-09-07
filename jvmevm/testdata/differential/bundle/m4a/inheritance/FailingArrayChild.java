package bundle.m4a.inheritance;

public class FailingArrayChild extends ArrayBase {
    static int failure = divide(1, 0);

    private static int divide(int left, int right) {
        return left / right;
    }
}
