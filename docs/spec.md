# Spaxiom DSL Formal Specification

## Overview
Spaxiom is an embedded domain-specific language (DSL) for spatial sensor fusion and temporal reasoning, implemented in Python. This document provides a formal grammar specification for the DSL, focusing on the key components and their composition rules.

## BNF Grammar Specification

The following Backus-Naur Form (BNF) grammar defines the core constructs of the Spaxiom DSL:

```bnf
<spaxiom-program> ::= <import-statements> <declaration-list> [<main-function>]

<import-statements> ::= "from spaxiom import" <import-list>
<import-list> ::= <import-item> ["," <import-item>]*
<import-item> ::= <identifier>

<declaration-list> ::= <declaration>+
<declaration> ::= <sensor-decl> | <zone-decl> | <condition-decl> | <event-handler-decl> | <entity-set-decl>

<sensor-decl> ::= <identifier> "=" <sensor-type> "(" <sensor-args> ")"
<sensor-type> ::= "Sensor" | "RandomSensor" | "TogglingSensor" | "GPIOSensor" | <custom-sensor>
<sensor-args> ::= "name=" <string> "," "sensor_type=" <string> "," "location=" <coordinate> ["," <sensor-option>]*
<sensor-option> ::= "privacy=" <privacy-value> | "sample_period_s=" <number> | "metadata=" <dict>
<privacy-value> ::= '"public"' | '"private"'
<coordinate> ::= "(" <number> "," <number> "," <number> ")"

<zone-decl> ::= <identifier> "=" "Zone" "(" <number> "," <number> "," <number> "," <number> ")"

<condition-decl> ::= <identifier> "=" <condition-expr>
<condition-expr> ::= <simple-condition> | <combined-condition> | <temporal-condition>
<simple-condition> ::= "Condition" "(" <lambda-function> ")"
<combined-condition> ::= <condition-expr> <operator> <condition-expr> | "~" <condition-expr>
<operator> ::= "&" | "|"
<temporal-condition> ::= "within" "(" <number> "," <condition-expr> ")" | "sequence" "(" <condition-list> "," <number> ")"
<condition-list> ::= "[" <condition-expr> ["," <condition-expr>]* "]"
<lambda-function> ::= "lambda" [":" <python-expression>]

<entity-set-decl> ::= <identifier> "=" "EntitySet" "(" <string> ")"

<event-handler-decl> ::= "@on" "(" <condition-expr> ")" <newline> "def" <identifier> "(" ")" ":" <newline> <handler-body>
<handler-body> ::= <python-statement>+

<main-function> ::= "def main():" <newline> <python-statement>+

<python-statement> ::= <valid-python-code>
<python-expression> ::= <valid-python-expression>
<dict> ::= "{" [<key-value-pair> ["," <key-value-pair>]*] "}"
<key-value-pair> ::= <string> ":" <value>
<value> ::= <string> | <number> | <dict> | <list>
<list> ::= "[" [<value> ["," <value>]*] "]"
<string> ::= '"' <characters> '"' | "'" <characters> "'"
<number> ::= <integer> | <float>
<integer> ::= <digit>+
<float> ::= <digit>+ "." <digit>*
<digit> ::= "0" | "1" | "2" | "3" | "4" | "5" | "6" | "7" | "8" | "9"
<identifier> ::= <letter> [<letter> | <digit> | "_"]*
<letter> ::= "A" | "B" | ... | "Z" | "a" | "b" | ... | "z"
<newline> ::= "\n"
<characters> ::= <character>*
<character> ::= <any-valid-character>
<custom-sensor> ::= <identifier>
```

## Operator Precedence

The Spaxiom DSL adopts standard logical operator precedence for conditions, which are implemented using Python's operator overloading mechanism. The precedence order from highest to lowest is:

1. `~` (NOT) - Unary operator with highest precedence
2. `&` (AND) - Binary operator with medium precedence
3. `|` (OR) - Binary operator with lowest precedence

This means that expressions are evaluated in the following order:

```
~A & B | C
```

is equivalent to:

```
((~A) & B) | C
```

### Precedence Rules

The precedence of operators in the Spaxiom DSL follows these rules:

1. **Negation (`~`) has the highest precedence**:
   - When you negate a condition using `~`, this is always applied first.
   - Example: `~condition1 & condition2` is interpreted as `(~condition1) & condition2`.

2. **Conjunction (`&`) has higher precedence than disjunction**:
   - The AND operator is applied before the OR operator.
   - Example: `condition1 & condition2 | condition3` is interpreted as `(condition1 & condition2) | condition3`.

3. **Disjunction (`|`) has the lowest precedence**:
   - The OR operator is applied last in a complex expression.
   - Example: `condition1 | condition2 & condition3` is interpreted as `condition1 | (condition2 & condition3)`.

4. **Parentheses can be used to override default precedence**:
   - For clarity or to change the order of operations, use parentheses.
   - Example: `condition1 | (condition2 & ~condition3)`.

### Implementation Details

These precedence rules are implemented in the `Condition` class through the following methods:

```python
def __and__(self, other: "Condition") -> "Condition":
    """Implement the & operator (logical AND)."""
    def combined_condition(**kwargs):
        # Short-circuit evaluation
        if not self(**kwargs):
            return False
        return other(**kwargs)
    return Condition(combined_condition)

def __or__(self, other: "Condition") -> "Condition":
    """Implement the | operator (logical OR)."""
    def combined_condition(**kwargs):
        # Short-circuit evaluation
        if self(**kwargs):
            return True
        return other(**kwargs)
    return Condition(combined_condition)

def __invert__(self) -> "Condition":
    """Implement the ~ operator (logical NOT)."""
    def inverted_condition(**kwargs):
        return not self(**kwargs)
    return Condition(inverted_condition)
```

## Examples

Here are some examples of how to use logical operators in Spaxiom with their evaluation order:

```python
# Individual conditions
in_zone = Condition(lambda: zone.contains(sensor.location))
is_hot = Condition(lambda: temperature.read() > 30.0)
is_moving = Condition(lambda: motion.read() > 0.5)

# Combined conditions with operator precedence

# 1. Simple AND: Both conditions must be true
in_hot_zone = in_zone & is_hot  # Evaluates: in_zone AND is_hot

# 2. Simple OR: Either condition can be true 
alert_condition = in_zone | is_hot  # Evaluates: in_zone OR is_hot

# 3. NOT applied to a single condition
not_in_zone = ~in_zone  # Evaluates: NOT in_zone

# 4. Complex expression with all operators
complex_condition = ~is_hot & in_zone | is_moving
# Evaluates as: ((NOT is_hot) AND in_zone) OR is_moving

# 5. Using parentheses to override precedence
override_precedence = ~(is_hot & in_zone) | is_moving
# Evaluates as: (NOT (is_hot AND in_zone)) OR is_moving

# 6. Another example with parentheses
another_override = is_hot & (in_zone | is_moving)
# Evaluates as: is_hot AND (in_zone OR is_moving)
```

## Temporal Operators

The temporal operators like `within` and `sequence` have their own precedence rules, and they typically operate on condition expressions:

```python
# Condition must be true for at least 5 seconds
sustained_condition = within(5.0, is_hot & in_zone)

# Sequence of conditions must happen in order within 10 seconds
entry_sequence = sequence([door_open, person_detected, door_closed], 10.0)
```

These temporal operators wrap condition expressions and create new condition objects that can be further combined with the logical operators described above. 