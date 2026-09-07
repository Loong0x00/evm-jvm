package bundle.m3d.reentrant;

public class ReentrantParent {
    public static int directDefault = ReentrantChild.dynamicValue;
    public static int callDefault = ReentrantChild.readDynamic();
    public static int sourceConstant = ReentrantChild.COMPILED_CONSTANT;
}
