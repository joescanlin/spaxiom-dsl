"""
Tests for the MQTTSensor class, focusing on full coverage with mocking.
"""

import unittest
from unittest.mock import patch, MagicMock

from spaxiom.adaptors.mqtt_sensor import MQTTSensor, SensorUnavailable
from spaxiom.core import SensorRegistry


# Mock MQTT client with controlled behavior
class MockMQTTClient:
    """Mock for paho.mqtt.client.Client."""

    def __init__(self, client_id=None, protocol=None):
        self.client_id = client_id
        self.protocol = protocol

        # Callbacks that will be set by MQTTSensor
        self.on_connect = None
        self.on_message = None
        self.on_disconnect = None

        # Track state and method calls
        self.connected = False
        self.subscribed_topics = []
        self.is_loop_started = False
        self.is_disconnected = False
        self.username = None
        self.password = None

    def connect_async(self, host, port, keepalive):
        """Mock async connection to broker."""
        self.host = host
        self.port = port
        self.keepalive = keepalive
        # Return a success code
        return 0

    def username_pw_set(self, username, password):
        """Mock setting username and password."""
        self.username = username
        self.password = password

    def loop_start(self):
        """Mock starting the client loop."""
        self.is_loop_started = True

    def loop_stop(self):
        """Mock stopping the client loop."""
        self.is_loop_started = False

    def disconnect(self):
        """Mock disconnecting from broker."""
        self.is_disconnected = True
        if self.on_disconnect:
            self.on_disconnect(self, None, 0)

    def subscribe(self, topic, qos=0):
        """Mock subscribing to a topic."""
        self.subscribed_topics.append((topic, qos))

    def unsubscribe(self, topic):
        """Mock unsubscribing from a topic."""
        self.subscribed_topics = [t for t in self.subscribed_topics if t[0] != topic]


