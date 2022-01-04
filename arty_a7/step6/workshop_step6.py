#!/usr/bin/env python3

from random import *
from migen import *
from ring import *

current_led = 0

# -------------------------------------------------------
# - This functions counts how long dut.do stays high
# -------------------------------------------------------
def get_do_high_length(dut):
    len = 0
    # wait until dut.do == 1
    # while dut.do == 1, increment len
    return len

# ----------------------------------------------
# - This is a generator.
# - If dut.do stays low for more than 50 clocks,
# - current_led is reset
# ----------------------------------------------
def detect_reset(dut):
    # This global variable indicates which led is active
    global current_led

    while True:
        # dut.do stays low for more than 50 clocks -> current_led = 0

        # Let the simuation run
        yield

# ----------------------------------------------
# - This is a generator.
# - It counts dut.do high pulses and measure them
# - to check is a '1' or a '0' is transmitted.
# - The color word is then retreive.
# ----------------------------------------------
def control_out(dut):
    global current_led

    # Bit index in a 24 bit data word
    i = 0

    # Color of the current LED
    color = 0

    while True:
        # Wait a high pulse and get its length
        # count = get_do_high_length

        # Set a variable "bit" according to count
        # it will tell us is a '0' or a '1' is sent

        color = (color << 1) | bit

        # If all 24 bits of the current LED have been shifted
        # then:
            print('Detected LED{} = '.format(current_led) + hex(color))
            # do whatever is needed to update variables

        # Let the simuation run
        yield

# -------------------------------------------------------
# - This is a function that sets dut.led and dut.colors
# -------------------------------------------------------
def set_led_and_color(dut, index):
    # set dut.leds to 1 (LSB) >> index
    # set dut.colors to a random color
    color = randrange(0xffffff)
    print("\nSet      LED{} = 0x{:x}\n".format(index, color))

# -----------------------------------------------------------------------
# - This generator sets led and color and wait for the shift to be done
# -----------------------------------------------------------------------
def change_nb_led_and_color(dut):
    # Do 8 complete Ring control
    for i in range(0, 8):
        #call set_led_and_color(dut, randrange(4))

        # Be sure the shift is started
        # while (dut.done != 1)
        #   continue

        # Be sure the shift is done
        # while (dut.done == 1)
        #   continue

    exit()

# -----------------------------------------------------------------------
# - Run
# -----------------------------------------------------------------------

def main():
        # We use a RingSerialCtrl with 4 LEDs
        ring = RingSerialCtrl(4, 24e6)

        # This is a list of generators that will run in parallel
        generators = {
            "sys" : [ # This will change the "color" and "led" signals every time
                      # the signal "done" is active (this signal has been added.
                      # It indicates when a single LED data shift is done)
                      change_nb_led_and_color(ring),

                      # Here we'll detect when the complete LED shift is done
                      # the data will should stay low for a long time
                      detect_reset(ring),

                      # This will decode '1' and '0' on the data line, shift
                      # all 24 bits to get the LED's data.
                      control_out(ring),
                    ]
        }

        # Run the simulation
        run_simulation(ring, generators, clocks={"sys": 1e9/24e6}, vcd_name="sim.vcd")

if __name__ == "__main__":
    main()
