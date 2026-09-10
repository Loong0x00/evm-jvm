package java.lang;
public class ExceptionInInitializerError extends LinkageError {
    private Throwable exception;
    public ExceptionInInitializerError() { super(); }
    public ExceptionInInitializerError(Throwable cause) { super(); exception = cause; }
    public Throwable getException() { return exception; }
    public Throwable getCause() { return exception; }
}
