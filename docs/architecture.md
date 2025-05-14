# Spaxiom Architecture

This page provides an overview of the Spaxiom DSL architecture and how its components interact.

## Architecture Diagram

The following diagram shows the high-level architecture of the Spaxiom DSL framework:

![Spaxiom Architecture Diagram](architecture_diagram.drawio)

You can open this diagram in [diagrams.net](https://app.diagrams.net/) to explore it interactively.

## Key Components

### Data Sources
Spaxiom supports various sensor types to collect data, including:
- RandomSensor
- GPIOSensor
- MQTTSensor
- FileSensor  
- SimVector

### Runtime
The core runtime handles:
- Sensor polling
- Event loop management
- History tracking
- Plugin system

### Conditions
Conditions evaluate sensor data against specified criteria:
- Basic conditions (λ)
- Logical operators (&, |, ~)
- Temporal operators (within, sequence)
- Entity-based conditions (exists)

### Actions
Actions execute when conditions are met:
- Event handlers
- GPIO outputs
- Custom callbacks

### Additional Components
- **Privacy Manager**: Controls access to sensitive sensor data
- **AI Module**: Handles ONNX model integration and entity detection
- **Entity System**: Manages entity tracking and attributes
- **Spatial Components**: Defines zones and spatial relationships

## Data Flow

The primary data flow follows this pattern:
1. Sensors collect data
2. Runtime processes the data
3. Conditions evaluate the data
4. Actions are triggered based on condition results

Components such as the Privacy Manager, AI Module, and Spatial Components integrate with this main flow to provide additional functionality. 