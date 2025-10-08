#ifndef CIRCULAR_B_H
#define CIRCULAR_B_H

#include "types.h"
#include "circular_a.h"  // This creates a circular dependency!

typedef struct {
    int value_b;
    void* ref_to_a;  // Reference to A
} CircularB;

CircularB* create_b(int val);
void process_b(CircularB* b);

#endif // CIRCULAR_B_H

