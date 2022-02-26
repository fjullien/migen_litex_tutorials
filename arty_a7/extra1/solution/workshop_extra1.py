#!/usr/bin/env python3

from migen import *
from migen.genlib.cdc import *

from litex.soc.interconnect import stream

from litex.build.generic_platform import *
from litex_boards.platforms import arty

from litex.soc.cores.clock import *

# We want to continuously stream the memory content (looping over its address).
# The memory content is initialized with default values and there is a writer port
# to allow its modification.
# The writer port operates in the "sys" clock domain (100MHz) and the streaming is
# clocked by the "ser" clock domain at 150MHz.

#                                                       100MHz  │  150MHz
#                                                               │
#              ┌────────────┐     ┌───────────────┐    ┌────────┴─────────┐
#              │  Dual port │     │  readport to  │    │                  │
# writer   ───►│            ├────►│               ├───►│ stream.AsyncFIFO ├────►  output
#              │   memory   │     │    stream     │    │                  │
#              └────────────┘     └───────────────┘    └────────┬─────────┘
#                                                               │
#                                                               │

# This is the layout of the writer port
writer_layout = [
    ("address", 12),
    ("data", 32),
    ("valid", 1)
]

# This is the layout of the output stream
stream_layout = [
    ("address", 4),
    ("data", 32)
]

# These are the initialization data
init_data = [
    0x1, 0x11223344,
    0x0, 0x66998855,
    0x1, 0x00000000,
    0x4, 0x00000044,
    0x8, 0x00000000,
    0x5, 0x0000000A,
    0x1, 0xFF000000
]

#------------------------------------------------
#-
#-          Clock and reset
#-
#------------------------------------------------
class CRG(Module):
    def __init__(self, platform, sys_clk_freq=100e6):
        self.clock_domains.cd_sys   = ClockDomain()
        self.clock_domains.cd_ser   = ClockDomain()

        # # #

        clk = platform.request("clk100")
        rst_n = platform.request("cpu_reset")

        self.submodules.pll = pll = S7PLL()

        self.comb += pll.reset.eq(~rst_n)

        pll.register_clkin(clk, 100e6)
        pll.create_clkout(self.cd_sys, sys_clk_freq)
        pll.create_clkout(self.cd_ser, 150e6)

        platform.add_period_constraint(clk, 1e9/100e6)
        platform.add_false_path_constraints(self.cd_sys.clk, self.cd_ser.clk)

#------------------------------------------------
#-
#-          The module
#-
#------------------------------------------------
class WorkshopMem(Module):
    def __init__(self, init_data):
        self.source = source = stream.Endpoint(stream_layout)
        self.writer = writer = Record(writer_layout)

        ###

        #------------------------------------------------
        #-          Dual port memory
        #------------------------------------------------

        mem = Memory(32, len(init_data), init=init_data)
        rport = mem.get_port(async_read=True)
        wport = mem.get_port(write_capable=True)
        self.specials += mem, rport, wport

        # This port is directly controlled by the writer port
        self.comb += [
            wport.adr.eq(writer.address),
            wport.dat_w.eq(writer.data),
            wport.we.eq(writer.valid),
        ]

        #------------------------------------------------
        #-          Asynchronous stream FIFO
        #------------------------------------------------

        self.submodules.fifo = fifo = stream.AsyncFIFO(stream_layout, depth=32, buffered=False)
        self.comb += fifo.source.connect(source)

        #------------------------------------------------
        #-          Memory read port to stream
        #------------------------------------------------

        read_addr = Signal(32)
        self.comb += rport.adr.eq(read_addr)

        fsm = FSM(reset_state="GET_ADDR")
        self.submodules += fsm

        fsm.act("GET_ADDR",
            NextValue(fifo.sink.valid, 0),
            NextValue(fifo.sink.address, rport.dat_r),
            NextValue(read_addr, read_addr + 1),
            NextState("GET_VALUE")
        )

        fsm.act("GET_VALUE",
            NextValue(fifo.sink.data, rport.dat_r),
            NextValue(fifo.sink.valid, 1),
            If(fifo.sink.ready,
                If(read_addr == (len(init_data)-1),
                    NextValue(read_addr, 0)
                ).Else(
                    NextValue(read_addr, read_addr + 1),
                ),
                NextState("GET_ADDR")
            )
        )

#------------------------------------------------
#-
#-    Use the module on the Arty platform
#-
#------------------------------------------------
class TestMemory(Module):
    def __init__(self, platform, init_data):

        # Get pin from ressources
        leds = platform.request_all("user_led")

        btn = platform.request_all("user_btn")
        btn_sync = Signal(len(btn))
        for i in range(len(btn)):
            self.specials += MultiReg(btn[i], btn_sync[i])

        sw = platform.request_all("user_sw")
        sw_sync = Signal(len(sw))
        for i in range(len(sw)):
            self.specials += MultiReg(sw[i], sw_sync[i])

        self.submodules.crg = CRG(platform)

        cnt = Signal(32)
        memstream = WorkshopMem(init_data)
        self.submodules += ClockDomainsRenamer({"write": "sys", "read": "ser"})(memstream)
        self.sync += cnt.eq(cnt + 1)
        self.comb += [
            memstream.writer.valid.eq(cnt[0]),
            memstream.writer.address.eq(btn_sync),
            memstream.writer.data.eq(Replicate(sw_sync, 8)),

            memstream.source.ready.eq(sw_sync[0]),
            leds.eq(memstream.source.data[0:4]   ^ memstream.source.data[4:8] ^
                    memstream.source.data[8:12]  ^ memstream.source.data[12:16] ^
                    memstream.source.data[16:20] ^ memstream.source.data[20:24] ^
                    memstream.source.data[24:28] ^ memstream.source.data[28:32] ^
                    memstream.source.data[24:28] ^ memstream.source.data[28:32] ^
                    memstream.source.address ^ memstream.source.valid
            )
        ]

#------------------------------------------------
#-
#-    Testbench
#-
#------------------------------------------------

def write_ram(dut, addr, value):
    yield dut.writer.address.eq(addr)
    yield dut.writer.data.eq(value)
    yield dut.writer.valid.eq(1)
    yield
    yield dut.writer.valid.eq(0)
    yield

def test(dut):
    for i in range(500):
        # At some point in time, the sink connected
        # to the fifo source can't receive data
        if (i > 200) and (i < 300):
            yield dut.source.ready.eq(0)
        else:
            yield dut.source.ready.eq(1)

        # Here we change a value in memory
        if i == 280:
            yield from write_ram(dut, 11, 0xAABBCCDD)

        yield


#------------------------------------------------
#-
#-    Build / Sim
#-
#------------------------------------------------
def main():
    if "sim" in sys.argv[1: ]:
        dut = ClockDomainsRenamer({"write": "sys", "read": "sclk"})(WorkshopMem(init_data))
        run_simulation(dut, test(dut), clocks={"sys": 1e9/10e6, "sclk": 1e9/100e6}, vcd_name="sim.vcd")
        exit()

    build_dir="gateware"
    platform = arty.Platform(variant="a7-35", toolchain="vivado")
    design = TestMemory(platform, init_data) 
    platform.build(design, build_dir=build_dir)

if __name__ == "__main__":
    main()
