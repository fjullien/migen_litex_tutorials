#!/usr/bin/env python3

from migen import *
from migen.genlib.resetsync import AsyncResetSynchronizer
from migen.genlib.misc import WaitTimer

from platform_tango import *

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
    def __init__(self, platform):

        crg = CRG(platform)
        self.submodules += crg

        led = platform.request("user_led", 1)
        blink = Blink(24)
        self.submodules += blink
        self.comb += led.eq(blink.out)

        data = platform.request("do")
        ring = RingSerialCtrl(24e6)
        self.submodules += ring
        self.comb += data.eq(~ring.do)

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
    def __init__(self, sys_clk_freq):
        self.do = Signal()

        ###

        t1h    = int(0.80e-6 * sys_clk_freq)
        t1l    = int(0.45e-6 * sys_clk_freq)

        pulse_cnt  = Signal(max=24)
        high       = Signal(1, reset=1)

        t1h_timer = WaitTimer(t1h)
        t1l_timer = WaitTimer(t1l)
        self.submodules += t1h_timer, t1l_timer

        self.sync += [
            If(pulse_cnt < 24,
                If(high,
                    self.do.eq(1),
                    t1h_timer.wait.eq(1),
                    If(t1h_timer.done,
                        high.eq(0),
                        t1h_timer.wait.eq(0),
                    )
                ).Else(
                    self.do.eq(0),
                    t1l_timer.wait.eq(1),
                    If(t1l_timer.done,
                        high.eq(1),
                        pulse_cnt.eq(pulse_cnt + 1),
                        t1l_timer.wait.eq(0),
                    ),
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
    platform= Platform()

    if "load" in sys.argv[1: ]:
        prog= platform.create_programmer()
        prog.load_bitstream(os.path.join(
            build_dir, "impl", "pnr", "project.fs"))
        exit()

    if "sim" in sys.argv[1: ]:
        ring = RingSerialCtrl(24e6)
        run_simulation(ring, test(), clocks={"sys": 1e9/24e6}, vcd_name="sim.vcd")
        exit()

    design = Tuto(platform)
    platform.build(design, build_dir=build_dir)

if __name__ == "__main__":
    main()
