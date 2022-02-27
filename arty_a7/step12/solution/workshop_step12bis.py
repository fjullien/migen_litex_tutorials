#!/usr/bin/env python3

import argparse

from migen import *

from litex.soc.integration.soc_core import *
from litex.soc.integration.builder import *
from litex.soc.integration.soc import SoCRegion

from litex.soc.cores.clock import *

# We know use the available Arty platform which is in litex_boards
from litex_boards.platforms import arty

# For the DDR3 controller
from litedram.modules import MT41K128M16
from litedram.phy import s7ddrphy

# This is for etherbone
from liteeth.phy.mii import LiteEthPHYMII

from ringbis import *

# CRG ----------------------------------------------------------------------------------------------

class _CRG(Module):
    def __init__(self, platform, sys_clk_freq):
        self.rst = Signal()
        self.clock_domains.cd_sys       = ClockDomain()
        self.clock_domains.cd_sys4x     = ClockDomain(reset_less=True)
        self.clock_domains.cd_sys4x_dqs = ClockDomain(reset_less=True)
        self.clock_domains.cd_idelay    = ClockDomain()
        self.clock_domains.cd_eth       = ClockDomain()

        # # #

        self.submodules.pll = pll = S7PLL(speedgrade=-1)
        self.comb += pll.reset.eq(~platform.request("cpu_reset") | self.rst)
        pll.register_clkin(platform.request("clk100"), 100e6)
        pll.create_clkout(self.cd_sys,       sys_clk_freq)
        pll.create_clkout(self.cd_sys4x,     4*sys_clk_freq)
        pll.create_clkout(self.cd_sys4x_dqs, 4*sys_clk_freq, phase=90)
        pll.create_clkout(self.cd_idelay,    200e6)
        pll.create_clkout(self.cd_eth,       25e6)

        # Ignore sys_clk to pll.clkin path created by SoC's rst.
        platform.add_false_path_constraints(self.cd_sys.clk, pll.clkin)

        self.submodules.idelayctrl = S7IDELAYCTRL(self.cd_idelay)

        self.comb += platform.request("eth_ref_clk").eq(self.cd_eth.clk)

# BaseSoC ------------------------------------------------------------------------------------------

class BaseSoC(SoCCore):
    def __init__(self, sys_clk_freq=int(100e6), mode=mode.DOUBLE, **kwargs):

        platform = arty.Platform(variant="a7-35", toolchain="vivado")

        SoCCore.__init__(self, platform, sys_clk_freq,
            ident         = "LiteX SoC on Arty A7-35",
            **kwargs
        )

        self.submodules.crg = _CRG(platform, sys_clk_freq)

        # DDR3 SDRAM -------------------------------------------------------------------------------
        if not self.integrated_main_ram_size:
            self.submodules.ddrphy = s7ddrphy.A7DDRPHY(platform.request("ddram"),
                memtype        = "DDR3",
                nphases        = 4,
                sys_clk_freq   = sys_clk_freq)
            self.add_sdram("sdram",
                phy           = self.ddrphy,
                module        = MT41K128M16(sys_clk_freq, "1:4"),
                l2_cache_size = kwargs.get("l2_size", 8192)
            )

        # Here we add the data out pin of the LED ring
        from litex.build.generic_platform import Pins, IOStandard
        platform.add_extension([("do", 0, Pins("B7"), IOStandard("LVCMOS33"))])

        led = RingControl(platform.request("do"), mode, 12, sys_clk_freq)
        self.submodules.ledring = led

        self.bus.add_master(name="ledring", master=self.ledring.bus)

       ##Ethernet PHY and Etherbone
       #self.submodules.ethphy = LiteEthPHYMII(
       #    clock_pads = self.platform.request("eth_clocks"),
       #    pads       = self.platform.request("eth"))

       ## Change the address here
       #self.add_etherbone(phy=self.ethphy, ip_address="192.168.1.98")

       #analyzer_signals = [
       #    led.bus
       #]

       #from litescope import LiteScopeAnalyzer
       #self.submodules.analyzer = LiteScopeAnalyzer(
       #            analyzer_signals,
       #            depth        = 512,
       #            clock_domain ="sys",
       #            csr_csv      = "analyzer.csv"
       #)
       #self.add_csr("analyzer")

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
