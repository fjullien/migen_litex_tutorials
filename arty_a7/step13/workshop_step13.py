#!/usr/bin/env python3

import argparse

from migen import *

from litex.soc.integration.soc_core import *
from litex.soc.integration.builder import *
from litex.soc.integration.soc import SoCRegion

from litex.soc.cores.clock import *

from litex_boards.platforms import arty

from litex.soc.interconnect import wishbone
from litex.soc.cores.dma import WishboneDMAWriter

from liteeth.phy.mii import LiteEthPHYMII
from liteeth.frontend.stream import LiteEthUDPStreamer
from liteeth.core import LiteEthUDPIPCore

from s2dma import *

# CRG ----------------------------------------------------------------------------------------------

class _CRG(Module):
    def __init__(self, platform, sys_clk_freq):
        self.rst = Signal()
        self.clock_domains.cd_sys       = ClockDomain()
        self.clock_domains.cd_eth       = ClockDomain()

        # # #

        self.submodules.pll = pll = S7PLL(speedgrade=-1)
        self.comb += pll.reset.eq(~platform.request("cpu_reset") | self.rst)
        pll.register_clkin(platform.request("clk100"), 100e6)
        pll.create_clkout(self.cd_sys, sys_clk_freq)
        pll.create_clkout(self.cd_eth, 25e6)

        # Ignore sys_clk to pll.clkin path created by SoC's rst.
        platform.add_false_path_constraints(self.cd_sys.clk, pll.clkin)

        self.comb += platform.request("eth_ref_clk").eq(self.cd_eth.clk)

# BaseSoC ------------------------------------------------------------------------------------------

class BaseSoC(SoCCore):
    def __init__(self, sys_clk_freq=int(100e6), **kwargs):

        platform = arty.Platform(variant="a7-35", toolchain="vivado")

        SoCCore.__init__(self, platform, sys_clk_freq,
            ident         = "LiteX SoC on Arty A7-35",
            **kwargs
        )

        self.submodules.crg = _CRG(platform, sys_clk_freq)

        self.add_ram("sram_udp", 0x20000000, 0x1000)

        self.submodules.ethphy = LiteEthPHYMII(
            clock_pads = self.platform.request("eth_clocks"),
            pads       = self.platform.request("eth"),
            with_hw_init_reset = False)

        self.add_etherbone(phy=self.ethphy, ip_address="192.168.1.98")

        self.submodules.udp_streamer = udp_streamer = LiteEthUDPStreamer(
            self.ethcore_etherbone.udp,
            ip_address = 0,
            udp_port   = 5678,
            cd         = "etherbone"
        )

        # udp_streamer.source is a stream that will transport UDP data payload
        # received on port 5678. It has a simple payload layout: [("data", 8)]
        #
        # You need to add a module that will connect to WishboneDMAWriter sink endpoint
        # which is [("address", adr_width), ("data", 8)]
        #
        # The the S2DMA module will take a stream with 'data' payload (sink)
        # and generate a source stream with 'data' and 'address' as payload
        # 
        #              ┌─────────┐  address ┌────────────────────┐
        #         data │         │  data    │                    │
        # stream ─────►│  S2DMA  ├─────────►│  WishboneDMAWriter ├────► Wishbone
        #              │         │          │                    │
        #              └─────────┘          └────────────────────┘

        # This is the instance of WishboneDMAWriter. It doesn't create its own
        # Wishbone bus so we need to give it one.
        # Then we add this interface as a Wishbone master.
        bus = wishbone.Interface(data_width=8, adr_width=self.bus.address_width)
        self.submodules.udp_dma = udp_dma = WishboneDMAWriter(bus)
        self.bus.add_master("udp_dma", master=bus)

        # This is our 'Stream 2 DMA' module
        self.submodules.s2dma = s2dma = S2DMA(data_width=8,
                                              adr_width=self.bus.address_width,
                                              address = 0x20000000)

        # Here you need to connect every element of the pipeline together.
        # udp_streamer -> s2dma -> udp_dma
        # Always use xxx.from.connect(yyy.to) !
        self.comb += [
            udp_streamer.source.connect(s2dma.sink),
            s2dma.source.connect(udp_dma.sink)
        ]

        #analyzer_signals = [
        #    udp_streamer.source,
        #    s2dma.source,
        #    s2dma.sink,
        #    udp_dma.bus
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
    parser.add_argument("--load",        action="store_true", help="Load bitstream")
    parser.add_argument("--sys-clk-freq",default=100e6,       help="System clock frequency (default: 100MHz)")

    builder_args(parser)

    soc_core_args(parser)

    args = parser.parse_args()

    soc = BaseSoC(
        sys_clk_freq      = int(float(args.sys_clk_freq)),
        **soc_core_argdict(args)
    )

    builder = Builder(soc, csr_csv="csr.csv")

    builder.build(run=args.build)

    if args.load:
        prog = soc.platform.create_programmer()
        prog.load_bitstream(os.path.join(builder.gateware_dir, soc.build_name + ".bit"))
        exit()

if __name__ == "__main__":
    main()
