import java.util.Arrays; import java.util.List;
public final class ArraysAsListGetRefusal { public static void main(String[] a) { List x=Arrays.asList(new Object[]{"x"}); x.get(0); } }
