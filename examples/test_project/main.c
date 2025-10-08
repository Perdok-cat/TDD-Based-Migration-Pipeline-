#include <stdio.h>
#include <stdlib.h>
#include "config.h"
#include "logger.h"
#include "utils.h"
#include "math_ops.h"

int main(int argc, char* argv[]) {
    // Initialize configuration
    Config* cfg = config_init();
    logger_init(cfg);
    
    logger_log(LOG_INFO, "Application started");
    
    // Test math operations
    int32_t a = 10, b = 5;
    printf("Add: %d + %d = %d\n", a, b, add(a, b));
    printf("Subtract: %d - %d = %d\n", a, b, subtract(a, b));
    printf("Multiply: %d * %d = %d\n", a, b, multiply(a, b));
    printf("Divide: %d / %d = %d\n", a, b, divide(a, b));
    printf("Power: %d ^ %d = %d\n", a, 3, power(a, 3));
    printf("Factorial: %d! = %d\n", 5, factorial(5));
    printf("GCD: gcd(%d, %d) = %d\n", 48, 18, gcd(48, 18));
    
    // Test string utilities
    const char* test_str = "Hello, World!";
    printf("String length: %d\n", string_length(test_str));
    
    char* copied = string_copy(test_str);
    printf("Copied string: %s\n", copied);
    free(copied);
    
    // Test array utilities
    int arr[] = {5, 2, 8, 1, 9, 3};
    int size = 6;
    printf("Array: ");
    array_print(arr, size);
    printf("Max: %d\n", array_max(arr, size));
    printf("Min: %d\n", array_min(arr, size));
    
    logger_log(LOG_INFO, "Application completed");
    logger_shutdown();
    config_destroy(cfg);
    
    return SUCCESS;
}

