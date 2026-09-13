import java.util.Iterator;
import java.util.LinkedHashSet;
import java.util.NoSuchElementException;
/** Java8 TEST oracle for collection semantics portable to the host. */
public final class ParentLinkedHashSetHostOracle {
  static final class Old { public int hashCode(){return 11;} public boolean equals(Object o){return false;} }
  static final class New { public int hashCode(){return 11;} public boolean equals(Object o){return o instanceof Old;} }
  static void require(boolean x){if(!x)throw new AssertionError();}
  public static void main(String[] x){
    LinkedHashSet<Object> grown=new LinkedHashSet<Object>();String[] a={"a","b","c","d","e","f","g","h","i"};
    require(grown.isEmpty());for(String s:a)require(grown.add(s));Iterator<Object> it=grown.iterator();for(String s:a)require(it.hasNext()&&it.next()==s);require(!it.hasNext());try{it.next();throw new AssertionError();}catch(NoSuchElementException ok){}
    LinkedHashSet<Object> directional=new LinkedHashSet<Object>(2);require(directional.add(new Old()));require(!directional.add(new New())&&directional.size()==1);
    ClassLoader l=ParentLinkedHashSetHostOracle.class.getClassLoader();require(l!=null&&l==ClassLoader.getSystemClassLoader()&&ClassLoader.class.getClassLoader()==null);
  }
}
