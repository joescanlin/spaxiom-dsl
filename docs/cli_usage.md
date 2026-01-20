# Spaxiom CLI Usage Guide

Spaxiom provides a command-line interface (CLI) for running Spaxiom DSL scripts and managing edge deployments. The CLI offers rich terminal output with colored tables, progress spinners, and interactive menus.

## Installation

The CLI is automatically installed with the Spaxiom package:

```bash
pip install spaxiom
```

For enhanced CLI features (colored output, interactive menus, REPL shell):

```bash
pip install spaxiom[cli]
```

For edge deployment features:

```bash
pip install spaxiom[edge,cli]
```

## Commands Overview

| Command | Description |
|---------|-------------|
| `spax run` | Run a Spaxiom DSL script |
| `spax new` | Create a new script scaffold |
| `spax version` | Show version and dependency info |
| `spax edge start` | Start the edge server |
| `spax edge status` | Show edge server status |
| `spax edge agents` | List and manage agents |
| `spax edge menu` | Interactive menu (arrow-key navigation) |
| `spax edge shell` | Interactive REPL shell |

## Running Scripts

### Basic Usage

```bash
spax run <script_path> [options]
```

### Options

- `--poll-ms`: Polling interval in milliseconds (default: 100)
- `--history-length`: Maximum history entries per condition (default: 1000)
- `--config`: YAML configuration file for sensors and zones
- `--verbose`: Enable verbose logging

### Examples

```bash
# Run with default settings
spax run examples/occupancy_demo.py

# Run with faster polling
spax run examples/sequence_demo.py --poll-ms 50

# Run with verbose logging
spax run examples/demo.py --verbose
```

## Creating New Scripts

Generate a new Spaxiom script scaffold:

```bash
spax new <script_name> [options]
```

### Options

- `--output-dir`: Output directory (default: current directory)
- `--sensors`: Number of sensor placeholders (default: 2)
- `--zones`: Number of zone placeholders (default: 1)
- `--privacy/--no-privacy`: Include privacy settings (default: enabled)

### Examples

```bash
# Create a basic demo script
spax new demo

# Create a complex script with more sensors
spax new complex_demo --sensors 5 --zones 3

# Create in a specific directory
spax new my_app --output-dir ./projects
```

## Edge Commands

The `spax edge` command group manages edge deployments for production IoT environments.

### Starting the Edge Server

```bash
spax edge start [options]
```

**Options:**

- `--host`: Host to bind to (default: 0.0.0.0)
- `--port`: Port number (default: 8080)
- `--db`: Database path (default: ~/.spaxiom/edge.db)
- `--reload`: Enable auto-reload for development

**Example:**

```bash
# Start on default port
spax edge start

# Start on custom port with auto-reload
spax edge start --port 8085 --reload
```

### Checking Status

```bash
spax edge status [--url URL]
```

Shows system health, sensor counts, active agents, and resource usage in a formatted table.

### Managing Agents

```bash
# List all agents
spax edge agents list

# Show agent details
spax edge agents info <agent_id>

# Start/stop agents
spax edge agents start <agent_id>
spax edge agents stop <agent_id>

# Configure summary schedules
spax edge agents schedule set --name daily --cadence 1d --format md
spax edge agents schedule list

# Generate summaries and action previews
spax edge agents summary --since 24h --format md --out ./summary.md
spax edge agents preview --agent-id <agent_id> --window 2h

# Replay scenarios and stream live events
spax edge agents playback ./scenario.json
spax edge agents feed --agent-id <agent_id>
```

### Interactive Menu

Launch an arrow-key navigable menu for common operations:

```bash
spax edge menu
```

The menu provides quick access to:

- View system status
- Manage sensors
- Configure zones
- Deploy patterns
- Monitor agents
- Access settings

Use arrow keys to navigate and Enter to select.

### Interactive Shell

Start a REPL shell with tab completion and command history:

```bash
spax edge shell
```

**Shell Commands:**

| Command | Description |
|---------|-------------|
| `status` | Show system status |
| `sensors` | List all sensors |
| `zones` | List all zones |
| `agents` | List running agents |
| `start <id>` | Start an agent |
| `stop <id>` | Stop an agent |
| `health` | Show health metrics |
| `help` | Show available commands |
| `exit` | Exit the shell |

**Example session:**

```
spaxiom> status
System: healthy
Sensors: 12 registered
Agents: 3 running

spaxiom> agents
ID          Pattern         Status    Ticks
agent_001   occupancy       running   1,234
agent_002   queue_flow      running   856
agent_003   adl_tracker     stopped   0

spaxiom> start agent_003
Agent agent_003 started

spaxiom> exit
```

## Version Information

Show version and installed optional dependencies:

```bash
spax version
```

Output includes:

- Spaxiom version
- Python version
- Optional dependencies status (Rich, FastAPI, etc.)

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SPAXIOM_DB_PATH` | Database file path | `~/.spaxiom/edge.db` |
| `SPAXIOM_LOG_LEVEL` | Logging level | `INFO` |
| `SPAXIOM_API_HOST` | API server host | `0.0.0.0` |
| `SPAXIOM_API_PORT` | API server port | `8080` |

## Getting Help

```bash
# General help
spax --help

# Command-specific help
spax run --help
spax edge --help
spax edge start --help
```
