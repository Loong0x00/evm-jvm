import java.util.Collection;
import java.util.Collections;

public final class SingletonListAddRefusalProbe {
    public static void main(String[] args) {
        Collection<Object> list = Collections.singletonList(new Object());
        list.add(new Object());
    }
}
