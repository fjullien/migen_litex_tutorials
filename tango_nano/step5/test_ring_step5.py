#!/usr/bin/env python3
from migen import *
from migen.genlib.resetsync import AsyncResetSynchronizer
from migen.genlib.misc import WaitTimer

from platform_tango import *
from ring import *

# CRG ----------------------------------------------------------------------------------------------

class CRG(Module):
    def __init__(self, platform):
        self.rst = Signal()
        self.clock_domains.cd_sys   = ClockDomain()

        # # #

        clk = platform.request("sys_clk")
        rst_n = platform.request("user_btn", 0)

        self.comb += self.cd_sys.clk.eq(clk)
        self.specials += AsyncResetSynchronizer(self.cd_sys, ~rst_n)

        platform.add_period_constraint(clk, 1e9/24e6)

# Design -------------------------------------------------------------------------------------------

class Tuto(Module):
    def __init__(self, platform, sys_clk_freq):

        crg = CRG(platform)
        self.submodules += crg

        led = RingControl(platform.request("do"), # Add parameters
        self.submodules.ledring = led

# Test -------------------------------------------------------------------------------------------

def test(dut):
    loop = 0
    while (loop < 50000):
        yield
        loop = loop + 1

# Build --------------------------------------------------------------------------------------------

def main():

    build_dir= 'gateware'
    platform= Platform()

    if "load" in sys.argv[1: ]:
        prog= platform.create_programmer()
        prog.load_bitstream(os.path.join(
            build_dir, "impl", "pnr", "project.fs"))
        exit()

    if "sim" in sys.argv[1: ]:
        do = Signal()
        ring = RingControl(do, 0x408020, 12, 24e6)
        run_simulation(ring, test(ring), clocks={"sys": 1e9/24e6}, vcd_name="sim.vcd")
        exit()

    # Here you may want to add the parameter you want to control from the command line

    # And pass it to Tuto
    design = Tuto(platform, 24e6)
    platform.build(design, build_dir=build_dir)

if __name__ == "__main__":
    main()
