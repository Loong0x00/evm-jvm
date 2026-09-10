import java.io.IOException;

public final class IOE0Origins {
  static final class AEHolder {
    static int value = 1 / zero();
  }
  static final class NPEHolder {
    static int value = ((int[])null).length;
  }

  static int zero() { return 0; }

  static void throwIO(IOException value) throws IOException { throw value; }

  public static int explicitAE() {
    ArithmeticException value = new ArithmeticException();
    return value.getMessage() == null && value.getCause() == null ? 1 : 0;
  }

  public static int implicitAECause() {
    try {
      int ignored = 1 / zero();
      return ignored;
    } catch (ArithmeticException value) {
      return value.getCause() == null ? 1 : 0;
    }
  }

  public static int explicitNPE() {
    NullPointerException value = new NullPointerException();
    return value.getMessage() == null && value.getCause() == null ? 1 : 0;
  }

  public static int implicitNPE() {
    try {
      int ignored = ((int[])null).length;
      return ignored;
    } catch (NullPointerException value) {
      return value.getMessage() == null && value.getCause() == null ? 1 : 0;
    }
  }

  public static int rethrowIdentity() {
    String message = new String(new char[]{'r', 'e'});
    IOException made = new IOException(message);
    try {
      try { throwIO(made); }
      catch (IOException first) { throw first; }
    } catch (IOException second) {
      return second == made && second.getMessage() == message && second.getCause() == null ? 1 : 0;
    }
    return 0;
  }

  public static int ordinaryEIIE() {
    Throwable cause = new IOException(new String(new char[]{'c'}));
    ExceptionInInitializerError wrapper = new ExceptionInInitializerError(cause);
    return wrapper.getException() == cause && wrapper.getCause() == cause && wrapper.getMessage() == null ? 1 : 0;
  }

  public static int wrappedAE() {
    try {
      return AEHolder.value;
    } catch (ExceptionInInitializerError wrapper) {
      Throwable first = wrapper.getException();
      Throwable second = wrapper.getCause();
      return first == second && first instanceof ArithmeticException && first.getCause() == null ? 1 : 0;
    }
  }

  public static int wrappedNPE() {
    try {
      return NPEHolder.value;
    } catch (ExceptionInInitializerError wrapper) {
      Throwable first = wrapper.getException();
      Throwable second = wrapper.getCause();
      return first == second && first instanceof NullPointerException &&
          first.getMessage() == null && first.getCause() == null ? 1 : 0;
    }
  }
}
