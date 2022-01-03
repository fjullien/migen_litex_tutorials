#!/usr/bin/env python3

# This is for argument parsing
import argparse

from migen import *
from migen.genlib.resetsync import AsyncResetSynchronizer

from litex.soc.integration.soc_core import *
from litex.soc.integration.builder import *

from platform_tango import *

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

# This SoC is based on SoCMini.
# It has no CPU
class BaseSoC(SoCMini):
    def __init__(self, sys_clk_freq=int(24e6), **kwargs):

        # We need to pass a Platform to our SoC
        platform = Platform()

        # Instance of our SoC
        # It will have:
        # - a system controller module
        # - an identifier module
        SoCMini.__init__(self, platform, sys_clk_freq,
            ident         = "LiteX SoC on Tang Nano",
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

        # CH552 firmware does not support traditional baudrates.
        self.add_uartbone(baudrate=int(1e6)) 

# Build --------------------------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="LiteX SoC on Tang Nano")

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
        sys_clk_freq      = 24e6,
        **soc_core_argdict(args)
    )

    # Pass arguments to the Builder constructor
    builder = Builder(soc, **builder_argdict(args))

    # Build the project only if args.build == True, i.e. --build
    builder.build(run=args.build)

    # If --load, load the bitstream
    if args.load:
        prog = soc.platform.create_programmer()
        prog.load_bitstream(os.path.join(builder.gateware_dir, "impl", "pnr", "project.fs"))

    # If --flash, flash the bitstream
    if args.flash:
        prog = soc.platform.create_programmer()
        prog.flash(0, os.path.join(builder.gateware_dir, "impl", "pnr", "project.fs"))

if __name__ == "__main__":
    main()
