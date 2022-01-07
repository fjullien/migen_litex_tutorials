from migen import *

from litex.soc.interconnect import stream

class S2DMA(Module):
    def __init__(self, data_width, adr_width, address=0):
        # Stream interfaces
        self.sink   = sink = stream.Endpoint([("data", 8)])
        self.source = source = stream.Endpoint([("address", adr_width), ("data", data_width)])

        ###

        #            ┌─────────────┐
        # ready  ◄───┤             │◄─── ready
        #            │             │
        #            │             │
        # valid  ───►│             ├───► valid
        #            │             │
        #            │             │
        # data   ───►│             ├───► data
        #            │             │
        #            │             │
        # last   ───►│             ├───► address
        #            └─────────────┘

        # You need to connect sink and sources signals and add some logic to control
        # the address of the source stream.

        self.comb += []

        self.sync += []
