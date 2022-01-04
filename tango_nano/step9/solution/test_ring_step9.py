#!/usr/bin/env python3

import argparse

from migen import *
from migen.genlib.resetsync import AsyncResetSynchronizer

from litex.soc.integration.soc_core import *
from litex.soc.integration.builder import *

from platform_tango import *
from ring import *

# CRG ----------------------------------------------------------------------------------------------

class CRG(Module):
    def __init__(self, platform, sys_clk_freq):
        self.rst = Signal()
        self.clock_domains.cd_sys   = ClockDomain()

        # # #

        clk = platform.request("sys_clk")
        rst_n = platform.request("user_btn", 0)

        self.comb += self.cd_sys.clk.eq(clk)
        self.specials += AsyncResetSynchronizer(self.cd_sys, ~rst_n)

        platform.add_period_constraint(clk, 1e9/sys_clk_freq)

# BaseSoC ------------------------------------------------------------------------------------------

class BaseSoC(SoCMini):
    def __init__(self, sys_clk_freq=int(24e6), mode=mode.DOUBLE, **kwargs):

        platform = Platform()

        SoCMini.__init__(self, platform, sys_clk_freq,
            ident         = "LiteX SoC on Tang Nano",
            ident_version = True)

        self.submodules.crg = CRG(platform, sys_clk_freq)

        led = RingControl(platform.request("do"), mode, 12, sys_clk_freq)
        self.submodules.ledring = led
        self.add_csr("ledring")

        self.add_uartbone(baudrate=int(1e6)) 

        analyzer_signals = []
        analyzer_signals += led.dbg
        analyzer_signals += led.ring.dbg

        from litescope import LiteScopeAnalyzer
        self.submodules.analyzer = LiteScopeAnalyzer(
                    analyzer_signals,
                    depth        = 16,
                    clock_domain ="sys",
                    csr_csv      = "analyzer.csv"
        )
        self.add_csr("analyzer")


# Build --------------------------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="LiteX SoC on Tang Nano")

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
        sys_clk_freq      = 24e6,
        mode              = m,
        **soc_core_argdict(args)
    )

    builder = Builder(soc, **builder_argdict(args))

    builder.build(run=args.build)

    if args.load:
        prog = soc.platform.create_programmer()
        prog.load_bitstream(os.path.join(builder.gateware_dir, "impl", "pnr", "project.fs"))

    if args.flash:
        prog = soc.platform.create_programmer()
        prog.flash(0, os.path.join(builder.gateware_dir, "impl", "pnr", "project.fs"))

if __name__ == "__main__":
    main()
