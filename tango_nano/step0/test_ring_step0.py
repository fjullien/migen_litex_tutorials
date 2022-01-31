#!/usr/bin/env python3

from migen import *
from migen.genlib.resetsync import AsyncResetSynchronizer
from platform_tango import *

# Blinker -------------------------------------------------------------------------------------------


class Blink(Module):
    def __init__(self, bit):
        # This signal, declared as a attribute of the class
        # can be accessed from outside the module.
        self.out = Signal()

        ###

        # Internal signal
        counter = Signal(25)

        # This is the actual counter. It is incremented each clock cycle.
        # Because it's not just only wires, it needs some memory (registers)
        # it has to be in a synchronous block.
        self.sync += counter.eq(counter + 1)

        # Combinatorial assignments can be seen as wires.
        # Here we connect a bit of the counter to the self.out signal
        self.comb += self.out.eq(counter[bit])

# Design -------------------------------------------------------------------------------------------

class Tuto(Module):
    def __init__(self, platform):

        # Get pin from ressources
        clk = platform.request("sys_clk")
        led0 = platform.request("user_led", 0)

        # Creates a "sys" clock domain and generates a startup reset
        crg = CRG(clk)
        self.submodules.crg = crg

        # Instance of Blink
        blink = Blink(22)
        self.submodules += blink
        self.comb += led0.eq(blink.out)

        # Add a timing constraint
        platform.add_period_constraint(clk, 1e9/24e6)

def main():

    # Instance of our platform (which is in platform_tango.py)
    platform = Platform()
    design = Tuto(platform)
    platform.build(design, build_dir="gateware")

    if "load" in sys.argv[1:]:
        prog = platform.create_programmer()
        prog.load_bitstream(os.path.join("gateware", "impl", "pnr", "project.fs"))
        exit()

if __name__ == "__main__":
    main()
