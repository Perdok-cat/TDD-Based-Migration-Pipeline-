#include "calculator.h"
#include "math_utils.h"

/**
 * Tính diện tích hình chữ nhật
 */
int rectangle_area(int width, int height) {
    return multiply(width, height);
}

/**
 * Tính chu vi hình chữ nhật
 */
int rectangle_perimeter(int width, int height) {
    int double_width = multiply(width, 2);
    int double_height = multiply(height, 2);
    return add(double_width, double_height);
}

/**
 * Tính tổng các số từ 1 đến n
 */
int sum_range(int n) {
    if (n <= 0) {
        return 0;
    }
    if (n == 1) {
        return 1;
    }
    return add(n, sum_range(n - 1));
}

