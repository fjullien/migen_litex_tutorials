#include <stdio.h>
#include <string.h>
#include <error.h>

#include <sys/socket.h>
#include <arpa/inet.h>

#include <json-c/json.h>

#include "modules.h"

/*----------------------------------------
 * This is the session private data
 *-----------------------------------------
 */
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

/*-----------------------------------------------------------
 * This is how we get arguments from sim_config.add_module.
 * It really should be something generic.
 * Don't pay too much attention to that.
 *------------------------------------------------------------
 */
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

/*----------------------------------------
 * This is how we get pads from interfaces
 * It really should be something generic.
 * Don't pay too much attention to that.
 *-----------------------------------------
 */
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

/*----------------------------------------
 * Called once
 *-----------------------------------------
 */
static int ledring_start(void *b)
{
    printf("[ledring] loaded\n");
    return RC_OK;
}

/*----------------------------------------
 * Create a session
 *-----------------------------------------
 */
static int ledring_new(void **sess, char *args)
{
    int ret = RC_OK;
    struct session_s *s = NULL;

    /*--------------------------------------
     * Create a session per module instance
     *--------------------------------------
     */
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

    /*--------------------------------------
     * Create a socket
     *--------------------------------------
     */
    s->sock = socket(AF_INET, SOCK_DGRAM, 0);
    if (s->sock < 0) {
        printf("Error while creating socket\n");
        return -1;
    }

    s->server.sin_addr.s_addr = inet_addr("127.0.0.1");
    s->server.sin_family = AF_INET;
    s->server.sin_port = htons(8888);

    /*--------------------------------------------
     * Get arguments from sim_config.add_module
     *--------------------------------------------
     */
    char *c_frequ = NULL;
    ret = litex_sim_module_get_args(args, "freq", &c_frequ);
    if (RC_OK != ret)
            goto out;

    /*--------------------------------------------
     * Compute delays
     *--------------------------------------------
     */
    s->frequ = atoi(c_frequ);
    s->val_high  = (int)(800e-9 * (float)(s->frequ));
    s->val_low   = (int)(400e-9 * (float)(s->frequ));
    s->val_reset = (int)(5e-6 * (float)(s->frequ));

out:
    *sess = (void *)s;
    return ret;
}

/*----------------------------------------
 * Get pads from interfaces
 *-----------------------------------------
 */
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

    /*--------------------------------------------
     * Get pads from interface ports
     *--------------------------------------------
     *
     * "data_out" port has only a "data_out" signal
     * However, in the case of the "eth" port, we would have passed, for example,
     * "source_ready" to get this signal in the "eth" port:
     *
     *      if (!strcmp(plist->name, "eth")) {
     *          litex_sim_module_pads_get(pads, "source_valid", (void **)&s->source_valid);
     *          litex_sim_module_pads_get(pads, "source_ready", (void **)&s->source_ready);
     *          ....
     *
     *     ("eth", 0,
     *          Subsignal("source_valid", Pins(1)),
     *          Subsignal("source_ready", Pins(1)),
     *          Subsignal("source_data",  Pins(8)),
     *          Subsignal("sink_valid",   Pins(1)),
     *          Subsignal("sink_ready",   Pins(1)),
     *          Subsignal("sink_data",    Pins(8)),
     *      ),
     */
    if (!strcmp(plist->name, "data_out"))
        litex_sim_module_pads_get(pads, "data_out", (void **)&s->data);

    /* There is always a "sys_clk" port */
    if (!strcmp(plist->name, "sys_clk"))
        litex_sim_module_pads_get(pads, "sys_clk", (void **)&s->sys_clk);

out:
    return ret;
}

/*----------------------------------------------
 * This is called every time the clock changes
 *----------------------------------------------
 */
static int ledring_tick(void *sess, uint64_t time_ps)
{
    struct session_s *s = (struct session_s *)sess;
    static clk_edge_state_t edge;
    int bit = 0, reset = 0;

    /* Because it could also be a falling edge */
    if (!clk_pos_edge(&edge, *s->sys_clk))
        return RC_OK;

    /* If data is high, count how long it stays high */
    if (*s->data) {
        s->cnt_high++;
        s->cnt_low = 0;
        s->get_bit = 1;
    /* Now, data is low, we can extract the bit information */
    } else {
        s->cnt_low++;

        /* For each bit, we need to decide if it's a '1' or '0' */
        if (s->get_bit) {
            /* We do this only once */
            s->get_bit = 0;

            /* It's a zero */
            if (s->cnt_high == s->val_low) {
                bit = 0;
                s->pulse_cnt++;
            /* It's a one */
            } else if (s->cnt_high == s->val_high) {
                bit = 1;
                s->pulse_cnt++;
            /* We don't know */
            } else {
                printf("Wrong count value = %d (%d, %d, %d)\n", s->cnt_high, s->val_low, s->val_high, s->frequ);
            }

            /* Shift the new bit to the value of this LED */
            s->val = (s->val << 1) | bit;
        }

        /* This is the condition for sending the values to the LED ring */
        s->cnt_high = 0;
        if (s->cnt_low > s->val_reset)
            reset = 1;
    }

    /* If we've got 24 bits, move to the next LED */
    if (s->pulse_cnt == 24) {
        s->pulse_cnt = 0;
        s->ring[s->led_index] = s->val;
        s->led_index++;
        s->val = 0;
    }

    /* Send the result to the graphical simulation */
    if (reset) {
        reset = 0;
        s->pulse_cnt = 0;
        s->led_index = 0;

        /* Only if values have changed...*/
        if (memcmp(s->ring, s->ring_prev, 12 * sizeof(unsigned int))) {
            /* Send it */
            int ret = sendto(s->sock, s->ring, 12 * sizeof(unsigned int),
                             0, (const struct sockaddr *)&s->server, sizeof(s->server));
            if (ret == -1)
                printf("sendto error\n");
            /* Save current values */
            memcpy(s->ring_prev, s->ring, 12 * sizeof(unsigned int));
        }
    }

    return RC_OK;
}

static struct ext_module_s ext_mod = {
    "ledring",          /* Modules's name */
    ledring_start,      /* Called once during start */
    ledring_new,        /* Called once for each module instance */
    ledring_add_pads,   /* Called for every interface */
    NULL,               /* End of simulation callback */
    ledring_tick        /* Called every clock cycle */
};

/*----------------------------------------
 * Register the module
 *-----------------------------------------
 */
int litex_sim_ext_module_init(int (*register_module)(struct ext_module_s *))
{
    int ret = RC_OK;
    ret = register_module(&ext_mod);
    return ret;
}
