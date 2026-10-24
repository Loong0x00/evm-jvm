import java.lang.reflect.Array;
public final class Probe { public static void main(String[] args) { Mark[] a = (Mark[]) Array.newInstance(Mark.class, 2); a[0] = new Impl(); } }
