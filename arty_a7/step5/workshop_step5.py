#!/usr/bin/env python3
import sys

from migen import *
from migen.genlib.resetsync import AsyncResetSynchronizer
from migen.genlib.misc import WaitTimer

from litex_boards.platforms import arty

from ring import *

# CRG ----------------------------------------------------------------------------------------------

class CRG(Module):
    def __init__(self, platform):
        self.rst = Signal()
        self.clock_domains.cd_sys   = ClockDomain()

        # # #

        clk = platform.request("clk100")
        rst_n = platform.request("cpu_reset")

        self.comb += self.cd_sys.clk.eq(clk)
        self.specials += AsyncResetSynchronizer(self.cd_sys, ~rst_n)

        platform.add_period_constraint(clk, 1e9/100e6)

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

    platform = arty.Platform(variant="a7-35", toolchain="vivado")

    from litex.build.generic_platform import Pins, IOStandard
    platform.add_extension([("do", 0, Pins("B7"), IOStandard("LVCMOS33"))])

    if "load" in sys.argv[1: ]:
        prog = platform.create_programmer()
        prog.load_bitstream(build_dir + "/top.bit")
        exit()

    if "sim" in sys.argv[1: ]:
        do = Signal()
        ring = RingControl(do, 0x408020, 12, 100e6)
        run_simulation(ring, test(ring), clocks={"sys": 1e9/100e6}, vcd_name="sim.vcd")
        exit()

    design = Tuto(platform, 24e6)
    platform.build(design, build_dir=build_dir)

if __name__ == "__main__":
    main()
