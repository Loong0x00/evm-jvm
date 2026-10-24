import java.util.Arrays;
import java.util.Iterator;
public final class ArraysAsListIteratorRemoveRefusal { public static void main(String[] a) { Iterator i=Arrays.asList(new Object[]{"x"}).iterator(); i.remove(); } }
