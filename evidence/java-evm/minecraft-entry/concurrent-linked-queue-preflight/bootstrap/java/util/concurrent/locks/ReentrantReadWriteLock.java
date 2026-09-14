package java.util.concurrent.locks;

import java.io.Serializable;

public class ReentrantReadWriteLock implements ReadWriteLock, Serializable {
    private ReentrantLock reader;
    private ReentrantLock writer;

    public ReentrantReadWriteLock() {
        reader = new ReentrantLock();
        writer = new ReentrantLock();
    }

    public Lock readLock() { return reader; }

    public Lock writeLock() { return writer; }
}
