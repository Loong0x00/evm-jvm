package probe;
import java.util.ArrayList;
public final class ArrayListRefusalCloneProbe extends ArrayList {  public Object copy() throws CloneNotSupportedException { return clone(); } public static void main(String[] args) throws Exception { new ArrayListRefusalCloneProbe().copy(); } }
