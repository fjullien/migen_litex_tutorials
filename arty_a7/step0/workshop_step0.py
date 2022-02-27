#!/usr/bin/env python3

from migen import *
from platform_arty_a7 import *

# Blinker -------------------------------------------------------------------------------------------


class Blink(Module):
    def __init__(self, bit):
        # This signal, declared as a attribute of the class
        # can be accessed from outside the module.

        # ....... Add an interface signal named 'out' here ...........


        ###

        # Internal signal

        # ....... Define a 25 bits signal named 'counter' here ...........

        # This is the actual counter. It is incremented each clock cycle.
        # Because it's not just only wires, it needs some memory (registers)
        # it has to be in a synchronous block.

        # ....... Increment 'counter' here ...........

        # Combinatorial assignments can be seen as wires.
        # Here we connect a bit of the counter to the self.out signal

        # ....... Connect bit counter[bit] to the out interface ...........

# Design -------------------------------------------------------------------------------------------

class Tuto(Module):
    def __init__(self, platform):

        # Get pin from ressources
        clk = platform.request("clk100")
        led0 = platform.request("user_led", 0)

        # Creates a "sys" clock domain and generates a startup reset
        crg = CRG(clk)
        self.submodules.crg = crg

        # Instance of Blink
        # ....... Create an instance of Blink ............
        # ....... Add it to submodules ...................
        # ....... Connect blink output to led0 ...........

        # Add a timing constraint
        platform.add_period_constraint(clk, 1e9/100e6)

# Test -------------------------------------------------------------------------------------------

def test():
    loop = 0
    while (loop < 10000):
        yield
        loop = loop + 1

# Build --------------------------------------------------------------------------------------------

def main():

    build_dir="gateware"

    # Instance of our platform (which is in platform_arty_a7.py)
    platform = Platform(toolchain="vivado")
    design = Tuto(platform)

    if "load" in sys.argv[1: ]:
        prog = platform.create_programmer()
        prog.load_bitstream(build_dir + "/top.bit")
        exit()

    if "sim" in sys.argv[1: ]:
        ring = Blink(4)
        run_simulation(ring, test(), clocks={"sys": 1e9/100e6}, vcd_name="sim.vcd")
        exit()

    platform.build(design, build_dir=build_dir)

if __name__ == "__main__":
    main()
