package probe;
import java.util.ArrayList;
public final class ArrayListCloneProbe extends ArrayList {
    public Object copy() { return super.clone(); }
    public static void main(String[] args) { new ArrayListCloneProbe().copy(); }
}
