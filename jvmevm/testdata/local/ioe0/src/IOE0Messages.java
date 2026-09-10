import java.io.EOFException;
import java.io.FileNotFoundException;
import java.io.IOException;

public final class IOE0Messages {
  static final class MessageOverride extends IOException {
    String actual;
    MessageOverride(String message) {
      super("base");
      actual = message;
    }
    public String getMessage() { return actual; }
  }

  public static int throwableZero() {
    Throwable value = new Throwable();
    return value.getMessage() == null && value.getCause() == null ? 1 : 0;
  }

  public static int throwableMessageIdentity() {
    String message = new String(new char[]{'m', 0, '\ud800'});
    Throwable value = new Throwable(message);
    return value.getMessage() == message && value.getCause() == null ? 1 : 0;
  }

  public static int exceptionMessageIdentity() {
    String message = new String(new char[]{'e', 'x'});
    Exception value = new Exception(message);
    return value.getMessage() == message && value.getCause() == null ? 1 : 0;
  }

  public static int ioZero() {
    IOException value = new IOException();
    return value.getMessage() == null && value.getCause() == null ? 1 : 0;
  }

  public static int ioLiteral() {
    String message = "io-literal";
    IOException value = new IOException(message);
    return value.getMessage() == message && value.getCause() == null ? 1 : 0;
  }

  public static int fnfeConstructed() {
    String message = new String(new char[]{'f', 'i', 'l', 'e'});
    FileNotFoundException value = new FileNotFoundException(message);
    return value.getMessage() == message && value.getCause() == null ? 1 : 0;
  }

  public static int eofNullVsEmpty() {
    String empty = new String(new char[0]);
    EOFException absent = new EOFException((String)null);
    EOFException present = new EOFException(empty);
    return absent.getMessage() == null && present.getMessage() == empty &&
        present.getMessage() != absent.getMessage() ? 1 : 0;
  }

  public static int virtualMessageOverride() {
    String message = new String(new char[]{'o', 'v', 'e', 'r'});
    Throwable value = new MessageOverride(message);
    return value.getMessage() == message && value.getCause() == null ? 1 : 0;
  }
}
