#ifndef CIRCULAR_A_H
#define CIRCULAR_A_H

#include "types.h"
#include "circular_b.h"  // This creates a circular dependency!

typedef struct {
    int value_a;
    void* ref_to_b;  // Reference to B
} CircularA;

CircularA* create_a(int val);
void process_a(CircularA* a);

#endif // CIRCULAR_A_H

