<div align="center">
  <img src="../images/intent-logo.svg" alt="INTENT Logo" width="200">
</div>

# Intelligent Network for Temporal & Embodied Neuro-symbolic Tasks (INTENT)

**INTENT** is a high-level pattern library built on top of Spaxiom that turns floor grids, switches, and air-quality probes into meaningful, agentic signals like *crowding*, *queue flow*, and *needs service* – in just a few lines of code.

Spaxiom gives you the **core DSL**:

- sensors, zones, and units
- spatial + temporal conditions
- event callbacks and runtime

INTENT adds **agent-ready patterns**:

- occupancy fields and flow estimates
- queue & wait-time analytics
- daily-living and facility-care routines
- pre-baked "intent outputs" for LLMs and other AI planners

Think of it as:

> Spaxiom = *axioms of the physical world*
> INTENT   = *named behaviours you can plug into agents*

---

## Install

```bash
pip install "spaxiom-dsl[intent]"
```

The intent extra pulls in any additional dependencies needed for the higher-level patterns
(if and when they are added). For now, it simply enables the spaxiom.intent module.

## Quick Example: From Floor Grid to Agent Intent

Below is a full, runnable example that:
1. Uses an existing floor grid sensor (FloorGridSensor)
2. Wraps it in an INTENT OccupancyField
3. Detects sustained crowding in a lobby
4. Calls an LLM to decide what to do (update signage, open a second desk, etc.)

```python
# examples/intent_lobby.py
import asyncio, json, os
import openai

from spaxiom.config   import load_yaml
from spaxiom.runtime  import start_runtime
from spaxiom.temporal import within
from spaxiom.logic    import on
from spaxiom.intent   import OccupancyField  # <- INTENT layer

# 1) Load sensors from YAML (includes FloorGridSensor "lobby_floor")
sensors = load_yaml("examples/lobby.yaml")
floor   = sensors["lobby_floor"]

# 2) Wrap into an OccupancyField pattern
field = OccupancyField(floor, name="lobby")

# 3) Define an intent: sustained crowding (>= 10% tiles active for 3 minutes)
crowded = within(180.0, field.percent_above(10.0))

# 4) When intent becomes true, we call our agent (LLM)
@on(crowded)
async def lobby_agent():
    facts = {
        "zone": field.name,
        "occupancy_pct": field.percent(),
        "hotspots": field.hotspots(top_k=3),
    }

    prompt = (
        "You are a smart-building lobby agent. "
        "Given this JSON describing current crowding, "
        "suggest 1–3 actions to improve flow and experience. "
        "Respond as JSON with an array of simple verbs "
        "like ['open_register','update_sign','do_nothing'].\n"
        + json.dumps(facts, separators=(',',':'))
    )

    # Configure API key from environment
    openai.api_key = os.getenv("OPENAI_API_KEY", "")
    if not openai.api_key:
        print("OPENAI_API_KEY not set; skipping agent call.")
        return

    rsp = await openai.ChatCompletion.acreate(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
    )

    actions = json.loads(rsp.choices[0].message.content)
    print("INTENT actions:", actions)
    # here you might call building APIs or Spaxiom actuators

if __name__ == "__main__":
    asyncio.run(start_runtime())
```

With this one file and a simple YAML config for lobby_floor, you get a live, agent-ready intent stream
without touching MQTT, coordinate math, or custom queue logic.

## Core INTENT Primitives

The initial INTENT release exposes a small but sharp set of patterns:

### OccupancyField

Wraps a 2-D sensor (e.g. FloorGridSensor) and provides:

```python
from spaxiom.intent import OccupancyField

field = OccupancyField(floor_sensor, name="lobby")

field.percent()          # overall occupancy %
field.percent_above(10)  # Condition: occupancy % >= 10
field.hotspots(top_k=3)  # [{x, y, weight}, ...] approximate hotspots
```

### QueueFlow

Turns a floor grid (optionally combined with other signals) into queue estimates:

```python
from spaxiom.intent import QueueFlow

queue = QueueFlow(floor_sensor)

queue.length()        # estimated number of people in line
queue.arrival_rate()  # people / minute (rough estimate)
queue.service_rate()  # people / minute (rough estimate)
queue.wait_time()     # seconds estimate (Little's Law style)
```

### ADLTracker (Activities of Daily Living)

For elder-care / routine monitoring:

```python
from spaxiom.intent import ADLTracker

adl = ADLTracker(
    bed_sensor=bed_mat,
    fridge_sensor=fridge_switch,
    bath_sensor=bath_humidity,
    hall_sensor=hall_floor,
)

# Register callbacks for events
adl.on("got_up",  lambda t: print("Got up at", t))
adl.on("meal",    lambda t: print("Meal event at", t))
adl.on("bath",    lambda t: print("Bath event at", t))
adl.on("walk",    lambda t: print("Walk event at", t))

counts = adl.daily_counts()
```

### FmSteward (Facilities Steward)

For facilities / restroom / consumables care:

```python
from spaxiom.intent import FmSteward

fm = FmSteward(
    door_counter=door_sensor,
    towel_sensor=load_cell,
    bin_sensor=ultrasonic_bin,
    gas_sensor=nh3,
    floor_sensor=wet_strip,
)

if fm.needs_service():
    meta = fm.snapshot()   # compact JSONable facts
    # feed to LLM or CMMS or alerting system
```

Each of these is just a thin, declarative layer over the raw Spaxiom DSL—INTENT doesn't replace the language,
it encodes useful patterns you'd otherwise re-implement in every project.

## When Should I Reach for INTENT?

**Use plain Spaxiom when:**
- You're designing a new pattern from scratch.
- You're adding a novel sensor type or custom spatial layout.

**Use INTENT when:**
- You have familiar scenarios:
  - occupancy / crowding
  - queues and waits
  - daily routines
  - facility-service thresholds
- You want to feed intent into an agent (LLM, planner) as quickly as possible.

In practice, most real-world apps will be a mix: 80% INTENT patterns, 20% custom Spaxiom DSL where your use-case is unique.
