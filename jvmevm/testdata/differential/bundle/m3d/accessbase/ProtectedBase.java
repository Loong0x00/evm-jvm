package bundle.m3d.accessbase;

public class ProtectedBase {
    protected static int protectedValue = 40;

    protected static int protectedCompute(int input) {
        return protectedValue + input * 2;
    }

    protected static void protectedStore(int input) {
        protectedValue = input;
    }
}
