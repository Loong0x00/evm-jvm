package bundle.m3c.errors;

public class NestedErrorRoot {
    public static int triggerNested(int addend) {
        return NestedFailure.value + addend;
    }
}
