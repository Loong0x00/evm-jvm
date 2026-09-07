package bundle.m3d.shared;

public class SharedRoot {
    public static int writeLeftReadRight(int input) {
        SharedLeft.counter = input;
        return SharedRight.counter;
    }

    public static int writeRightReadLeft(int input) {
        SharedRight.counter = input * 2;
        return SharedLeft.counter;
    }

    public static int twoWrites(int first, int second) {
        SharedLeft.counter = first;
        SharedRight.counter = second;
        return SharedBase.counter;
    }

    public static int voidUpdateAcrossSiblings(int input) {
        SharedLeft.add(input);
        return SharedRight.counter;
    }

    public static int inheritedCallsShareStorage(int input) {
        SharedLeft.add(input);
        return SharedRight.read(input * 2);
    }
}
