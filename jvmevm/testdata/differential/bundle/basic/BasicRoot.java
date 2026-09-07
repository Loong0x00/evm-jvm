package bundle.basic;

public class BasicRoot {
    public static int direct(int value) {
        return BasicHelper.transform(value);
    }

    public static int zeroArgument(int prefix) {
        return prefix + BasicHelper.zero();
    }

    public static int threeArguments(int first, int second, int third) {
        return BasicHelper.combine(first, second, third);
    }

    public static int overloadOne(int value) {
        return BasicHelper.overloaded(value);
    }

    public static int overloadTwo(int first, int second) {
        return BasicHelper.overloaded(first, second);
    }

    public static int twoExternalCalls(int first, int second) {
        return BasicHelper.transform(first) + BasicHelper.transform(second);
    }
}
