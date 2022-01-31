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

        # Pass nb_leds = 12
        ring = RingSerialCtrl(12, 24e6)
        self.submodules += ring

        # Configure RingSerialCtrl inputs
        self.comb += ring.leds.eq(0b110111011010)
        self.comb += ring.led_data.eq(0x000020)

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
    def __init__(self, nleds, sys_clk_freq):
        self.do       = Signal()
        self.leds     = Signal(12)
        self.colors   = Signal(24)

        ###

        # Internal signals

        # Timings
        trst = int(75e-6 * sys_clk_freq)
        t0h  = int(0.40e-6 * sys_clk_freq)
        t0l  = int(0.85e-6 * sys_clk_freq)
        t1h  = int(0.80e-6 * sys_clk_freq)
        t1l  = int(0.45e-6 * sys_clk_freq)

        # Timers
        t0h_timer = WaitTimer(t0h)
        t0l_timer = WaitTimer(t0l)
        self.submodules += t0h_timer, t0l_timer

        #......

        # FSM
        self.submodules.fsm = fsm = FSM(reset_state="LED-SHIFT")

        # Wait for reset time
        fsm.act("RST",
            #...
        )

        # Get the current led control bit to see if it
        # should be on or off and prepare a variable with
        # the data (24 bits) to send
        fsm.act("LED-SHIFT",
            #...
        )

        # Test data bit
        fsm.act("BIT-TEST",
            #...
        )

        # Send a 'zero' pulse
        fsm.act("ZERO-SEND",
            #...
        )

        # Send a 'one' pulse
        fsm.act("ONE-SEND",
            #...
        )

        # Shift the current data to get the next bit to test
        # and then, go to BIT-TEST
        fsm.act("BIT-SHIFT",
            #...
        )


# Test -------------------------------------------------------------------------------------------

# Pass the device under test to the testbench
def test(dut):
    loop = 0
    # This is how we set values during simulation
    # Don't forget 'yield', migen won't complain
    yield dut.leds.eq(0xfff)
    yield dut.colors.eq(0xff0000)

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
        ring = RingSerialCtrl(12, 24e6)
        run_simulation(ring, test(ring), clocks={"sys": 1e9/24e6}, vcd_name="sim.vcd")
        exit()

    design = Tuto(platform)
    platform.build(design, build_dir=build_dir)

if __name__ == "__main__":
    main()
