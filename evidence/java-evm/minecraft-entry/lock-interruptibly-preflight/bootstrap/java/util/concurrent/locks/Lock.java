package java.util.concurrent.locks;

public interface Lock {
    void lock();
    void lockInterruptibly() throws InterruptedException;
    void unlock();
}
