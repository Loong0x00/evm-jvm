package bundle.m3d.owner;

public class OwnerRoot {
    public static int fieldThroughChild(int input) {
        return SymbolicChild.runs * 1000 + SymbolicChild.value * 10 + input;
    }

    public static int callThroughChild(int input) {
        return SymbolicChild.inheritedCall(input);
    }

    public static int fieldThroughFailingChild(int input) {
        return FailingSymbolicChild.value + input;
    }

    public static int callThroughFailingChild(int input) {
        return FailingSymbolicChild.inheritedCall(input);
    }

    public static int writeThroughChild(int input) {
        SymbolicChild.value = input;
        return DeclaringBase.runs * 1000 + DeclaringBase.value;
    }

    public static int voidCallThroughChild(int input) {
        SymbolicChild.store(input);
        return DeclaringBase.runs * 1000 + DeclaringBase.value;
    }
}
