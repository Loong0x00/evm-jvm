package bundle.m3c.init;

public class ComputedFinalRoot {
    public static int readFinal(int addend) {
        return ComputedFinalOwner.VALUE + addend;
    }

    public static int readFinalTwice(int addend) {
        return ComputedFinalOwner.VALUE * 1000
                + ComputedFinalOwner.VALUE
                + ComputedFinalOwner.helperRuns + addend;
    }
}
