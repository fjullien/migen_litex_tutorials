/* Set elf format*/
INCLUDE generated/output_format.ld
ENTRY(_start)

/* Include definition of memory regions */
/*
MEMORY {
	rom : ORIGIN = 0x00000000, LENGTH = 0x00020000
	sram : ORIGIN = 0x10000000, LENGTH = 0x00002000
	main_ram : ORIGIN = 0x40000000, LENGTH = 0x00001000
	csr : ORIGIN = 0xf0000000, LENGTH = 0x00010000
}
*/

INCLUDE generated/regions.ld

SECTIONS
{
	.text :
	{
		_ftext = .;
		/* Make sure crt0 files come first, and they, and the isr */
		/* don't get disposed of by greedy optimisation */
		*crt0*(.text)
		KEEP(*crt0*(.text))
		KEEP(*(.text.isr))

		*(.text .stub .text.* .gnu.linkonce.t.*)
		_etext = .;
	} > rom
	/* .text will be located in main_ram when the program is loaded
	 * by the BIOS from the host.
	 * Change this to > rom if the program is placed in the integrated rom.
	 */

	.rodata :
	{
		. = ALIGN(8);
		_frodata = .;
		*(.rodata .rodata.* .gnu.linkonce.r.*)
		*(.rodata1)
		. = ALIGN(8);
		_erodata = .;
	} > rom
	/* .rodata will be located in main_ram when the program is loaded
	 * by the BIOS from the host.
	 * Change this to > rom if the program is placed in the integrated rom.
	 */

	.data :
	{
		. = ALIGN(8);
		_fdata = .;
		*(.data .data.* .gnu.linkonce.d.*)
		*(.data1)
		_gp = ALIGN(16);
		*(.sdata .sdata.* .gnu.linkonce.s.*)
		. = ALIGN(8);
		_edata = .;
	} > sram AT > rom
	/* .data will be located in sram but copied from main_ram.
	 * Change this to AT > rom if the program is placed in the integrated rom.
	 */

	.bss :
	{
		. = ALIGN(8);
		_fbss = .;
		*(.dynsbss)
		*(.sbss .sbss.* .gnu.linkonce.sb.*)
		*(.scommon)
		*(.dynbss)
		*(.bss .bss.* .gnu.linkonce.b.*)
		*(COMMON)
		. = ALIGN(8);
		_ebss = .;
		_end = .;
	} > sram
}

/* Some symbols are needed by some crt0 files */
PROVIDE(_fstack = ORIGIN(sram) + LENGTH(sram));
PROVIDE(_fdata_rom = LOADADDR(.data));
PROVIDE(_edata_rom = LOADADDR(.data) + SIZEOF(.data));
