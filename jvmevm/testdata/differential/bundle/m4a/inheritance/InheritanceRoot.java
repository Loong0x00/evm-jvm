package bundle.m4a.inheritance;

public final class InheritanceRoot {
    private InheritanceRoot() {}

    public static int inheritedRead(int index) {
        return ArrayLeft.DATA[index];
    }

    public static int siblingSharedWrite(int index, int value) {
        ArrayLeft.DATA[index] = value;
        return ArrayRight.DATA[index];
    }

    public static int siblingIdentity(int ignored) {
        return ArrayLeft.DATA == ArrayRight.DATA ? 1 : 0;
    }

    public static int inheritedHelperIdentity(int ignored) {
        return ArrayLeft.data() == ArrayRight.DATA ? 1 : 0;
    }

    public static int finalInheritedMutable(int index, int value) {
        ArrayLeft.FINAL_DATA[index] = value;
        return ArrayRight.FINAL_DATA[index];
    }

    public static int inheritedReplacement(int value) {
        int[] old = ArrayLeft.DATA;
        ArrayRight.DATA = new int[1];
        old[0] = value;
        return ArrayLeft.DATA[0] - old[0];
    }

    public static int failingSymbolicChildDoesNotInitialize(int index) {
        return FailingArrayChild.DATA[index];
    }
}
