from migen import *

from litex.build.generic_platform import *
from litex.build.xilinx import XilinxPlatform
from litex.build.openocd import OpenOCD

# IOs ----------------------------------------------------------------------------------------------

_io = [
    # Clk / Rst
    ("clk100",    0, Pins("E3"), IOStandard("LVCMOS33")),
    ("cpu_reset", 0, Pins("C2"), IOStandard("LVCMOS33")),

    # Leds
    ("user_led", 0, Pins("H5"),  IOStandard("LVCMOS33")),
    ("user_led", 1, Pins("J5"),  IOStandard("LVCMOS33")),
    ("user_led", 2, Pins("T9"),  IOStandard("LVCMOS33")),
    ("user_led", 3, Pins("T10"), IOStandard("LVCMOS33")),

    # Serial
    ("serial", 0,
        Subsignal("tx", Pins("D10")),
        Subsignal("rx", Pins("A9")),
        IOStandard("LVCMOS33")
    ),

]

# Platform -----------------------------------------------------------------------------------------

class Platform(XilinxPlatform):
    default_clk_name   = "clk100"
    default_clk_period = 1e9/100e6

    def __init__(self, toolchain="vivado"):
        XilinxPlatform.__init__(self, "xc7a35ticsg324-1L", _io, [], toolchain=toolchain)
        self.toolchain.bitstream_commands = \
            ["set_property BITSTREAM.CONFIG.SPI_BUSWIDTH 4 [current_design]"]
        self.toolchain.additional_commands = \
            ["write_cfgmem -force -format bin -interface spix4 -size 16 "
             "-loadbit \"up 0x0 {build_name}.bit\" -file {build_name}.bin"]
        self.add_platform_command("set_property INTERNAL_VREF 0.675 [get_iobanks 34]")

    def create_programmer(self):
        return OpenOCD("openocd_xc7_ft2232.cfg", "bscan_spi_xc7a35t.bit")
