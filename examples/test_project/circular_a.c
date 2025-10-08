#include "circular_a.h"
#include <stdlib.h>

CircularA* create_a(int val) {
    CircularA* a = (CircularA*)malloc(sizeof(CircularA));
    if (a) {
        a->value_a = val;
        a->ref_to_b = NULL;
    }
    return a;
}

void process_a(CircularA* a) {
    if (a) {
        a->value_a *= 2;
    }
}

