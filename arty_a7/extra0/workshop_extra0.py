#!/usr/bin/env python3

from migen import *
from migen.genlib.cdc import *

from litex.build.generic_platform import *
from litex_boards.platforms import arty

def delay(self, delay, input, output):
    r = Signal(delay)
    for i in range(delay):
        if i == 0:
            self.sync += r[0].eq(input)
        else:
            self.sync += r[i].eq(r[i-1])

    self.comb += output.eq(r[delay-1])

class Compute(Module):
    def __init__(self, pipeline):
        self.out          = Signal(4)
        self.out_valid    = Signal()
        self.input1       = Signal(4)
        self.input1_valid = Signal()
        self.input2       = Signal(4)
        self.input2_valid = Signal()

        ###

        a = Signal(32)
        b = Signal(32)

        if pipeline == False:

            self.comb += a.eq((self.input1 * 0x99887733) +                 # a1--+---a11----+-----a111------+--- b
                              (self.input1 * 0x11223344) +                 # a2--+          |               |
                                                                           #                |               |
                              (self.input1 * 0x55667788) +                 # a3--+---a12----+               |
                              (self.input2 * Replicate(self.input1, 8)) +  # a4--+                          |
                                                                           #                                |
                              (self.input1 * 0x99aabbcc) +                 # a5--+---a13----------a112------+
                              0x12345678)                                  # ----+

            self.sync += b.eq(a)
            self.comb += self.out.eq(b[0:4] ^ b[4:8] ^ b[8:12] ^ b[12:16] ^ b[16:20] ^ b[20:24] ^ b[24:28] ^ b[28:32])

            delay(self, 1, self.input1_valid & self.input2_valid, self.out_valid)

        else:
            # Write a pipelined version here.
            pass


# Design -------------------------------------------------------------------------------------------

class TestPipeline(Module):
    def __init__(self, platform, pipeline):

        # Get pin from ressources
        clk = platform.request("clk100")
        leds = platform.request_all("user_led")

        btn = platform.request_all("user_btn")
        btn_sync = Signal(len(btn))
        for i in range(len(btn)):
            self.specials += MultiReg(btn[i], btn_sync[i])


        sw = platform.request_all("user_sw")
        sw_sync = Signal(len(sw))
        for i in range(len(sw)):
            self.specials += MultiReg(sw[i], sw_sync[i])

        crg = CRG(clk)
        self.submodules.crg = crg

        cnt = Signal(32)
        compute = Compute(pipeline)
        self.submodules += compute
        self.sync += cnt.eq(cnt + 1)
        self.comb += [
            compute.input1.eq(cnt),
            compute.input2.eq(btn_sync),
            compute.input1_valid.eq(1),
            compute.input2_valid.eq(1),
            leds.eq(compute.out)
        ]

# Test -------------------------------------------------------------------------------------------

def test(dut):
    loop = 0
    yield dut.input1_valid.eq(1)
    yield dut.input2_valid.eq(1)
    yield dut.input1.eq(5)
    yield dut.input2.eq(6)
    yield

    yield dut.input1.eq(8)
    yield dut.input2.eq(8)
    yield

    yield dut.input1.eq(9)
    yield dut.input2.eq(4)
    yield

    yield dut.input1_valid.eq(0)
    yield dut.input2_valid.eq(0)
    yield dut.input1.eq(0)
    yield dut.input2.eq(0)

    for i in range(20):
        yield

# Build -------------------------------------------------------------------------------------------

def main():

    pipeline = False
    if "pipe" in sys.argv[1: ]:
        pipeline = True

    build_dir="gateware"
    platform = arty.Platform(variant="a7-35", toolchain="vivado")
    design = TestPipeline(platform, pipeline)

    if "sim" in sys.argv[1: ]:
        dut = Compute(pipeline)
        run_simulation(dut, test(dut), clocks={"sys": 1e9/100e6}, vcd_name="sim.vcd")
        exit()

    platform.build(design, build_dir=build_dir)

if __name__ == "__main__":
    main()
