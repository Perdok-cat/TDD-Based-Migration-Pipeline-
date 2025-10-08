#ifndef LOGGER_H
#define LOGGER_H

#include "config.h"

typedef enum {
    LOG_DEBUG,
    LOG_INFO,
    LOG_WARNING,
    LOG_ERROR
} LogLevel;

void logger_init(Config* cfg);
void logger_log(LogLevel level, const char* message);
void logger_shutdown(void);

#endif // LOGGER_H

