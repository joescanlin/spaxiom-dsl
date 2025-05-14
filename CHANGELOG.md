# Changelog

All notable changes to this project will be documented in this file.

## [0.1.0-beta] - 2025-05-14

### Added

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
- More comprehensive test coverage (over 60%)
- Updated documentation with privacy and hardware examples

### Fixed

- Several bug fixes and performance improvements 