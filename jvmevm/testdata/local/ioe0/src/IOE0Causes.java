import java.io.FileNotFoundException;
import java.io.IOException;

public final class IOE0Causes {
  static Throwable shared;
  static CustomError error;
  static BrokenIO escaped;

  static final class CustomError extends Error {
    int marker;
    CustomError(int marker) { super(); this.marker = marker; }
  }

  static final class WrapperHolder {
    static int value = failWithIO();
  }

  static final class ErrorHolder {
    static int value = failWithError();
  }

  static final class FailedHolder {
    static int value = ((int[])null).length;
  }

  static final class IOChild extends FileNotFoundException {
    IOChild(String message) { super(message); }
  }

  static final class BrokenIO extends IOException {
    BrokenIO(String message) {
      super(message);
      escaped = this;
      int ignored = ((int[])null).length;
      if (ignored != 0) escaped = null;
    }
  }

  static int failWithIO() {
    try {
      return ((int[])null).length;
    } catch (NullPointerException cause) {
      shared = cause;
      throw cause;
    }
  }

  static int failWithError() {
    error = new CustomError(17);
    throw error;
  }

  static Throwable makeLaterCause(String message) {
    shared = new IOException(message);
    return shared;
  }

  public static int eiieNull() {
    ExceptionInInitializerError zero = new ExceptionInInitializerError();
    ExceptionInInitializerError explicit = new ExceptionInInitializerError((Throwable)null);
    return zero.getException() == null && zero.getCause() == null &&
        explicit.getException() == null && explicit.getCause() == null ? 1 : 0;
  }

  public static int eiieArgumentIdentity() {
    shared = null;
    String message = new String(new char[]{'a', 'r', 'g'});
    // The wrapper's NEW executes before this argument call allocates its cause.
    ExceptionInInitializerError wrapper = new ExceptionInInitializerError(makeLaterCause(message));
    return wrapper.getException() == shared && wrapper.getCause() == shared &&
        shared.getMessage() == message ? 1 : 0;
  }

  public static int vmWrapper() {
    try {
      return WrapperHolder.value;
    } catch (ExceptionInInitializerError wrapper) {
      Throwable cause = wrapper.getCause();
      return cause == shared && wrapper.getException() == shared &&
          cause.getMessage() == shared.getMessage() ? 1 : 0;
    }
  }

  public static int sharedTwoWrappers() {
    Throwable cause = new IOException(new String(new char[]{'s'}));
    ExceptionInInitializerError first = new ExceptionInInitializerError(cause);
    ExceptionInInitializerError second = new ExceptionInInitializerError(cause);
    return first != second && first.getCause() == cause && second.getCause() == cause &&
        first.getException() == second.getException() ? 1 : 0;
  }

  public static int customErrorUnwrapped() {
    try {
      return ErrorHolder.value;
    } catch (CustomError caught) {
      return caught == error && caught.marker == 17 && caught.getCause() == null ? 1 : 0;
    }
  }

  public static int failedClassLater() {
    int score = 0;
    try {
      score += FailedHolder.value;
    } catch (ExceptionInInitializerError first) {
      if (first.getCause() instanceof NullPointerException) score += 1;
    }
    try {
      score += FailedHolder.value;
    } catch (NoClassDefFoundError later) {
      score += 2;
    }
    return score;
  }

  public static int ioSubclassMessage() {
    String message = new String(new char[]{'s', 'u', 'b'});
    IOChild child = new IOChild(message);
    int score = 0;
    try { throw child; }
    catch (IOException caught) {
      if (caught == child && caught.getMessage() == message) score++;
    }
    try { throw child; }
    catch (Exception caught) {
      if (caught == child && caught.getCause() == null) score++;
    }
    return score == 2 ? 1 : 0;
  }

  public static int constructorFailureAfterSuper() {
    escaped = null;
    String message = new String(new char[]{'p', 'o', 's', 't'});
    try {
      new BrokenIO(message);
      return 0;
    } catch (NullPointerException caught) {
      return escaped != null && escaped.getMessage() == message && escaped.getCause() == null &&
          caught.getMessage() == null && caught.getCause() == null ? 1 : 0;
    }
  }
}
