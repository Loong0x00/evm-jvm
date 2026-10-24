import java.util.Collections;
import java.util.Iterator;
public final class RemoveProbe { public static void main(String[] args) { Iterator<Object> x=Collections.singletonList(new Object()).iterator(); x.remove(); } }
