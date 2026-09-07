package bundle.m4a.init;

public final class InitRoot {
    private InitRoot() {}

    public static int initializedLength(int ignored) {
        return InitOwner.VALUES.length;
    }

    public static int initializedElement(int index) {
        return InitOwner.VALUES[index];
    }

    public static int preparedNull(int ignored) {
        return InitOwner.NULL_VALUE == null ? 1 : 0;
    }

    public static int initializerAlias(int value) {
        InitOwner.ALIAS[1] = value;
        return InitOwner.VALUES[1];
    }

    public static int initializerFinalAlias(int value) {
        InitOwner.FINAL_ALIAS[2] = value;
        return InitOwner.ALIAS[2];
    }

    public static int helperReturnedField(int index) {
        int[] values = InitOwner.values();
        return values[index];
    }

    public static int helperCalledOnce(int ignored) {
        int left = InitOwner.VALUES[0];
        int right = InitOwner.ALIAS[1];
        return InitMaker.calls * 100 + left + right;
    }

    public static int replaceAfterInitialization(int value) {
        int[] old = InitOwner.VALUES;
        InitOwner.VALUES = new int[1];
        InitOwner.VALUES[0] = value;
        return old.length * 100 + InitOwner.VALUES[0];
    }
}
