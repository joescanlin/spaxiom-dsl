# Changelog

All notable changes to this project will be documented in this file.

## [0.1.0-rc2] - 2025-06-01

### Fixed
- Fixed README formatting to properly display badges and ASCII art
- Improved PyPI package appearance

## [0.1.0-rc1] - 2025-06-01

### Added

- **MQTT Integration**: Complete support for MQTT brokers
  - `MQTTSensor` class for subscribing to topics
  - Secure authentication with username/password
  - Automatic reconnection handling

- **YAML Configuration**: Support for YAML-based sensor configuration
  - Load sensors directly from YAML files
  - Simplified deployment for complex sensor networks
  - Configuration validation with helpful error messages

- **SimVector Module**: Advanced sensor simulation capabilities
  - Vector-based approach for efficient time series simulation
  - Configurable interpolation between keyframes
  - Support for sine, step, and custom patterns

- **Plugin System**: Extensible architecture for custom components
  - Register custom sensors, outputs, and processing components
  - Runtime discovery of extensions
  - Plugin isolation for better stability

- **ONNX Inference**: Added support for AI model inference using ONNX Runtime
  - Includes person detection example with ONNX model integration
  - Automatic entity creation from detection results

- **GPIO Adapter**: Hardware integration for Raspberry Pi and similar devices
  - `GPIOSensor` class for reading digital inputs
  - `GPIOOutput` class for controlling output pins
  - Support for RPi.GPIO and gpiozero libraries

- **Privacy Tags**: Enhanced privacy controls for sensor data
  - Sensors can be marked as private to control data visibility
  - Runtime automatically redacts private sensor values in logs
  - Support for privacy warnings when accessing restricted data

- **Sensor Summarization**: Statistical analysis for sensor data streams
  - `summary()` method for Condition instances
  - Returns a RollingSummary object for tracking statistics
  - Support for min, max, mean, variance calculations

- **CLI Scaffold**: Command-line tools for project creation
  - `spax-run new` command for generating script templates
  - Customizable sensor and zone placeholders
  - Privacy settings configuration
  - Ready-to-run application structure

### Improved

- Enhanced error handling across all modules
- Comprehensive test coverage (over 80%)
- Improved documentation with MQTT, YAML, and simulation examples
- Performance optimizations for large sensor networks

### Fixed

- Resolved issues with asyncio event loop in shutdown process
- Fixed thread safety issues in sensor registry
- Corrected behavior of temporal operators in edge cases
- Several bug fixes and performance improvements 