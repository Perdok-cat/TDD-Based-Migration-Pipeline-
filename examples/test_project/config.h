#ifndef CONFIG_H
#define CONFIG_H

#include "types.h"

#define APP_NAME "TestApp"
#define APP_VERSION "1.0.0"
#define DEBUG_MODE 1

typedef struct {
    string_t name;
    int32_t version;
    int debug_enabled;
} Config;

Config* config_init(void);
void config_destroy(Config* cfg);

#endif // CONFIG_H

