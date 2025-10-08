#include "utils.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int string_length(const char* str) {
    logger_log(LOG_DEBUG, "Calculating string length");
    return strlen(str);
}

char* string_copy(const char* src) {
    if (!src) return NULL;
    
    char* dest = (char*)malloc(strlen(src) + 1);
    if (dest) {
        strcpy(dest, src);
    }
    return dest;
}

int string_compare(const char* s1, const char* s2) {
    return strcmp(s1, s2);
}

int array_max(int* arr, int size) {
    if (!arr || size <= 0) return 0;
    
    int max = arr[0];
    for (int i = 1; i < size; i++) {
        if (arr[i] > max) {
            max = arr[i];
        }
    }
    logger_log(LOG_DEBUG, "Found array maximum");
    return max;
}

int array_min(int* arr, int size) {
    if (!arr || size <= 0) return 0;
    
    int min = arr[0];
    for (int i = 1; i < size; i++) {
        if (arr[i] < min) {
            min = arr[i];
        }
    }
    return min;
}

void array_print(int* arr, int size) {
    printf("[");
    for (int i = 0; i < size; i++) {
        printf("%d", arr[i]);
        if (i < size - 1) printf(", ");
    }
    printf("]\n");
}

