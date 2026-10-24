import java.util.Arrays; import java.util.List;
public final class ArraysAsListSetRefusal { public static void main(String[] a) { List x=Arrays.asList(new Object[]{"x"}); x.set(0,"y"); } }
