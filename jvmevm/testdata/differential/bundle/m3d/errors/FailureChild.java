package bundle.m3d.errors;

public class FailureChild extends ParentFailure {
    static int childState = childInitialize();

    private static int childInitialize() {
        return 99;
    }

    public static int entry(int input) {
        return childState + input;
    }
}
