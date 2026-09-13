import java.security.PrivilegedAction;
import java.util.Collection;
import java.util.Iterator;
import java.util.LinkedHashSet;
import java.util.NoSuchElementException;
import java.util.Properties;
import java.util.Set;

/** Parent generated control for the measured ordered-set surface and prior blockers. */
public final class ParentLinkedHashSetProbe {
  static int done;
  static final class Equal {
    final int value; Equal(int value){this.value=value;}
    public int hashCode(){return 7;}
    public boolean equals(Object o){return o instanceof Equal && value==((Equal)o).value;}
  }
  static final class Old {
    public int hashCode(){return 11;}
    public boolean equals(Object o){return false;}
  }
  static final class New {
    public int hashCode(){return 11;}
    public boolean equals(Object o){return o instanceof Old;}
  }
  static final class StringAction implements PrivilegedAction<String> {
    public String run(){return "ordered-action";}
  }
  static void require(boolean ok){if(!ok){int z=0;int x=1/z;}}
  @SuppressWarnings("rawtypes") static Object erased(PrivilegedAction x){return x.run();}
  public static void main(String[] ignored){
    Collection<Object> grown=new LinkedHashSet<Object>();
    require(grown.isEmpty());
    String[] ordered={"a","b","c","d","e","f","g","h","i"};
    for(int i=0;i<ordered.length;i++) require(grown.add(ordered[i]));
    require(grown.size()==9 && !grown.isEmpty());
    Iterator<Object> gi=grown.iterator();
    for(int i=0;i<ordered.length;i++) require(gi.hasNext() && gi.next()==ordered[i]);
    require(!gi.hasNext());

    LinkedHashSet<Object> set=new LinkedHashSet<Object>(0);
    Equal one=new Equal(1),two=new Equal(2);
    require(set.add(one) && set.add(null) && set.add(two));
    require(!set.add(new Equal(1)) && set.size()==3);
    Iterator<Object> left=set.iterator(),right=set.iterator();
    require(left.next()==one && right.next()==one);
    require(left.next()==null && left.hasNext() && left.next()==two && !left.hasNext());
    try { left.next(); require(false); } catch(NoSuchElementException expected) { }
    require(right.hasNext() && right.next()==null && right.hasNext());

    Set<Object> directional=new LinkedHashSet<Object>(2);
    Old old=new Old(); require(directional.add(old));
    require(!directional.add(new New()) && directional.size()==1);

    ClassLoader loader=ParentLinkedHashSetProbe.class.getClassLoader();
    require(loader!=null && loader==Equal.class.getClassLoader());
    require(loader==ClassLoader.getSystemClassLoader());
    require(ClassLoader.class.getClassLoader()==null && Class.class.getClassLoader()==null);
    require(Thread.currentThread()==Thread.currentThread());
    require(Thread.currentThread().getContextClassLoader()==null);
    PrivilegedAction<String> action=new StringAction();
    require("ordered-action".equals(action.run()) && "ordered-action".equals(erased(action)));
    require(System.getSecurityManager()==null);
    Properties p=new Properties();p.setProperty("set","ordered");
    Object[] src={loader,p.getProperty("set")},dst=new Object[2];System.arraycopy(src,0,dst,0,2);
    require(dst[0]==loader && "ordered".equals(dst[1]));
    done=733;
  }
}
