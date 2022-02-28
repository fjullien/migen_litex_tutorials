#!/usr/bin/env python3

import argparse
import os

from migen import *

from litex.build.generic_platform import *
from litex.build.sim import SimPlatform
from litex.build.sim.config import SimConfig

from litex.soc.integration.soc_core import *
from litex.soc.integration.builder import *

from liteeth.phy.model import LiteEthPHYModel

from ring import *

# IOs ----------------------------------------------------------------------------------------------

_io = [
    ("sys_clk", 0, Pins(1)),
    ("sys_rst", 0, Pins(1)),
    ("serial", 0,
        Subsignal("source_valid", Pins(1)),
        Subsignal("source_ready", Pins(1)),
        Subsignal("source_data",  Pins(8)),

        Subsignal("sink_valid",   Pins(1)),
        Subsignal("sink_ready",   Pins(1)),
        Subsignal("sink_data",    Pins(8)),
    ),
    ("eth_clocks", 0,
        Subsignal("tx", Pins(1)),
        Subsignal("rx", Pins(1)),
    ),
    ("eth", 0,
        Subsignal("source_valid", Pins(1)),
        Subsignal("source_ready", Pins(1)),
        Subsignal("source_data",  Pins(8)),

        Subsignal("sink_valid",   Pins(1)),
        Subsignal("sink_ready",   Pins(1)),
        Subsignal("sink_data",    Pins(8)),
    ),

    # This is the ring data out. Our C++ model will be
    # connected to this pin
    ("data_out", 0, Pins(1)),
]
# Platform -----------------------------------------------------------------------------------------

class Platform(SimPlatform):
    def __init__(self):
        SimPlatform.__init__(self, "SIM", _io)

# BaseSoC ------------------------------------------------------------------------------------------

class BaseSoC(SoCCore):
    def __init__(self, sys_clk_freq=int(100e6), **kwargs):

        platform = Platform()

        SoCCore.__init__(self, platform, sys_clk_freq,
            ident               = "LiteX SoC Simulation",
            ident_version       = True,
            uart_name           = "sim",
            integrated_rom_size = 0x10000,
            **kwargs
        )

        self.submodules.crg = CRG(platform.request("sys_clk"))

        led = RingControl(platform.request("data_out"), mode.DOUBLE, 12, sys_clk_freq, sim=True)
        self.submodules.ledring = led
        self.add_csr("ledring")

        #-------------------------------------------------------------------------------
        # Using the etherbone bridge, we can run litescope on the simulated platform
        #-------------------------------------------------------------------------------

        #self.submodules.ethphy = LiteEthPHYModel(self.platform.request("eth"))
        #self.add_etherbone(phy=self.ethphy, ip_address="192.168.1.98")

        #analyzer_signals = [
        #    led.ring.do,
        #    led.ring.fsm,
        #]

        #from litescope import LiteScopeAnalyzer
        #self.submodules.analyzer = LiteScopeAnalyzer(analyzer_signals,
        #    depth        = 1000,
        #    clock_domain = "sys",
        #    csr_csv      = "analyzer.csv")

# Build --------------------------------------------------------------------------------------------

def main():
    sim_config = SimConfig()
    sys_clk_freq = int(20e6)

    # Needed to create the simulated clock
    sim_config.add_clocker("sys_clk", freq_hz=sys_clk_freq)

    # Needed to create the simulated serial port + terminal
    sim_config.add_module("serial2console", "serial")

    # This is our LedRing model
    sim_config.add_module("ledring", "data_out", args={"freq" : sys_clk_freq})

    # In case we want Ethernet
    #sim_config.add_module("ethernet", "eth", args={"interface": "tap0", "ip": "192.168.1.100"})

    soc     = BaseSoC(sys_clk_freq)
    builder = Builder(soc, csr_csv="csr.csv")
    builder.build(
        extra_mods = ["ledring"],
        extra_mods_path = os.path.abspath(os.getcwd()) + "/modules",
        sim_config=sim_config
    )

if __name__ == "__main__":
    main()