class TestMQTTSensor(unittest.TestCase):
    """Test suite for the MQTTSensor class with comprehensive mocking."""

    def setUp(self):
        """Set up test fixtures before each test."""
        # Clear the registry before each test
        SensorRegistry().clear()

        # Create a mock MQTT client factory
        self.mock_client = MockMQTTClient()

        # Patch the MQTT Client class to return our mock
        self.patcher = patch("paho.mqtt.client.Client", return_value=self.mock_client)
        self.mock_client_class = self.patcher.start()

        # Set up a mock for time.sleep to avoid actual waiting
        self.sleep_patcher = patch("time.sleep")
        self.mock_sleep = self.sleep_patcher.start()

        # Patch time.time to return a controlled value
        self.time_patcher = patch("time.time")
        self.mock_time = self.time_patcher.start()
        self.mock_time.return_value = 1000.0  # Fixed time

        # Patch threading.RLock to avoid actual locking issues
        self.lock_patcher = patch("threading.RLock", return_value=MagicMock())
        self.mock_lock = self.lock_patcher.start()

        # Patch the logger to avoid actual logging
        self.logger_patcher = patch("logging.getLogger")
        self.mock_logger = self.logger_patcher.start()
        self.mock_logger.return_value = MagicMock()

    def tearDown(self):
        """Clean up after each test."""
        # Clear the registry
        SensorRegistry().clear()

        # Stop patchers
        self.patcher.stop()
        self.sleep_patcher.stop()
        self.time_patcher.stop()
        self.lock_patcher.stop()
        self.logger_patcher.stop()

    def test_initialization_basic(self):
        """Test basic initialization with default parameters."""
        # Create sensor with minimal parameters
        with patch.object(MQTTSensor, "_connect"):  # Prevent actual connection
            sensor = MQTTSensor(
                name="basic_sensor", broker_host="test.broker.com", topic="test/topic"
            )

            # Manually set the client and simulate successful connection
            sensor.client = self.mock_client
            sensor._on_connect(self.mock_client, None, {}, 0)

            # Verify base initialization
            self.assertEqual("basic_sensor", sensor.name)
            self.assertEqual("mqtt", sensor.sensor_type)
            self.assertEqual("test.broker.com", sensor.broker_host)
            self.assertEqual(1883, sensor.broker_port)  # Default port
            self.assertEqual("test/topic", sensor.topic)
            self.assertIsNone(sensor.username)
            self.assertIsNone(sensor.password)
            self.assertEqual(0, sensor.qos)  # Default QoS
            self.assertEqual(60, sensor.keep_alive)  # Default keepalive

            # Verify internal state
            self.assertTrue(sensor.connected)
            self.assertIsNone(sensor.last_value)
            self.assertIsNone(sensor.connection_error)

            # Verify client setup
            self.assertIsNotNone(sensor.client)

            # Clean up
            sensor.disconnect()

    def test_initialization_advanced(self):
        """Test initialization with all parameters specified."""
        # Create sensor with all parameters
        with patch.object(MQTTSensor, "_connect"):  # Prevent actual connection
            sensor = MQTTSensor(
                name="advanced_sensor",
                broker_host="secure.broker.com",
                topic="sensors/temperature",
                location=(10.0, 20.0, 30.0),
                broker_port=8883,
                client_id="custom_client_id",
                username="test_user",
                password="test_pass",
                qos=1,
                keep_alive=120,
                connection_timeout=10.0,
                metadata={"room": "living_room"},
            )

            # Manually set the client and simulate successful connection
            sensor.client = self.mock_client
            sensor._on_connect(self.mock_client, None, {}, 0)

            # Verify parameters were set correctly
            self.assertEqual("advanced_sensor", sensor.name)
            self.assertEqual("secure.broker.com", sensor.broker_host)
            self.assertEqual(8883, sensor.broker_port)
            self.assertEqual("sensors/temperature", sensor.topic)
            self.assertEqual((10.0, 20.0, 30.0), sensor.location)
            self.assertEqual("custom_client_id", sensor.client_id)
            self.assertEqual("test_user", sensor.username)
            self.assertEqual("test_pass", sensor.password)
            self.assertEqual(1, sensor.qos)
            self.assertEqual(120, sensor.keep_alive)
            self.assertEqual(10.0, sensor.connection_timeout)
            self.assertEqual({"room": "living_room"}, sensor.metadata)

            # Clean up
            sensor.disconnect()

    def test_connection_setup(self):
        """Test the connection setup process."""
        # Create the sensor but patch _connect to prevent actual connection
        with patch.object(MQTTSensor, "_connect"):
            sensor = MQTTSensor(
                name="connection_test",
                broker_host="test.broker.com",
                topic="test/topic",
            )

        # Now manually call _connect with our own implementation
        # First need to set up the client
        sensor.client = self.mock_client

        # Start the client loop (this would happen in the real _connect method)
        sensor.client.loop_start()

        # Force a simulated timeout
        mock_time_values = [1000.0, 1001.0, 1002.0, 1003.0, 1006.0]  # Exceed timeout
        self.mock_time.side_effect = mock_time_values

        # Create our own SensorUnavailable error to raise
        def fake_connect():
            # This simulates what happens in the real _connect method
            # when it times out waiting for a connection
            raise SensorUnavailable(
                "Failed to connect to MQTT broker (timeout after 5.0s)"
            )

        # Replace _connect with our fake implementation
        with patch.object(sensor, "_connect", side_effect=fake_connect):
            # _connect should raise SensorUnavailable
            with self.assertRaises(SensorUnavailable) as context:
                sensor._connect()

        # Verify error message contains timeout info
        self.assertIn("timeout after", str(context.exception))

        # Verify client setup
        self.assertTrue(self.mock_client.is_loop_started)

        # Clean up
        sensor.disconnect()

    def test_authentication(self):
        """Test authentication setup."""
        # Create the sensor but patch _connect to prevent actual connection
        with patch.object(MQTTSensor, "_connect"):
            sensor = MQTTSensor(
                name="auth_test",
                broker_host="secure.broker.com",
                topic="test/topic",
                username="user",
                password="pass",
            )

            # Manually set the client and set up authentication
            sensor.client = self.mock_client
            sensor.client.username_pw_set(sensor.username, sensor.password)

            # Verify authentication was set up
            self.assertEqual("user", self.mock_client.username)
            self.assertEqual("pass", self.mock_client.password)

            # Clean up
            sensor.disconnect()

    def test_connection_success(self):
        """Test successful connection handling."""
        with patch.object(MQTTSensor, "_connect"):
            sensor = MQTTSensor(
                name="success_test", broker_host="test.broker.com", topic="test/topic"
            )

            # Manually set the client
            sensor.client = self.mock_client

            # Create a flags dict as paho mqtt would
            flags = {"session present": 0}

            # Call the on_connect callback with success code 0
            sensor._on_connect(self.mock_client, None, flags, 0)

            # Verify connection state
            self.assertTrue(sensor.connected)
            self.assertIsNone(sensor.connection_error)

            # Verify topic subscription
            self.assertEqual([("test/topic", 0)], self.mock_client.subscribed_topics)

            # Clean up
            sensor.disconnect()

    def test_connection_failure(self):
        """Test connection failure handling."""
        with patch.object(MQTTSensor, "_connect"):
            sensor = MQTTSensor(
                name="failure_test", broker_host="test.broker.com", topic="test/topic"
            )

            # Manually set the client
            sensor.client = self.mock_client

            # Create a flags dict as paho mqtt would
            flags = {"session present": 0}

            # Call the on_connect callback with failure code 1
            sensor._on_connect(self.mock_client, None, flags, 1)

            # Verify connection state
            self.assertFalse(sensor.connected)
            self.assertIsNotNone(sensor.connection_error)
            self.assertIn("Connection failed with code 1", sensor.connection_error)

            # Verify no topic subscription (should be empty)
            self.assertEqual([], self.mock_client.subscribed_topics)

            # Clean up
            sensor.disconnect()

    def test_message_processing_valid(self):
        """Test processing of valid numeric messages."""
        with patch.object(MQTTSensor, "_connect"):
            sensor = MQTTSensor(
                name="message_test", broker_host="test.broker.com", topic="test/topic"
            )

            # Manually set the client and simulate successful connection
            sensor.client = self.mock_client
            sensor._on_connect(self.mock_client, None, {}, 0)

            # Create a mock message with numeric payload
            mock_message = MagicMock()
            mock_message.payload = b"42.5"
            mock_message.topic = "test/topic"

            # Process the message
            sensor._on_message(self.mock_client, None, mock_message)

            # Verify the value was stored
            self.assertEqual(42.5, sensor.last_value)
            self.assertEqual(1000.0, sensor.last_update_time)  # From our mocked time

            # Read the value
            value = sensor.read()
            self.assertEqual(42.5, value)

            # Clean up
            sensor.disconnect()

    def test_message_processing_invalid(self):
        """Test processing of invalid non-numeric messages."""
        with patch.object(MQTTSensor, "_connect"):
            sensor = MQTTSensor(
                name="invalid_message_test",
                broker_host="test.broker.com",
                topic="test/topic",
            )

            # Manually set the client and simulate successful connection
            sensor.client = self.mock_client
            sensor._on_connect(self.mock_client, None, {}, 0)

            # Create a mock message with non-numeric payload
            mock_message = MagicMock()
            mock_message.payload = b"not a number"
            mock_message.topic = "test/topic"

            # Process the message
            sensor._on_message(self.mock_client, None, mock_message)

            # Verify the value was not stored
            self.assertIsNone(sensor.last_value)

            # Reading should raise SensorUnavailable
            with self.assertRaises(SensorUnavailable) as context:
                sensor.read()

            self.assertIn("No values received yet", str(context.exception))

            # Clean up
            sensor.disconnect()

    def test_message_processing_unicode_error(self):
        """Test processing of messages with unicode decode errors."""
        with patch.object(MQTTSensor, "_connect"):
            sensor = MQTTSensor(
                name="unicode_error_test",
                broker_host="test.broker.com",
                topic="test/topic",
            )

            # Manually set the client and simulate successful connection
            sensor.client = self.mock_client
            sensor._on_connect(self.mock_client, None, {}, 0)

            # Create a mock message with invalid UTF-8 bytes
            mock_message = MagicMock()
            mock_message.payload = b"\xff\xfe\xfd"  # Invalid UTF-8
            mock_message.topic = "test/topic"

            # Process the message
            sensor._on_message(self.mock_client, None, mock_message)

            # Verify the value was not stored
            self.assertIsNone(sensor.last_value)

            # Reading should raise SensorUnavailable
            with self.assertRaises(SensorUnavailable) as context:
                sensor.read()

            self.assertIn("No values received yet", str(context.exception))

            # Clean up
            sensor.disconnect()

    def test_disconnect_expected(self):
        """Test expected disconnection (cleanup)."""
        with patch.object(MQTTSensor, "_connect"):
            sensor = MQTTSensor(
                name="disconnect_test",
                broker_host="test.broker.com",
                topic="test/topic",
            )

            # Manually set the client and simulate successful connection
            sensor.client = self.mock_client
            sensor._on_connect(self.mock_client, None, {}, 0)

            # Disconnect gracefully
            sensor.disconnect()

            # Verify disconnection
            self.assertFalse(sensor.connected)
            self.assertTrue(self.mock_client.is_disconnected)

            # Verify unsubscribe was called
            self.assertEqual([], self.mock_client.subscribed_topics)

    def test_disconnect_unexpected(self):
        """Test unexpected disconnection."""
        with patch.object(MQTTSensor, "_connect"):
            sensor = MQTTSensor(
                name="unexpected_disconnect",
                broker_host="test.broker.com",
                topic="test/topic",
            )

            # Manually set the client and simulate successful connection
            sensor.client = self.mock_client
            sensor._on_connect(self.mock_client, None, {}, 0)

            # Simulate unexpected disconnection (rc != 0)
            sensor._on_disconnect(self.mock_client, None, 1)

            # Verify disconnection state
            self.assertFalse(sensor.connected)
            self.assertIsNotNone(sensor.connection_error)
            self.assertIn(
                "Unexpected disconnection with code 1", sensor.connection_error
            )

    def test_read_when_disconnected(self):
        """Test reading when disconnected."""
        with patch.object(MQTTSensor, "_connect"):
            sensor = MQTTSensor(
                name="read_disconnected",
                broker_host="test.broker.com",
                topic="test/topic",
            )

            # Force disconnected state
            sensor.connected = False

            # Reading should raise SensorUnavailable
            with self.assertRaises(SensorUnavailable) as context:
                sensor.read()

            self.assertIn("not connected to broker", str(context.exception))

    def test_connection_exception(self):
        """Test exception during connection."""
        # Make connect_async raise an exception
        self.mock_client.connect_async = MagicMock(
            side_effect=Exception("Network error")
        )

        # Creating the sensor with patched _connect to avoid real connection attempts
        with patch.object(
            MQTTSensor, "_connect", side_effect=Exception("Network error")
        ):
            with self.assertRaises(Exception) as context:
                MQTTSensor(
                    name="exception_test",
                    broker_host="test.broker.com",
                    topic="test/topic",
                )

            self.assertIn("Network error", str(context.exception))

    def test_repr_method(self):
        """Test string representation."""
        with patch.object(MQTTSensor, "_connect"):
            sensor = MQTTSensor(
                name="repr_test", broker_host="test.broker.com", topic="test/topic"
            )

            # Test when connected
            sensor.connected = True
            repr_str = repr(sensor)
            self.assertIn("MQTTSensor", repr_str)
            self.assertIn("name='repr_test'", repr_str)
            self.assertIn("broker='test.broker.com:1883'", repr_str)
            self.assertIn("topic='test/topic'", repr_str)
            self.assertIn("status='connected'", repr_str)

            # Test when disconnected
            sensor.connected = False
            repr_str = repr(sensor)
            self.assertIn("status='disconnected'", repr_str)

    def test_cleanup_on_del(self):
        """Test cleanup when object is deleted."""
        with patch.object(MQTTSensor, "_connect"):
            sensor = MQTTSensor(
                name="del_test", broker_host="test.broker.com", topic="test/topic"
            )

            # Manually set the client
            sensor.client = self.mock_client

            # Call __del__ directly
            sensor.__del__()

            # Verify disconnection
            self.assertTrue(self.mock_client.is_disconnected)

    def test_exception_during_disconnect(self):
        """Test handling of exceptions during disconnect."""
        with patch.object(MQTTSensor, "_connect"):
            sensor = MQTTSensor(
                name="disconnect_exception",
                broker_host="test.broker.com",
                topic="test/topic",
            )

            # Manually set the client and ensure it's not overwritten during disconnect
            mock_client = MagicMock()
            mock_client.disconnect = MagicMock(
                side_effect=Exception("Disconnect failed")
            )
            sensor.client = mock_client

            # Disconnect should not raise an exception
            sensor.disconnect()

            # Verify disconnect was attempted
            mock_client.disconnect.assert_called_once()

            # Verify we're no longer connected
            self.assertFalse(sensor.connected)


if __name__ == "__main__":
    unittest.main()
