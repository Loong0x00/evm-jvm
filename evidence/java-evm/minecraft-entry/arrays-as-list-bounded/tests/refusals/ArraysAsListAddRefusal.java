import java.util.Arrays; import java.util.List;
public final class ArraysAsListAddRefusal { public static void main(String[] a) { List x=Arrays.asList(new Object[]{"x"}); x.add("y"); } }
