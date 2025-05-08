#!/usr/bin/env python3
"""
Simple timestamp demo for Spaxiom DSL.

This demonstrates the basic timestamp functionality without using the runtime.
"""

import time
from spaxiom.logic import Condition, transitioned_to_true

# Create a condition with a changing value
value_state = False

def get_value():
    global value_state
    return value_state

# Create the condition
condition = Condition(get_value)

# Test the condition in a loop
for i in range(10):
    print(f"\nIteration {i+1}:")
    
    # Every other iteration, toggle the value
    if i % 2 == 1:
        value_state = not value_state
        print(f"  * Toggling value to: {value_state}")
    
    # Evaluate the condition
    now = time.time()
    result = condition.evaluate(now)
    print(f"  Value: {result}")
    print(f"  Last changed: {condition.last_changed:.2f}")
    print(f"  Time since change: {now - condition.last_changed:.2f} seconds")
    
    # Check if it transitioned to true
    transition = transitioned_to_true(condition, now)
    print(f"  Transitioned to true: {transition}")
    
    # Wait a bit
    time.sleep(0.5) 