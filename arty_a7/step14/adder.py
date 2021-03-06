from migen import *

from litex.soc.interconnect import stream

# This is the module generated by litex_read_verilog.
# We can't use it directly because it doesn't have
# stream endpoints.
# We could add endpoints directly here but lets do this in
# another module (StreamAddOne)

# !!!!!!!!!! Your module from verilog here !!!!!!!!

class StreamAddOne(Module):
    def __init__(self):
        # Stream interfaces
        self.sink   = sink = stream.Endpoint([("data", 8)])
        self.source = source = stream.Endpoint([("data", 8)])

        # # #

        # Instantiate your module and connect it to stream endpoints

