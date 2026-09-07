package bundle.m3d.noinit;

public class NoInitRoot extends NoInitMiddle {
    static int rootState = append(5);

    public static int noClinitMiddle(int input) {
        return trace * 100 + rootState + input;
    }

    public static int inheritedAfterNoClinit(int input) {
        return NoInitRoot.trace + input;
    }
}
