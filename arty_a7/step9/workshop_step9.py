#!/usr/bin/env python3

import argparse

from migen import *
from migen.genlib.resetsync import AsyncResetSynchronizer

from litex.soc.integration.soc_core import *
from litex.soc.integration.builder import *

from litex_boards.platforms import arty
from ring import *

# CRG ----------------------------------------------------------------------------------------------

class CRG(Module):
    def __init__(self, platform, sys_clk_freq):
        self.rst = Signal()
        self.clock_domains.cd_sys   = ClockDomain()

        # # #

        clk = platform.request("clk100")
        rst_n = platform.request("cpu_reset")

        self.comb += self.cd_sys.clk.eq(clk)
        self.specials += AsyncResetSynchronizer(self.cd_sys, ~rst_n)

        platform.add_period_constraint(clk, 1e9/100e6)

# BaseSoC ------------------------------------------------------------------------------------------

class BaseSoC(SoCMini):
    def __init__(self, sys_clk_freq=int(100e6), mode=mode.DOUBLE, **kwargs):

        platform = arty.Platform(variant="a7-35", toolchain="vivado")

        from litex.build.generic_platform import Pins, IOStandard
        platform.add_extension([("do", 0, Pins("B7"), IOStandard("LVCMOS33"))])

        SoCMini.__init__(self, platform, sys_clk_freq,
            ident         = "LiteX SoC on Arty A7-35",
            ident_version = True)

        self.submodules.crg = CRG(platform, sys_clk_freq)

        led = RingControl(platform.request("do"), mode, 12, sys_clk_freq)
        self.submodules.ledring = led
        self.add_csr("ledring")

        self.add_uartbone() 

        # Add your signals here
        analyzer_signals = []

        # Add your instance of LiteScopeAnalyzer here after
        # Don't forget to add csr for your analyzer module
        from litescope import LiteScopeAnalyzer

# Build --------------------------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="LiteX SoC on Arty A7-35")

    parser.add_argument("--build",       action="store_true", help="Build bitstream")
    parser.add_argument("--mode-single", action="store_true", help="Build bitstream")
    parser.add_argument("--load",        action="store_true", help="Load bitstream")
    parser.add_argument("--flash",       action="store_true", help="Flash Bitstream")

    builder_args(parser)

    soc_core_args(parser)

    args = parser.parse_args()

    m = mode.DOUBLE
    if args.mode_single:
        m = mode.SINGLE

    soc = BaseSoC(
        sys_clk_freq      = 100e6,
        mode              = m,
        **soc_core_argdict(args)
    )

    builder = Builder(soc, **builder_argdict(args))

    builder.build(run=args.build)

    if args.load:
        prog = soc.platform.create_programmer()
        prog.load_bitstream(os.path.join(builder.gateware_dir, soc.build_name + ".bit"))
        exit()

if __name__ == "__main__":
    main()
