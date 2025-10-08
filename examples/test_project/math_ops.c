#include "math_ops.h"
#include "utils.h"
#include <stdio.h>

int32_t add(int32_t a, int32_t b) {
    logger_log(LOG_DEBUG, "Addition operation");
    return a + b;
}

int32_t subtract(int32_t a, int32_t b) {
    logger_log(LOG_DEBUG, "Subtraction operation");
    return a - b;
}

int32_t multiply(int32_t a, int32_t b) {
    return a * b;
}

int32_t divide(int32_t a, int32_t b) {
    if (b == 0) {
        logger_log(LOG_ERROR, "Division by zero");
        return 0;
    }
    return a / b;
}

int32_t power(int32_t base, int32_t exp) {
    if (exp == 0) return 1;
    
    int32_t result = 1;
    for (int i = 0; i < exp; i++) {
        result = multiply(result, base);
    }
    return result;
}

int32_t factorial(int32_t n) {
    if (n <= 1) return 1;
    return multiply(n, factorial(subtract(n, 1)));
}

int32_t gcd(int32_t a, int32_t b) {
    if (b == 0) return a;
    return gcd(b, a % b);
}

