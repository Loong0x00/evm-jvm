package java.lang;
public class Throwable implements java.io.Serializable {
    private String detailMessage;
    private Throwable cause;
    public Throwable() { super(); cause = this; }
    public Throwable(String message) { super(); cause = this; detailMessage = message; }
    public String getMessage() { return detailMessage; }
    public Throwable getCause() { return cause == this ? null : cause; }
}
