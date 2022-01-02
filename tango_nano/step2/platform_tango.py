from migen import *

from litex.build.generic_platform import *
from litex.build.gowin.platform import GowinPlatform
from litex.build.openfpgaloader import OpenFPGALoader

# IOs ----------------------------------------------------------------------------------------------

_io = [
    # Clk / Rst
    ("sys_clk",  0, Pins("35"), IOStandard("LVCMOS33")),

    # Leds
    ("user_led", 0, Pins("16"), IOStandard("LVCMOS33")),
    ("user_led", 1, Pins("17"), IOStandard("LVCMOS33")),
    ("user_led", 2, Pins("18"), IOStandard("LVCMOS33")),

    # Buttons.
    ("user_btn", 0, Pins("15"),  IOStandard("LVCMOS33")),
    ("user_btn", 1, Pins("14"),  IOStandard("LVCMOS33")),

    # Ring DI
    ("do", 0, Pins("23"), IOStandard("LVCMOS33")),

    # Serial
    ("serial", 0,
        Subsignal("tx", Pins("8")),
        Subsignal("rx", Pins("9")),
        IOStandard("LVCMOS33")
    ),
]

# Platform -----------------------------------------------------------------------------------------

class Platform(GowinPlatform):
    def __init__(self):
        GowinPlatform.__init__(self, "GW1N-LV1QN48C6/I5", _io, [], toolchain="gowin", devicename="GW1N-1")
        self.toolchain.options["use_done_as_gpio"] = 1
        self.toolchain.options["use_reconfign_as_gpio"] = 1

    def create_programmer(self):
        return OpenFPGALoader("tangnano")
