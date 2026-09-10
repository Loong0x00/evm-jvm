package java.io;
public abstract class OutputStream implements Closeable, Flushable {
    protected OutputStream() {}
    public abstract void write(int value) throws IOException;
    public void write(byte[] value) throws IOException {
        write(value, 0, value.length);
    }
    public void write(byte[] value, int offset, int length) throws IOException {
        int capacity = value.length;
        if (offset < 0 || length < 0 || offset > capacity - length) throw new IndexOutOfBoundsException();
        for (int i = 0; i < length; i++) write(value[offset + i]);
    }
    public void close() throws IOException {}
    public void flush() throws IOException {}
}
