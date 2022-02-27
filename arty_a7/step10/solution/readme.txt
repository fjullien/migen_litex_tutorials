./workshop_step10.py --integrated-rom-size 0x10000 --integrated-main-ram 0x10000 --csr-csv csr.csv --build
./workshop_step10.py --integrated-rom-size 0x10000 --integrated-main-ram 0x10000 --csr-csv csr.csv --load
litex_term --kernel=src/demo.bin /dev/ttyUSB3

./workshop_step10.py --integrated-main-ram 0x10000 --no-compile-software --integrated-rom-size 0x10000 --integrated-rom-init src/demo-rom.bin --build --load
./workshop_step10.py --integrated-main-ram 0x10000 --no-compile-software --integrated-rom-size 0x10000 --integrated-rom-init src/demo-rom.bin --load