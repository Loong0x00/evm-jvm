package bundle.m3d.owner;

public class FailingSymbolicChild extends DeclaringBase {
    static int failure = 1 / zero();

    private static int zero() {
        return 0;
    }
}
