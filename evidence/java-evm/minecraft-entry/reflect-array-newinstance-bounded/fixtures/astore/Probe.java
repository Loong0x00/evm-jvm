import java.lang.reflect.Array;
public final class Probe {
    public static void main(String[] args) {
        Object x = Array.newInstance(Component.class, 1);
        Object[] alias = (Object[]) x;
        alias[0] = new Object();
    }
}
