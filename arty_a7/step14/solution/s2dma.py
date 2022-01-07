from migen import *

from litex.soc.interconnect import stream

class S2DMA(Module):
    def __init__(self, data_width, adr_width, address=0):
        # Stream interfaces
        self.sink   = sink = stream.Endpoint([("data", 8)])
        self.source = source = stream.Endpoint([("address", adr_width), ("data", data_width)])

        ###

        addr = Signal(adr_width, reset=address)

        self.comb += [
            source.data.eq(sink.data),
            source.address.eq(addr),
            source.valid.eq(sink.valid),
            sink.ready.eq(source.ready),
        ]

        # Or we can use connect with 'omit'.
        # It means: connect everything except signals listed in 'omit'.
        # There is also 'keep' which means: connect nothing but signals listed in 'keep'.
        #
        # Always use xxx.from.connect(yyy.to) !
        # Here data go from sink which is the input to source which is the output

        #self.comb += [
        #    sink.connect(source, omit={"address"}),
        #    source.address.eq(addr),
        #]

        self.sync += [
            # Make sure the data is valid
            If(sink.valid & sink.ready,
                addr.eq(addr + 1),
                # If this data is the last of this stream
                If(sink.last,
                    addr.eq(address)
                )
            ),
        ]
