#include "math_utils.h"

/**
 * Tính tổng hai số nguyên
 */
int add(int a, int b) {
    return a + b;
}

/**
 * Tính tích hai số nguyên
 */
int multiply(int a, int b) {
    return a * b;
}

/**
 * Tính lũy thừa (base^exponent)
 */
int power(int base, int exponent) {
    if (exponent == 0) {
        return 1;
    }
    if (exponent == 1) {
        return base;
    }
    return base * power(base, exponent - 1);
}

