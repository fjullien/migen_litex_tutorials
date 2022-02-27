#!/usr/bin/env python3

import argparse

from migen import *
from migen.genlib.resetsync import AsyncResetSynchronizer

from litex.soc.integration.soc_core import *
from litex.soc.integration.builder import *

from litex.soc.cores.clock import *

from litex_boards.platforms import arty
from ring import *

# CRG ----------------------------------------------------------------------------------------------

class CRG(Module):
    def __init__(self, platform, sys_clk_freq):
        self.clock_domains.cd_sys   = ClockDomain()
        self.clock_domains.cd_led   = ClockDomain()

        # # #

        clk = platform.request("clk100")
        rst_n = platform.request("cpu_reset")

        self.submodules.pll = pll = S7PLL()

        self.comb += pll.reset.eq(~rst_n)

        pll.register_clkin(clk, 100e6)
        pll.create_clkout(self.cd_sys, sys_clk_freq)
        pll.create_clkout(self.cd_led, 50e6)

        platform.add_period_constraint(clk, 1e9/100e6)

# BaseSoC ------------------------------------------------------------------------------------------

class BaseSoC(SoCCore):
    def __init__(self, sys_clk_freq=int(100e6), mode=mode.DOUBLE, **kwargs):

        platform = arty.Platform(variant="a7-35", toolchain="vivado")

        from litex.build.generic_platform import Pins, IOStandard
        platform.add_extension([("do", 0, Pins("B7"), IOStandard("LVCMOS33"))])

        SoCCore.__init__(self, platform, sys_clk_freq,
            ident         = "LiteX SoC on Arty A7-35",
            **kwargs
        )

        self.submodules.crg = CRG(platform, sys_clk_freq)

        led = ClockDomainsRenamer("led")(RingControl(platform.request("do"), mode, 12, 50e6))
        self.submodules.ledring = led
        self.add_csr("ledring")

# Build --------------------------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="LiteX SoC on Arty A7-35")

    parser.add_argument("--build",       action="store_true", help="Build bitstream")
    parser.add_argument("--mode-single", action="store_true", help="Build bitstream")
    parser.add_argument("--load",        action="store_true", help="Load bitstream")
    parser.add_argument("--flash",       action="store_true", help="Flash Bitstream")
    parser.add_argument("--sys-clk-freq",default=100e6,       help="System clock frequency (default: 100MHz)")

    builder_args(parser)

    soc_core_args(parser)

    args = parser.parse_args()

    m = mode.DOUBLE
    if args.mode_single:
        m = mode.SINGLE

    soc = BaseSoC(
        sys_clk_freq      = int(float(args.sys_clk_freq)),
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
