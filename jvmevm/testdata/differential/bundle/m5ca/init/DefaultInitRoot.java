package bundle.m5ca.init;

/** Default-bearing interface initialization fails from a switch-selected body. */
public class DefaultInitRoot {
    public static int entry(int seed) {
        M5caFailingDefault value = new M5caFailingDefaultImpl();
        return value.choose(seed);
    }
}

interface M5caFailingDefault {
    int MARK = M5caInitFailure.fail(7);

    default int choose(int key) {
        switch (key) {
        case -1: return MARK - 1;
        case 0: return MARK;
        default: return MARK + key;
        }
    }
}

class M5caFailingDefaultImpl implements M5caFailingDefault {}

class M5caInitFailure {
    static int fail(int key) {
        switch (key) {
        case -7: return 17;
        case 0: return 23;
        case 7:
            int zero = key - 7;
            return 1 / zero;
        default: return 31;
        }
    }
}
