#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <irq.h>
#include <libbase/uart.h>
#include <libbase/console.h>
#include <generated/csr.h>

int main(void)
{
#ifdef CONFIG_CPU_HAS_INTERRUPT
	irq_setmask(0);
	irq_setie(1);
#endif
	uart_init();
	while(1) {
		/* Set led colors using a helper available in generated files */
		
		/* litex/soc/software/libbase/system.c */
		busy_wait(1000);

		/* use a printf to be sure it works :) */
	}

	return 0;
}
