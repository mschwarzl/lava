import sys
import os
try:
    from IPython.kernel.zmq.kernelapp import IPKernelApp
    ZMQ = True
except:
    # had trouble finding kernel.zmq.  Try:
    #   $ pip install -U ipython pyzmq
    ZMQ = False
try:
    import gdb
except:
    print "Either your gdb is not > gdb 7"
    print "Or you are trying to run this without gdb"
    print "Exiting . . ."
    sys.exit(1)

if not "ATP" in os.environ:
    print "Must define ATP breakpoint locations. Exiting . . ."
    sys.exit(1)
else:
    # define dua and atp break point locations
    # must be in format of gdb break points (ie, file : line, *address, symbol_name)
    atp_loc = os.environ['ATP']

BUG_EFFECT_COUNT = 0
# bp_num is int
def get_bp_hits(bp_num):
    data = gdb.execute("info b {}".format(bp_num), to_string=True)
    hit_str = "breakpoint already hit "
    if not hit_str in data:
        return 0
    else:
        return int(data.split(hit_str)[1].split()[0])

EXIT_LOC = "exit"

def launch_debug_using_ipython():
    # run this from a gdb session in order to create a 
    # ipython session one could connect to for gdb_python symbol
    # symbol support
    import IPython
    if not ZMQ:
        IPython.embed()
    else:
        IPython.embed_kernel()
        """
        After this you will see:
            NOTE: When using the `ipython kernel` entry point, Ctrl-C will not work.

            To exit, you will have to explicitly quit this process, by either
            sending
            "quit" from a client, or using Ctrl-\ in UNIX-like environments.

            To read more about this, see
            https://github.com/ipython/ipython/issues/2049


            To connect another client to this kernel, use:
                    --existing kernel-138767.json
        To connect to this ipython kernel, from another terminal on same machine
        type:
            $ ipython console --existing kernel-138767.json
        Note that the kernel number will change with each run of the debugging
        application
        To exit, type quit in the ipython terminal, which will give you control
        of the gdb session
        """


def event_handler (event):
    def handle_bp_event ():
        assert (len(event.breakpoints) == 1)
        b = event.breakpoints[0]
        if b.number == 1:
            # we are at the attack point
            print "== HIT ATP, RESETTING COUNT =="
            gdb.execute("disable 2")
            BUG_EFFECT_COUNT = 0
        elif b.location == EXIT_LOC:
            print "At program exit normal with status:"
            # status will usually be in eax variable for 32 bit systems
            # or maybe it's in $esp + 4
            gdb.execute("p $eax")
            gdb.execute("x/xw $esp+4")
            gdb.execute("q")
        else:
            print "Unknown breakpoint"
            gdb.execute("q")

    def handle_sig_event ():
        print "Instruciton Count: {}".format(BUG_EFFECT_COUNT)
        if event.stop_signal in ["SIGSEGV"]:
            print "Found a SIG {}".format(event.stop_signal)
            gdb.execute("p $_siginfo._sifields._sigfault.si_addr")
            gdb.execute("info proc mappings")
            gdb.execute("q")
        else:
            import IPython; IPython.embed_kernel()
            print "Reached unhandled signal event: {}".format(event.stop_signal)
            print "Exiting . . ."
            sys.exit(1)
    # print "event handler type: stop with signal{}".format(event.stop_signal)
    # print event.breakpoints
    #launch_debug_using_ipython()
    if isinstance(event, gdb.BreakpointEvent):
        handle_bp_event()
    elif isinstance(event, gdb.SignalEvent):
        handle_sig_event()
    else:
        print event
        sys.exit(1)
        # at a general stop event which includes catch points
        # skip
        pass
    gdb.execute("c")


gdb.execute("set breakpoint pending on")
gdb.execute("set pagination off")
gdb.execute("set logging off")
gdb.execute("set confirm off")

gdb.execute("break " + atp_loc, to_string=True)
# set breakpoints on normal exit of program and SEGFAULTS
gdb.execute("break " + EXIT_LOC, to_string=True)
# gdb.execute("handle SIGSEGV stop")
gdb.execute("handle all stop")

# establish callback on breakpoints
gdb.events.stop.connect(event_handler)

# uncomment this line of code to trigger an ipython kernel session that you can
# console into.  See launch_debug_using_ipython() for more info
#import IPython; IPython.embed_kernel()
gdb.execute("r")
