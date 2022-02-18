#include <stdio.h>
#include <string.h>
#include <error.h>

#include <sys/socket.h>
#include <arpa/inet.h>

#include <json-c/json.h>

#include "modules.h"

struct session_s
{
    char *data;
    char *sys_clk;
    int frequ;

    int cnt_high, cnt_low;
    int val;
    int pulse_cnt;
    int get_bit;
    unsigned int ring[12];
    unsigned int ring_prev[12];
    int led_index;
    int val_high;
    int val_low;
    int val_reset;

    struct sockaddr_in server;
    int sock;

};

int litex_sim_module_get_args(char *args, char *arg, char **val)
{
    int ret = RC_OK;
    json_object *jsobj = NULL;
    json_object *obj = NULL;
    char *value = NULL;
    int r;

    jsobj = json_tokener_parse(args);
    if (NULL == jsobj) {
        fprintf(stderr, "Error parsing json arg: %s \n", args);
        ret = RC_JSERROR;
        goto out;
    }

    if (!json_object_is_type(jsobj, json_type_object)) {
        fprintf(stderr, "Arg must be type object! : %s \n", args);
        ret = RC_JSERROR;
        goto out;
    }

    obj = NULL;
    r = json_object_object_get_ex(jsobj, arg, &obj);
    if (!r) {
        fprintf(stderr, "Could not find object: \"%s\" (%s)\n", arg, args);
        ret = RC_JSERROR;
        goto out;
    }
    value = strdup(json_object_get_string(obj));

out:
    *val = value;
    return ret;
}

static int litex_sim_module_pads_get(struct pad_s *pads, char *name, void **signal)
{
    int ret = RC_OK;
    void *sig = NULL;
    int i;

    if (!pads || !name || !signal) {
        ret = RC_INVARG;
        goto out;
    }

    i = 0;
    while (pads[i].name) {
        if (!strcmp(pads[i].name, name)) {
            sig = (void *)pads[i].signal;
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
    printf("[ledring] loaded\n");
    return RC_OK;
}

static int ledring_new(void **sess, char *args)
{
    int ret = RC_OK;
    struct session_s *s = NULL;

    if (!sess) {
        ret = RC_INVARG;
        goto out;
    }

    s = (struct session_s *)malloc(sizeof(struct session_s));
    if (!s) {
        ret = RC_NOENMEM;
        goto out;
    }

    memset(s, 0, sizeof(struct session_s));

    s->sock = socket(AF_INET, SOCK_DGRAM, 0);
    if (s->sock < 0) {
        printf("Error while creating socket\n");
        return -1;
    }

    s->server.sin_addr.s_addr = inet_addr("127.0.0.1");
    s->server.sin_family = AF_INET;
    s->server.sin_port = htons(8888);

    char *c_frequ = NULL;
    ret = litex_sim_module_get_args(args, "freq", &c_frequ);
    if (RC_OK != ret)
            goto out;

    s->frequ = atoi(c_frequ);
    s->val_high  = (int)(800e-9 * (float)(s->frequ));
    s->val_low   = (int)(400e-9 * (float)(s->frequ));
    s->val_reset = (int)(5e-6 * (float)(s->frequ));

out:
    *sess = (void *)s;
    return ret;
}

static int ledring_add_pads(void *sess, struct pad_list_s *plist)
{
    int ret = RC_OK;
    struct session_s *s = (struct session_s *)sess;
    struct pad_s *pads;

    if (!sess || !plist) {
        ret = RC_INVARG;
        goto out;
    }
    pads = plist->pads;

    if (!strcmp(plist->name, "data_out"))
        litex_sim_module_pads_get(pads, "data_out", (void **)&s->data);

    if (!strcmp(plist->name, "sys_clk"))
        litex_sim_module_pads_get(pads, "sys_clk", (void **)&s->sys_clk);

out:
    return ret;
}

static int ledring_tick(void *sess, uint64_t time_ps)
{
    struct session_s *s = (struct session_s *)sess;
    static clk_edge_state_t edge;
    int bit = 0, reset = 0;

    /* Because it also be a falling edge */
    if (!clk_pos_edge(&edge, *s->sys_clk))
        return RC_OK;

    /* Count how long data stays high */
    if (*s->data) {
        s->cnt_high++;
        s->cnt_low = 0;
        s->get_bit = 1;
    /* Now, data is low, we can extract the bit information */
    } else {
        s->cnt_low++;

        if (s->get_bit) {
            /* We do this only once */
            s->get_bit = 0;
            if (s->cnt_high == s->val_low) {
                bit = 0;
                s->pulse_cnt++;
            } else if (s->cnt_high == s->val_high) {
                bit = 1;
                s->pulse_cnt++;
            } else {
                printf("Wrong count value = %d (%d, %d, %d)\n", s->cnt_high, s->val_low, s->val_high, s->frequ);
            }

            s->val = (s->val << 1) | bit;
        }

        s->cnt_high = 0;
        if (s->cnt_low > s->val_reset)
            reset = 1;
    }

    if (s->pulse_cnt == 24) {
        s->pulse_cnt = 0;
        s->ring[s->led_index] = s->val;
        s->led_index++;
        s->val = 0;
    }

    if (reset) {
        reset = 0;
        s->pulse_cnt = 0;
        s->led_index = 0;

        if (memcmp(s->ring, s->ring_prev, 12 * sizeof(unsigned int))) {
            int ret = sendto(s->sock, s->ring, 12 * sizeof(unsigned int),
                             0, (const struct sockaddr *)&s->server, sizeof(s->server));
            if (ret == -1)
                printf("sendto error\n");

            memcpy(s->ring_prev, s->ring, 12 * sizeof(unsigned int));
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
    ledring_tick};

int litex_sim_ext_module_init(int (*register_module)(struct ext_module_s *))
{
    int ret = RC_OK;
    ret = register_module(&ext_mod);
    return ret;
}
