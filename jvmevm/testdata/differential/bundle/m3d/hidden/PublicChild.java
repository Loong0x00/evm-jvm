package bundle.m3d.hidden;

public class PublicChild extends HiddenBase {
    static int childOnly = touchChild();

    private static int touchChild() {
        HiddenBase.value = HiddenBase.value + 1000;
        return 1;
    }
}
