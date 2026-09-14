public final class UnsupportedAbstractMain {
  public static void main(String[] ignored) throws Exception { AbstractNewInstanceTarget.class.newInstance(); }
}
abstract class AbstractNewInstanceTarget { public AbstractNewInstanceTarget() {} }
