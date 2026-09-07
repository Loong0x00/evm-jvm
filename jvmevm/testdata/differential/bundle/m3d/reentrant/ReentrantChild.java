package bundle.m3d.reentrant;

public class ReentrantChild extends ReentrantParent {
    public static final int COMPILED_CONSTANT = 7;
    public static int dynamicValue = initializeDynamic();
    public static int completed = finish();

    private static int initializeDynamic() {
        return directDefault * 100 + callDefault * 10 + 9;
    }

    private static int finish() {
        return dynamicValue * 10 + sourceConstant;
    }

    static int readDynamic() {
        return dynamicValue;
    }

    public static int parentObservedDefaults(int input) {
        return directDefault * 10000 + callDefault * 1000
                + sourceConstant * 100 + input;
    }

    public static int childCompleted(int input) {
        return dynamicValue * 1000 + completed + input;
    }
}
