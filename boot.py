# boot.py - - runs on boot-up
import micropython
import machine
import gc

micropython.alloc_emergency_exception_buf(100)


def reboot():
    machine.reset()


def mem_info():
    print("Alloc: "+str(gc.mem_alloc()))
    print("Free: "+str(gc.mem_free()))
    print("% free: "+str(gc.mem_free()/(gc.mem_free()+gc.mem_alloc())))

