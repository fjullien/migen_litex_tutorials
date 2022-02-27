BUILD_DIR?=../build/digilent_arty/

include $(BUILD_DIR)/software/include/generated/variables.mak
include $(SOC_DIRECTORY)/software/common.mak

OBJECTS   = isr.o main.o crt0.o

all: demo.bin demo-rom.bin

# pull in dependency info for *existing* .o files
-include $(OBJECTS:.o=.d)

%.bin: %.elf
	$(OBJCOPY) -O binary $< $@
	chmod -x $@

demo.elf: $(OBJECTS)
	$(CC) $(LDFLAGS) \
		-T linker.ld \
		-N -o $@ \
		$(OBJECTS) \
		$(PACKAGES:%=-L$(BUILD_DIR)/software/%) \
		$(LIBS:lib%=-l%)
	chmod -x $@

demo-rom.elf: $(OBJECTS)
	$(CC) $(LDFLAGS) \
		-T linker-rom.ld \
		-N -o $@ \
		$(OBJECTS) \
		$(PACKAGES:%=-L$(BUILD_DIR)/software/%) \
		$(LIBS:lib%=-l%)
	chmod -x $@

main.o: main.c
	$(compile)

crt0.o: $(CPU_DIRECTORY)/crt0.S
	$(assemble)

%.o: %.c
	$(compile)

%.o: %.S
	$(assemble)

clean:
	@$(RM) $(OBJECTS) $(OBJECTS:.o=.d) demo.elf demo.bin .*~ *~

.PHONY: all main.o clean load
