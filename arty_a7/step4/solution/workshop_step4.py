#!/usr/bin/env python3

import sys

from migen import *
from migen.genlib.resetsync import AsyncResetSynchronizer
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
        ring = RingSerialCtrl(12, 100e6)
        self.submodules += ring
        self.comb += ring.leds.eq(0b110111011010)
        self.comb += ring.colors.eq(0x008020)
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
    def __init__(self, nleds, sys_clk_freq):
        self.do       = Signal()
        self.leds     = Signal(12)
        self.colors   = Signal(24)

        ###

        bit_count = Signal(8)
        led_count = Signal(8)
        data      = Signal(24)
        led       = Signal(12)

        # Timings.
        trst = int(75e-6 * sys_clk_freq)
        t0h  = int(0.40e-6 * sys_clk_freq)
        t0l  = int(0.85e-6 * sys_clk_freq)
        t1h  = int(0.80e-6 * sys_clk_freq)
        t1l  = int(0.45e-6 * sys_clk_freq)

        # Timers.
        t0h_timer = WaitTimer(t0h)
        t0l_timer = WaitTimer(t0l)
        self.submodules += t0h_timer, t0l_timer

        t1h_timer = WaitTimer(t1h)
        t1l_timer = WaitTimer(t1l)
        self.submodules += t1h_timer, t1l_timer

        trst_timer = WaitTimer(trst)
        self.submodules += trst_timer

        # FSM
        self.submodules.fsm = fsm = FSM(reset_state="RST")
        fsm.act("RST",
            trst_timer.wait.eq(1),
            If(trst_timer.done,
                NextValue(led_count, 0),
                NextState("LED-SHIFT"),
                NextValue(led, self.leds),
            )
        )
        fsm.act("LED-SHIFT",
            NextValue(bit_count, 24-1),
            NextValue(led_count, led_count + 1),
            If(led[-1] == 0,
                NextValue(data, 0)
            ).Else(
                NextValue(data, self.colors)
            ),
            NextValue(led, led << 1),
            If(led_count == (nleds),
                NextState("RST")
            ).Else(
                NextState("BIT-TEST")
            )
        )
        fsm.act("BIT-TEST",
            If(data[-1] == 0,
                NextState("ZERO-SEND"),
            ),
            If(data[-1] == 1,
                NextState("ONE-SEND"),
            ),
        )
        fsm.act("ZERO-SEND",
            t0h_timer.wait.eq(1),
            t0l_timer.wait.eq(t0h_timer.done),
            self.do.eq(~t0h_timer.done),
            If(t0l_timer.done,
                NextState("BIT-SHIFT")
            )
        )
        fsm.act("ONE-SEND",
            t1h_timer.wait.eq(1),
            t1l_timer.wait.eq(t1h_timer.done),
            self.do.eq(~t1h_timer.done),
            If(t1l_timer.done,
                NextState("BIT-SHIFT")
            )
        )
        fsm.act("BIT-SHIFT",
            NextValue(data, data << 1),
            NextValue(bit_count, bit_count - 1),
            If(bit_count == 0,
                NextState("LED-SHIFT")
            ).Else(
                NextState("BIT-TEST")
            )
        )


# Test -------------------------------------------------------------------------------------------

def test(dut):
    loop = 0
    yield dut.leds.eq(0xfff)
    yield dut.colors.eq(0xff0000)
    while (loop < 30000):
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
        ring = RingSerialCtrl(4, 100e6)
        run_simulation(ring, test(ring), clocks={"sys": 1e9/100e6}, vcd_name="sim.vcd")
        exit()

    design = Tuto(platform)
    platform.build(design, build_dir=build_dir)

if __name__ == "__main__":
    main()
