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
	printf("################################\n");
	printf("#####    My own program   ######\n");
	printf("################################\n\n");
	while(1) {
		uint32_t color = rand() & 0xffffff;
		ledring_color_write(color);
		busy_wait(1000);
		printf("Current color = %06lx\n", color);
	}

	return 0;
}
