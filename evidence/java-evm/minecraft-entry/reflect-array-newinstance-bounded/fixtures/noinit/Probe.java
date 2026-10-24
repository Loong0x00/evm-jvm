import java.lang.reflect.Array;
public final class Probe {
    public static void main(String[] args) {
        Object x = Array.newInstance(Component.class, 0);
        if (x == null) throw new AssertionError();
    }
}
