package bundle.m4b.access.base;

public class ProtectedBase {
    protected int protectedValue;

    protected ProtectedBase(int value) { protectedValue = value; }

    protected int directValue(int add) { return protectedValue + add + 100; }
}
