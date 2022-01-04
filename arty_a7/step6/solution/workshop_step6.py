#!/usr/bin/env python3

from random import *

from migen import *
from ring import *

current_led   = 0

# -------------------------------------------------------
# - This functions counts how long dut.do stays high
# -------------------------------------------------------
def get_do_high_length(dut):
    count = 0
    while (yield dut.do != 1):
        yield
    while (yield dut.do != 0):
        count = count + 1
        yield
    return count

# ----------------------------------------------
# - This is a generator.
# - If dut.do stays low for more than 50 clocks,
# - current_led is reset
# ----------------------------------------------
def detect_reset(dut):
    global current_led
    count = 0
    while True:
        while (yield dut.do == 0):
            count = count + 1
            if count > 50:
                current_led = 0
            yield
        count = 0
        yield

# ----------------------------------------------
# - This is a generator.
# - It counts dut.do high pulses and measure them
# - to check is a '1' or a '0' is transmitted.
# - The color word is then retreive.
# ----------------------------------------------
def control_out(dut):
    global current_led
    i = 0
    color = 0
    while True:
        count = (yield from get_do_high_length(dut))

        bit = 1
        if count == 9:
            bit = 0

        color = (color << 1) | bit

        i = i + 1
        if i == 24:
            print('Detected LED{} = '.format(current_led) + hex(color))
            color = 0
            i = 0
            current_led = current_led + 1

        yield

# -------------------------------------------------------
# - This is a function that sets dut.led and dut.colors
# -------------------------------------------------------
def set_led_and_color(dut, index):
    yield dut.leds.eq(0x800 >> index)
    color = randrange(0xFFFFFF)
    yield dut.colors.eq(color)
    print("\nSet      LED{} = 0x{:x}\n".format(index, color))

# -----------------------------------------------------------------------
# - This generator sets led and color and wait for the shift to be done
# -----------------------------------------------------------------------
def change_nb_led_and_color(dut):
    for i in range(0, 8):
        yield from set_led_and_color(dut, randrange(4))
        while (yield dut.done != 1):
            yield
        while (yield dut.done):
            yield
    exit()

# -----------------------------------------------------------------------
# - Run
# -----------------------------------------------------------------------

def main():
        ring = RingSerialCtrl(4, 24e6)

        generators = {
            "sys" : [ change_nb_led_and_color(ring),
                      control_out(ring),
                      detect_reset(ring),
                    ]
        }

        run_simulation(ring, generators, clocks={"sys": 1e9/24e6}, vcd_name="sim.vcd")

if __name__ == "__main__":
    main()
