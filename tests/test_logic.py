"""
Tests for the Condition module logical operations.
"""

from spaxiom.condition import Condition


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