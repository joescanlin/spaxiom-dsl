"""
Tests for the Condition module logical operations.
"""

import time
from spaxiom.logic import Condition, transitioned_to_true


def test_condition_basic():
    """Test that basic Condition objects work correctly."""
    always_true = Condition(lambda: True)
    always_false = Condition(lambda: False)

    assert always_true() is True
    assert always_false() is False

    # Test with dynamic values
    counter = 0

    def increment_counter():
        nonlocal counter
        counter += 1
        return counter > 3

    counting_condition = Condition(increment_counter)

    # First few calls should be False
    assert counting_condition() is False
    assert counting_condition() is False
    assert counting_condition() is False

    # Then should become True
    assert counting_condition() is True
    assert counting_condition() is True


def test_condition_not():
    """Test the NOT (~) operator on Conditions."""
    always_true = Condition(lambda: True)
    always_false = Condition(lambda: False)

    not_true = ~always_true
    not_false = ~always_false

    assert not_true() is False
    assert not_false() is True

    # Double negation
    assert (~not_true)() is True
    assert (~not_false)() is False


def test_condition_and():
    """Test the AND (&) operator on Conditions."""
    always_true = Condition(lambda: True)
    always_false = Condition(lambda: False)

    # True AND True = True
    assert (always_true & always_true)() is True

    # True AND False = False
    assert (always_true & always_false)() is False

    # False AND True = False
    assert (always_false & always_true)() is False

    # False AND False = False
    assert (always_false & always_false)() is False

    # Short-circuit evaluation (no need to actually call second condition)
    call_count = 0

    def counter():
        nonlocal call_count
        call_count += 1
        return True

    counting_condition = Condition(counter)

    # This should not call the counter function because always_false is evaluated first
    (always_false & counting_condition)()
    assert call_count == 0


def test_condition_or():
    """Test the OR (|) operator on Conditions."""
    always_true = Condition(lambda: True)
    always_false = Condition(lambda: False)

    # True OR True = True
    assert (always_true | always_true)() is True

    # True OR False = True
    assert (always_true | always_false)() is True

    # False OR True = True
    assert (always_false | always_true)() is True

    # False OR False = False
    assert (always_false | always_false)() is False

    # Short-circuit evaluation (no need to actually call second condition)
    call_count = 0

    def counter():
        nonlocal call_count
        call_count += 1
        return False

    counting_condition = Condition(counter)

    # This should not call the counter function because always_true is evaluated first
    (always_true | counting_condition)()
    assert call_count == 0


def test_complex_condition():
    """Test complex combinations of logical operators."""
    t = Condition(lambda: True)
    f = Condition(lambda: False)

    # (True OR False) AND (NOT False) = True AND True = True
    complex_condition = (t | f) & (~f)
    assert complex_condition() is True

    # NOT (True AND False) OR False = NOT False OR False = True OR False = True
    complex_condition = ~(t & f) | f
    assert complex_condition() is True

    # (NOT True) OR (False AND True) = False OR False = False
    complex_condition = (~t) | (f & t)
    assert complex_condition() is False


def test_timestamp_tracking():
    """Test that Condition tracks last_value and last_changed timestamps."""
    # Create a condition with a changing value
    value_state = False

    def toggle_value():
        nonlocal value_state
        value_state = not value_state
        return value_state

    toggle_condition = Condition(toggle_value)

    # Initial state
    initial_time = time.time()
    result = toggle_condition.evaluate(initial_time)
    
    assert result is True  # First call toggles to True
    assert toggle_condition.last_value is True
    assert toggle_condition.last_changed == initial_time
    
    # Second evaluation at new time
    second_time = initial_time + 1.0
    result = toggle_condition.evaluate(second_time)
    
    assert result is False  # Toggles back to False
    assert toggle_condition.last_value is False
    assert toggle_condition.last_changed == second_time
    
    # Third evaluation with no change
    third_time = second_time + 1.0
    result = toggle_condition.evaluate(third_time)
    
    assert result is True  # Toggles to True again
    assert toggle_condition.last_value is True
    assert toggle_condition.last_changed == third_time


def test_evaluate_method():
    """Test that evaluate method updates timestamps correctly."""
    # Create a condition that changes value on each call
    toggle_value = [True, False, True]
    call_index = 0
    
    def toggle():
        nonlocal call_index
        result = toggle_value[call_index]
        call_index = (call_index + 1) % len(toggle_value)
        return result
    
    condition = Condition(toggle)
    
    # First evaluation - should be True
    t1 = 1000.0
    result1 = condition.evaluate(t1)
    assert result1 is True
    assert condition.last_value is True
    assert condition.last_changed == t1
    
    # Second evaluation - should change to False
    t2 = 2000.0
    result2 = condition.evaluate(t2)
    assert result2 is False
    assert condition.last_value is False
    assert condition.last_changed == t2
    
    # Third evaluation - should change to True
    t3 = 3000.0
    result3 = condition.evaluate(t3)
    assert result3 is True
    assert condition.last_value is True
    assert condition.last_changed == t3


def test_transitioned_to_true():
    """Test the transitioned_to_true method and helper function."""
    # Create a condition with controllable state
    state = False

    def get_state():
        return state

    test_condition = Condition(get_state)
    
    # Initial state is False
    t1 = 1000.0
    assert test_condition.evaluate(t1) is False
    assert test_condition.transitioned_to_true(t1) is False
    assert transitioned_to_true(test_condition, t1) is False
    
    # Get the previous state values for debugging
    prev_value = test_condition.last_value
    prev_changed = test_condition.last_changed
    
    # Change state to True
    state = True
    t2 = 2000.0
    
    # Evaluate and check value
    result = test_condition.evaluate(t2)
    assert result is True
    
    # Print debug info
    print(f"Debug: prev_value={prev_value}, current_value={test_condition.last_value}")
    print(f"Debug: prev_changed={prev_changed}, current_changed={test_condition.last_changed}")
    
    # Directly check transitioned_to_true
    trans_result = test_condition.transitioned_to_true(t2)
    print(f"Debug: transitioned_to_true result: {trans_result}")
    
    # It should have transitioned at this timestamp
    assert trans_result is True
    assert transitioned_to_true(test_condition, t2) is True
    
    # Same state, different timestamp
    t3 = 3000.0
    assert test_condition.evaluate(t3) is True
    # It shouldn't register as a transition anymore
    assert test_condition.transitioned_to_true(t3) is False
    assert transitioned_to_true(test_condition, t3) is False
