"""
Plugin system for Spaxiom DSL.

This module provides a plugin mechanism for extending the Spaxiom DSL with custom
functionality. Plugins can add new sensor types, actuators, or other extensions.

Plugins are automatically loaded from the spaxiom_site_plugins namespace if available.
"""

import pkgutil
import importlib
import logging
import traceback
from typing import Callable, List

# List of registered plugin functions
PLUGINS: List[Callable[[], None]] = []

# Logger for plugin operations
logger = logging.getLogger(__name__)


def register_plugin(func: Callable[[], None]) -> Callable[[], None]:
    """
    Decorator to register a function as a Spaxiom plugin.

    Plugin functions are called during runtime startup to extend
    the DSL with custom functionality (e.g., adding new sensor types).

    Args:
        func: Function to register as a plugin

    Returns:
        The function unchanged

    Example:
        ```python
        # In your plugin module:
        from spaxiom import register_plugin

        @register_plugin
        def setup_custom_sensors():
            # Register custom sensor types, actuators, etc.
            pass
        ```
    """
    if func not in PLUGINS:
        logger.debug(f"Registering plugin: {func.__name__}")
        PLUGINS.append(func)
    return func


def discover_and_load_plugins() -> None:
    """
    Discover and load plugins from the spaxiom_site_plugins namespace.

    This function searches for modules in the spaxiom_site_plugins namespace
    and imports them, which triggers the registration of any functions
    decorated with @register_plugin.

    Returns:
        None
    """
    logger.debug("Discovering plugins...")

    # Try to import from spaxiom_site_plugins namespace
    namespace = "spaxiom_site_plugins"
    try:
        # Find all modules in the namespace
        imported = importlib.import_module(namespace)
        for _, name, is_pkg in pkgutil.iter_modules(imported.__path__, f"{namespace}."):
            try:
                logger.debug(f"Found plugin module: {name}")
                importlib.import_module(name)
            except ImportError:
                logger.warning(f"Failed to import plugin module: {name}")
                logger.debug(traceback.format_exc())
    except ImportError:
        # namespace package doesn't exist, which is fine
        logger.debug(f"No {namespace} package found.")
    except Exception as e:
        logger.warning(f"Error discovering plugins: {str(e)}")
        logger.debug(traceback.format_exc())


def initialize_plugins() -> None:
    """
    Initialize all registered plugins.

    This function calls each registered plugin function in the order they were
    registered. It should be called during runtime startup.

    Returns:
        None
    """
    logger.debug(f"Initializing {len(PLUGINS)} plugins...")

    for plugin_func in PLUGINS:
        try:
            logger.debug(f"Initializing plugin: {plugin_func.__name__}")
            plugin_func()
        except Exception as e:
            logger.error(f"Error initializing plugin {plugin_func.__name__}: {str(e)}")
            logger.debug(traceback.format_exc())


def reset_plugins() -> None:
    """
    Reset the plugin system by clearing all registered plugins.

    This is primarily useful for testing.

    Returns:
        None
    """
    logger.debug("Resetting plugin system...")
    PLUGINS.clear()
