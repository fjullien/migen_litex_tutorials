#!/usr/bin/env python3

import argparse

from migen import *
from migen.genlib.resetsync import AsyncResetSynchronizer

from litex.soc.integration.soc_core import *
from litex.soc.integration.builder import *

# In order to use PLLs
from litex.soc.cores.clock import *

from litex_boards.platforms import arty
from ring import *

# CRG ----------------------------------------------------------------------------------------------

class CRG(Module):
    def __init__(self, platform, sys_clk_freq):
        self.clock_domains.cd_sys = ClockDomain()
        # Add a led clock domain here

        # # #

        clk = platform.request("clk100")
        rst_n = platform.request("cpu_reset")

        # Add a pll, 7 series FPGA pll are S7PLL() and use register_clkin and
        # create_clkout methods to create assign clock signals.








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

        # Use ClockDomainsRenamer to put RingControl in the "led" clock domain
        # Don't forget that csr register are always in "sys" clock domain
        led = RingControl(platform.request("do"), mode, 12, 50e6)
        self.submodules.ledring = led
        self.add_csr("ledring")

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
        sys_clk_freq      = int(60e6),
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
