# Spaxiom-DSL

An embedded domain-specific language for spatial sensor fusion and AI.

## Installation

```bash
pip install -e .
```

## Quick Example

```python
from spaxiom import Spatial, fuse
result = fuse(Spatial.from_lidar(lidar_data), Spatial.from_camera(camera_data))
```

## License

MIT 