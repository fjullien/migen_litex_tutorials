#!/usr/bin/env python3

# This is for argument parsing
import argparse

from migen import *
from migen.genlib.resetsync import AsyncResetSynchronizer

from litex.soc.integration.soc_core import *
from litex.soc.integration.builder import *

from litex_boards.platforms import arty

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

# This SoC is based on SoCMini.
# It has no CPU
class BaseSoC(SoCMini):
    def __init__(self, sys_clk_freq=int(100e6), **kwargs):

        # We need to pass a Platform to our SoC
        platform = arty.Platform(variant="a7-35", toolchain="vivado")

        from litex.build.generic_platform import Pins, IOStandard
        platform.add_extension([("do", 0, Pins("B7"), IOStandard("LVCMOS33"))])

        # Instance of our SoC
        # It will have:
        # - a system controller module
        # - an identifier module
        SoCMini.__init__(self, platform, sys_clk_freq,
            ident         = "LiteX SoC on Arty A7-35",
            ident_version = True)

        # This is a mandatory module
        # It should a least provides self.clock_domains.cd_sys   = ClockDomain()
        self.submodules.crg = CRG(platform, sys_clk_freq)

        # uartbone will allow us to access the wishbone bus of the SoC from the
        # UART. By default, add_uartbone will request "serial" resources.

        #                             ┌──────────┐    ┌────────┐
        #                             │          │◄──►│  ctrl  │
        #            ┌──────────┐     │ Wishbone │    └────────┘
        # UART ◄────►│ uartbone │◄───►│ crossbar │
        #            └──────────┘     │          │    ┌────────────┐
        #                             │          │◄──►│ identifier │
        #                             │          │    └────────────┘
        #                             │          │
        #                             └──────────┘

        # Default baudrate is 115200
        self.add_uartbone() 

# Build --------------------------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="LiteX SoC on Arty A7-35")

    # Those are local arguments. They are used in the main function
    parser.add_argument("--build", action="store_true", help="Build bitstream")
    parser.add_argument("--load",  action="store_true", help="Load bitstream")
    parser.add_argument("--flash", action="store_true", help="Flash Bitstream")

    # The builder adds its own arguments
    builder_args(parser)

    # The SoCCore adds its own arguments
    soc_core_args(parser)

    # Inspects the command line and convert each argument to the appropriate type
    # and then invoke the appropriate action
    args = parser.parse_args()

    # Pass arguments to the SoC constructor
    soc = BaseSoC(
        sys_clk_freq      = 100e6,
        **soc_core_argdict(args)
    )

    # Pass arguments to the Builder constructor
    builder = Builder(soc, **builder_argdict(args))

    # Build the project only if args.build == True, i.e. --build
    builder.build(run=args.build)

    # If --load, load the bitstream
    if args.load:
        prog = soc.platform.create_programmer()
        prog.load_bitstream(os.path.join(builder.gateware_dir, soc.build_name + ".bit"))
        exit()

if __name__ == "__main__":
    main()
