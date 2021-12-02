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
        rst = platform.request("user_btn", 0)
        clk = platform.request("sys_clk")

        # We need to define a clock domain
        self.clock_domains.cd_sys = ClockDomain("cd_sys")

        # Assign clock pin to clock domain
        self.comb += self.cd_sys.clk.eq(clk)

        # Assign reset pin (inverted) to clock domain
        # Here we use AsyncResetSynchronizer which is a special module
        # See: https://github.com/m-labs/migen/blob/master/migen/genlib/resetsync.py#L7
        self.specials += AsyncResetSynchronizer(self.cd_sys, ~rst)

        # Add a timing constraint
        platform.add_period_constraint(clk, 1e9/24e6)

        # Request led pin
        led0 = platform.request("user_led", 0)
        led1 = platform.request("user_led", 1)

        # First instance of Blink
        blink0 = Blink(24)
        self.submodules += blink0
        self.comb += led0.eq(blink0.out)

        # Second instance of Blink
        blink1 = Blink(22)
        self.submodules += blink1
        self.comb += led1.eq(blink1.out)

# Test -------------------------------------------------------------------------------------------

def test():
    # Simulate 10000 clock cycles
    loop = 0
    while (loop < 10000):
        # Means -> compute the result of this cycle
        yield
        loop = loop + 1

# Build --------------------------------------------------------------------------------------------

def main():

    # Choose where build takes place
    build_dir = 'gateware'

    # Instance of our platform (which is in platform_tango.py)
    platform = Platform()

    # This will load the bitstream into the FPGA.
    # If the power supply is turned off, the bitstream is gone.
    if "load" in sys.argv[1: ]:
        prog = platform.create_programmer()
        prog.load_bitstream(os.path.join(
            build_dir, "impl", "pnr", "project.fs"))
        exit()

    # Flash the bitstream into non volatile memory
    if "flash" in sys.argv[1: ]:
        prog = platform.create_programmer()
        prog.flash(0, os.path.join(build_dir, "impl", "pnr", "project.fs"))
        exit()

    # Run a simulation
    if "sim" in sys.argv[1: ]:
        # Instance of module that will be simulated.
        # This kind of simulation must run on module that only contains pure logic.
        # No platform related things must be present.
        ring = Blink()
        run_simulation(ring, test(), clocks={"sys": 1e9/24e6}, vcd_name="sim.vcd")
        exit()

    # If no argument is given, build the bitstream
    design = Tuto(platform)
    platform.build(design, build_dir=build_dir)

if __name__ == "__main__":
    main()
