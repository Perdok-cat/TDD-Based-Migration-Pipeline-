#include <stdio.h>
#include "math_utils.h"
#include "calculator.h"

/**
 * Hàm main để test các functions từ các modules khác nhau
 */
int main() {
    printf("=== Test Math Utils ===\n");
    
    // Test add function
    int result1 = add(10, 20);
    printf("add(10, 20) = %d\n", result1);
    
    // Test multiply function
    int result2 = multiply(7, 8);
    printf("multiply(7, 8) = %d\n", result2);
    
    // Test power function
    int result3 = power(2, 8);
    printf("power(2, 8) = %d\n", result3);
    
    printf("\n=== Test Calculator ===\n");
    
    // Test rectangle_area (sử dụng multiply từ math_utils)
    int result4 = rectangle_area(5, 10);
    printf("rectangle_area(5, 10) = %d\n", result4);
    
    // Test rectangle_perimeter (sử dụng multiply và add từ math_utils)
    int result5 = rectangle_perimeter(5, 10);
    printf("rectangle_perimeter(5, 10) = %d\n", result5);
    
    // Test sum_range (sử dụng add từ math_utils)
    int result6 = sum_range(10);
    printf("sum_range(10) = %d\n", result6);
    
    printf("\n=== Test Complete ===\n");
    
    return 0;
}

