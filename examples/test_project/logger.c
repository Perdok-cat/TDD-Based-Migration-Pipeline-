#include "logger.h"
#include <stdio.h>
#include <time.h>

static Config* global_config = NULL;

void logger_init(Config* cfg) {
    global_config = cfg;
    logger_log(LOG_INFO, "Logger initialized");
}

void logger_log(LogLevel level, const char* message) {
    const char* level_str[] = {"DEBUG", "INFO", "WARNING", "ERROR"};
    
    if (global_config && global_config->debug_enabled) {
        printf("[%s] %s\n", level_str[level], message);
    }
}

void logger_shutdown(void) {
    logger_log(LOG_INFO, "Logger shutting down");
    global_config = NULL;
}

