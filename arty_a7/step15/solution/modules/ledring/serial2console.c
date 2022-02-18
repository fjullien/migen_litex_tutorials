#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "error.h"
#include <unistd.h>
#include <event2/listener.h>
#include <event2/util.h>
#include <event2/event.h>
#include <termios.h>

#include "modules.h"

struct session_s {
  char *data;
};

struct event_base *base;
static int litex_sim_module_pads_get(struct pad_s *pads, char *name, void **signal)
{
    int ret = RC_OK;
    void *sig = NULL;
    int i;

    if (!pads || !name || !signal) {
        ret=RC_INVARG;
        goto out;
    }

    i = 0;
    while (pads[i].name) {
        if (!strcmp(pads[i].name, name)) {
            sig = (void*)pads[i].signal;
            break;
        }
        i++;
    }

out:
    *signal = sig;
    return ret;
}

static int ledring_start(void *b)
{
    base = (struct event_base *)b;
    printf("[ledring] loaded (%p)\n", base);
    return RC_OK;
}

static int ledring_new(void **sess, char *args)
{
    int ret = RC_OK;
    struct timeval tv = {1, 0};
    struct session_s *s = NULL;

    if (!sess) {
        ret = RC_INVARG;
        goto out;
    }

    s = (struct session_s*) malloc(sizeof(struct session_s));
    if (!s) {
        ret=RC_NOENMEM;
        goto out;
    }

    memset(s, 0, sizeof(struct session_s));

out:
    *sess = (void*) s;
    return ret;
}

static int ledring_add_pads(void *sess, struct pad_list_s *plist)
{
    int ret = RC_OK;
    struct session_s *s = (struct session_s*)sess;
    struct pad_s *pads;

    if(!sess || !plist) {
        ret = RC_INVARG;
        goto out;
    }

    pads = plist->pads;
    ret = litex_sim_module_pads_get(pads, plist->name, (void**)&s->data);
    if (ret != RC_OK)
        goto out;

    s->name = plist->name;
out:
    return ret;
}

static int ledring_tick(void *sess, uint64_t time_ps)
{
    static clk_edge_state_t edge;
    struct session_s *s = (struct session_s*)sess;
    static char data_old;

    if (!clk_pos_edge(&edge, *s->sys_clk))
        return RC_OK;

    if (*s->data) {
        if (*s->data != data_old) {
            printf("data changed\n");
            data_old = *s->data;
        }
    }

  return RC_OK;
}

static struct ext_module_s ext_mod = {
  "ledring",
  ledring_start,
  ledring_new,
  ledring_add_pads,
  NULL,
  ledring_tick
};

int litex_sim_ext_module_init(int (*register_module) (struct ext_module_s *))
{
  int ret = RC_OK;
  ret = register_module(&ext_mod);
  return ret;
}
