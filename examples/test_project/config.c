#include "config.h"
#include <stdlib.h>
#include <string.h>

Config* config_init(void) {
    Config* cfg = (Config*)malloc(sizeof(Config));
    if (cfg) {
        cfg->name = APP_NAME;
        cfg->version = 1;
        cfg->debug_enabled = DEBUG_MODE;
    }
    return cfg;
}

void config_destroy(Config* cfg) {
    if (cfg) {
        free(cfg);
    }
}

