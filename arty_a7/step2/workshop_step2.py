#!/usr/bin/env python3

import sys

from migen import *
from migen.genlib.resetsync import AsyncResetSynchronizer

# We want to use WaitTime so import it
from migen.genlib.misc import WaitTimer

from litex_boards.platforms import arty

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
    def __init__(self, platform):

        crg = CRG(platform)
        self.submodules += crg

        led = platform.request("user_led", 1)
        blink = Blink(24)
        self.submodules += blink
        self.comb += led.eq(blink.out)

        data = platform.request("do")
        ring = RingSerialCtrl(100e6)
        self.submodules += ring
        self.comb += data.eq(ring.do)

# Blinker -------------------------------------------------------------------------------------------

class Blink(Module):
    def __init__(self, bit):
        self.out = Signal()

        ###

        counter = Signal(25)
        self.comb += self.out.eq(counter[bit])
        self.sync += counter.eq(counter + 1)

# RingSerialCtrl -------------------------------------------------------------------------------------------

class RingSerialCtrl(Module):
    # Here we pass the clock frequency as a parameter for the module
    def __init__(self, sys_clk_freq):
        self.do = Signal()

        ###

        t1h    = int(0.80e-6 * sys_clk_freq)

        pulse_cnt  = Signal(max=24)
        high       = Signal(1, reset=1)

        # Add your timer instance here

        self.sync += [
            If(pulse_cnt < 24,
                If(high,
                    self.do.eq(1),
                    # Start the timer
                    # timer finished ?
                    #    We are sending a 'low' level
                    #    Stop the timer
                ).Else(
                    self.do.eq(0),
                    # Start the timer
                    # timer finished ?
                    #    We are sending a 'high' level
                    #    Stop the timer
                    #    increment bit counter
                )
            )
        ]

# Test -------------------------------------------------------------------------------------------

def test():
    loop = 0
    while (loop < 10000):
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
        ring = RingSerialCtrl(100e6)
        run_simulation(ring, test(), clocks={"sys": 1e9/100e6}, vcd_name="sim.vcd")
        exit()

    design = Tuto(platform)
    platform.build(design, build_dir=build_dir)

if __name__ == "__main__":
    main()
