package java.util.concurrent.locks;

import java.io.Serializable;

public class ReentrantLock implements Lock, Serializable {
    private int holds;

    public ReentrantLock() {}

    public void lock() { ++holds; }

    public void unlock() { --holds; }
}
