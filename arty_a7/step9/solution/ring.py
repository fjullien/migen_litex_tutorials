from enum import IntEnum

from migen import *
from migen.genlib.misc import WaitTimer

from litex.soc.interconnect.csr import AutoCSR, CSRStorage

class mode(IntEnum):
    SINGLE = 0
    DOUBLE = 1

class RingControl(Module, AutoCSR):
    def __init__(self, pad, mode, nleds, sys_clk_freq):
        self.color     = CSRStorage(24, reset=0x400000)

        ring = RingSerialCtrl(nleds, sys_clk_freq)
        self.submodules.ring = ring

        ring_timer = WaitTimer(int(0.05*sys_clk_freq))
        self.submodules += ring_timer

        # This is a build time configuration.
        # Here we use a Python 'if/else' statement
        if (mode == mode.DOUBLE):
            print("Led ring controller configured for dual led")
            led_array = Array([
                0b100000100000,
                0b010000010000,
                0b001000001000,
                0b000100000100,
                0b000010000010,
                0b000001000001,
                0b100000100000,
                0b010000010000,
                0b001000001000,
                0b000100000100,
                0b000010000010,
                0b000001000001,
                ]
            )
        else:
            print("Led ring controller configured for single led")
            led_array = Array([
                0b100000000000,
                0b010000000000,
                0b001000000000,
                0b000100000000,
                0b000010000000,
                0b000001000000,
                0b000000100000,
                0b000000010000,
                0b000000001000,
                0b000000000100,
                0b000000000010,
                0b000000000001,
                ]
            )

        index = Signal(12, reset=1)

        # We want the timer to stop as soon as 'done' is set.
        # If we reset 'wait' in the sync block, 'done' will be
        # high during 2 clock cycles and our index value
        # will be incremented two times.
        self.comb += ring_timer.wait.eq(~ring_timer.done)

        # Use index as an index to an array
        self.sync += [
            If(ring_timer.done,
                index.eq(index + 1),
                If(index == 11,
                    index.eq(0)
                ),
            ),
        ]

        self.comb += ring.leds.eq(led_array[index])

        self.comb += [
            ring.colors.eq(self.color.storage),
            pad.eq(ring.do)
        ]

        # Debug signals (for LiteScope/ILA obervation)
        self.dbg = [
            index,
            self.color.storage
        ]

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

        # Debug signals (for LiteScope/ILA obervation)
        self.dbg = [
            bit_count,
            trst_timer.wait,
        ]