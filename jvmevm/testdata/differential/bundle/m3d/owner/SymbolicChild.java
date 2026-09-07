package bundle.m3d.owner;

public class SymbolicChild extends DeclaringBase {
    static int childRuns = touchChild();

    private static int touchChild() {
        DeclaringBase.value = DeclaringBase.value + 1000;
        return 1;
    }
}
