#include "circular_b.h"
#include <stdlib.h>

CircularB* create_b(int val) {
    CircularB* b = (CircularB*)malloc(sizeof(CircularB));
    if (b) {
        b->value_b = val;
        b->ref_to_a = NULL;
    }
    return b;
}

void process_b(CircularB* b) {
    if (b) {
        b->value_b += 10;
    }
}

