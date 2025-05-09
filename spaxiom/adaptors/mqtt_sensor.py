"""
MQTT Sensor module for connecting to MQTT brokers in Spaxiom DSL.
"""

import time
import threading
import logging
from typing import Optional, Dict, Any, Tuple
import paho.mqtt.client as mqtt

from spaxiom.sensor import Sensor


class SensorUnavailable(Exception):
    """Exception raised when a sensor is unavailable."""

    pass


class MQTTSensor(Sensor):
    """
    A sensor that subscribes to an MQTT topic and returns the latest numeric value.

    This sensor connects to an MQTT broker, subscribes to a specified topic,
    and returns the most recent numeric payload when `read()` is called.

    Attributes:
        broker_host: Hostname or IP address of the MQTT broker
        broker_port: Port number of the MQTT broker
        topic: The MQTT topic to subscribe to
        client_id: Unique client ID for the MQTT connection
        username: Optional username for broker authentication
        password: Optional password for broker authentication
        qos: MQTT Quality of Service level (0, 1, or 2)
        last_value: The most recent numeric value received from the topic
        connected: Whether the sensor is currently connected to the broker
    """

    def __init__(
        self,
        name: str,
        broker_host: str,
        topic: str,
        location: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        broker_port: int = 1883,
        client_id: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        qos: int = 0,
        keep_alive: int = 60,
        connection_timeout: float = 5.0,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize an MQTT sensor.

        Args:
            name: Unique name for the sensor
            broker_host: Hostname or IP address of the MQTT broker
            topic: The MQTT topic to subscribe to
            location: Spatial coordinates (x, y, z) of the sensor
            broker_port: Port number of the MQTT broker (default 1883)
            client_id: Unique client ID for the MQTT connection (default: auto-generated)
            username: Optional username for broker authentication
            password: Optional password for broker authentication
            qos: MQTT Quality of Service level (0, 1, or 2)
            keep_alive: Keep alive interval in seconds for the MQTT connection
            connection_timeout: Time to wait for a connection in seconds
            metadata: Optional metadata dictionary
        """
        # First call the parent constructor to register the sensor
        super().__init__(
            name=name, sensor_type="mqtt", location=location, metadata=metadata
        )

        # Then set additional attributes
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.topic = topic
        self.client_id = client_id
        self.username = username
        self.password = password
        self.qos = qos
        self.keep_alive = keep_alive
        self.connection_timeout = connection_timeout

        # Internal state
        self.last_value: Optional[float] = None
        self.last_update_time: Optional[float] = None
        self.connected = False
        self.connection_error: Optional[str] = None
        self.client = None
        self.lock = threading.RLock()  # For thread-safe access to last_value

        # Set up logging
        self.logger = logging.getLogger(__name__)

        # Connect to the broker and start subscription
        self._connect()

    def _connect(self) -> None:
        """
        Connect to the MQTT broker and subscribe to the topic.
        """
        try:
            # Create a new client instance
            self.client = mqtt.Client(client_id=self.client_id, protocol=mqtt.MQTTv311)

            # Set up callbacks
            self.client.on_connect = self._on_connect
            self.client.on_message = self._on_message
            self.client.on_disconnect = self._on_disconnect

            # Set up authentication if provided
            if self.username and self.password:
                self.client.username_pw_set(self.username, self.password)

            # Connect to the broker
            self.client.connect_async(
                host=self.broker_host,
                port=self.broker_port,
                keepalive=self.keep_alive,
            )

            # Start the MQTT loop in a background thread
            self.client.loop_start()

            # Wait for the connection to be established
            start_time = time.time()
            while (
                not self.connected
                and time.time() - start_time < self.connection_timeout
            ):
                time.sleep(0.1)

            if not self.connected:
                raise SensorUnavailable(
                    f"Failed to connect to MQTT broker at {self.broker_host}:{self.broker_port} "
                    f"(timeout after {self.connection_timeout}s): {self.connection_error or 'Unknown error'}"
                )

        except Exception as e:
            self.logger.error(f"Error connecting to MQTT broker: {str(e)}")
            self.connected = False
            self.connection_error = str(e)
            if self.client:
                try:
                    self.client.loop_stop()
                except Exception:
                    pass  # Ignore errors during cleanup
            raise SensorUnavailable(f"Failed to connect to MQTT broker: {str(e)}")

    def _on_connect(
        self, client: mqtt.Client, userdata: Any, flags: Dict[str, int], rc: int
    ) -> None:
        """
        Callback for when the client connects to the broker.

        Args:
            client: The MQTT client instance
            userdata: User data passed to the client
            flags: Response flags from the broker
            rc: Return code from the connection
        """
        if rc == 0:
            # Successful connection
            self.connected = True
            self.connection_error = None
            self.logger.info(
                f"Connected to MQTT broker at {self.broker_host}:{self.broker_port}"
            )

            # Subscribe to the topic
            client.subscribe(self.topic, qos=self.qos)
            self.logger.info(f"Subscribed to topic: {self.topic}")
        else:
            # Connection failed
            self.connected = False
            self.connection_error = f"Connection failed with code {rc}"
            self.logger.error(
                f"Connection to MQTT broker failed with code {rc}. "
                f"See paho-mqtt documentation for error codes."
            )

    def _on_message(
        self, client: mqtt.Client, userdata: Any, message: mqtt.MQTTMessage
    ) -> None:
        """
        Callback for when a message is received from the broker.

        Args:
            client: The MQTT client instance
            userdata: User data passed to the client
            message: The message received from the broker
        """
        try:
            # Try to convert the payload to a float
            payload = message.payload.decode("utf-8").strip()
            value = float(payload)

            # Update the last value with a lock for thread safety
            with self.lock:
                self.last_value = value
                self.last_update_time = time.time()

            self.logger.debug(f"Received value {value} on topic {message.topic}")
        except (ValueError, UnicodeDecodeError) as e:
            self.logger.warning(
                f"Received non-numeric payload on topic {message.topic}: {str(e)}"
            )

    def _on_disconnect(self, client: mqtt.Client, userdata: Any, rc: int) -> None:
        """
        Callback for when the client disconnects from the broker.

        Args:
            client: The MQTT client instance
            userdata: User data passed to the client
            rc: Return code from the disconnection
        """
        self.connected = False
        if rc != 0:
            self.connection_error = f"Unexpected disconnection with code {rc}"
            self.logger.warning(
                f"Unexpected disconnection from MQTT broker with code {rc}"
            )
        else:
            self.logger.info("Disconnected from MQTT broker")

    def _read_raw(self) -> float:
        """
        Read the latest value from the MQTT topic.

        Returns:
            The latest numeric value received from the MQTT topic

        Raises:
            SensorUnavailable: If the sensor is not connected to the broker
        """
        if not self.connected:
            raise SensorUnavailable(
                f"MQTT sensor {self.name} is not connected to broker {self.broker_host}:{self.broker_port}"
            )

        with self.lock:
            if self.last_value is None:
                raise SensorUnavailable(
                    f"No values received yet from topic {self.topic}"
                )
            return self.last_value

    def __del__(self) -> None:
        """Clean up resources when the object is deleted."""
        self.disconnect()

    def disconnect(self) -> None:
        """Disconnect from the MQTT broker and clean up resources."""
        if self.client:
            try:
                self.client.unsubscribe(self.topic)
                self.client.loop_stop()
                self.client.disconnect()
            except Exception as e:
                self.logger.warning(f"Error disconnecting from MQTT broker: {str(e)}")
            finally:
                self.connected = False
                self.client = None

    def __repr__(self) -> str:
        """Return a string representation of the MQTT sensor."""
        status = "connected" if self.connected else "disconnected"
        return (
            f"MQTTSensor(name='{self.name}', "
            f"broker='{self.broker_host}:{self.broker_port}', "
            f"topic='{self.topic}', "
            f"status='{status}')"
        )
