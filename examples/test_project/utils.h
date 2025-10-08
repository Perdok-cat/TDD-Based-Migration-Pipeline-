#ifndef UTILS_H
#define UTILS_H

#include "types.h"
#include "logger.h"

// String utilities
int string_length(const char* str);
char* string_copy(const char* src);
int string_compare(const char* s1, const char* s2);

// Array utilities
int array_max(int* arr, int size);
int array_min(int* arr, int size);
void array_print(int* arr, int size);

#endif // UTILS_H

