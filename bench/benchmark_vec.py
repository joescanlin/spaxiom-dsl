#!/usr/bin/env python3
"""
SimVector Benchmark

This script measures the throughput (sensor value updates per second) for a SimVector
with 1,000 sensors running for 10 seconds.
"""

import time
from concurrent.futures import ThreadPoolExecutor

from spaxiom import SimVector


def track_updates(sim_vector, duration: float = 10.0) -> int:
    """
    Track how many sensor updates occur in the given duration.

    Args:
        sim_vector: The SimVector instance to benchmark
        duration: Duration of the benchmark in seconds

    Returns:
        Total number of sensor reads completed
    """
    start_time = time.time()
    end_time = start_time + duration
    total_reads = 0

    # Track reads for the specified duration
    while time.time() < end_time:
        # Read all sensors to track how many reads can be done
        for sensor in sim_vector.sensors:
            sensor.read()
            total_reads += 1

    return total_reads


def benchmark_single_thread(sim_vector, duration: float = 10.0) -> float:
    """
    Benchmark single-threaded read performance.

    Args:
        sim_vector: The SimVector instance to benchmark
        duration: Duration of the benchmark in seconds

    Returns:
        Updates per second (throughput)
    """
    print(f"Running single-threaded benchmark for {duration:.1f} seconds...")

    total_reads = track_updates(sim_vector, duration)

    # Calculate throughput
    throughput = total_reads / duration
    return throughput


def benchmark_multi_thread(
    sim_vector, duration: float = 10.0, num_threads: int = 4
) -> float:
    """
    Benchmark multi-threaded read performance.

    Args:
        sim_vector: The SimVector instance to benchmark
        duration: Duration of the benchmark in seconds
        num_threads: Number of threads to use for reading sensors

    Returns:
        Updates per second (throughput)
    """
    print(
        f"Running multi-threaded benchmark ({num_threads} threads) for {duration:.1f} seconds..."
    )

    start_time = time.time()
    total_reads = 0

    # Divide sensors among threads
    sensors_per_thread = len(sim_vector.sensors) // num_threads

    # Function for each thread to execute
    def thread_func(sensors):
        nonlocal total_reads
        local_reads = 0
        end_time = start_time + duration

        while time.time() < end_time:
            for sensor in sensors:
                sensor.read()
                local_reads += 1

        return local_reads

    # Create thread groups
    sensor_groups = []
    for i in range(num_threads):
        start_idx = i * sensors_per_thread
        end_idx = (
            start_idx + sensors_per_thread
            if i < num_threads - 1
            else len(sim_vector.sensors)
        )
        sensor_groups.append(sim_vector.sensors[start_idx:end_idx])

    # Run threads
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        results = list(executor.map(thread_func, sensor_groups))

    # Sum up total reads
    total_reads = sum(results)

    # Calculate throughput
    throughput = total_reads / duration
    return throughput


def run_benchmark(num_sensors: int = 1000, duration: float = 10.0, hz: float = 30.0):
    """
    Run the SimVector benchmark.

    Args:
        num_sensors: Number of sensors to include in the benchmark
        duration: Duration of the benchmark in seconds
        hz: Update frequency for the SimVector
    """
    print("\nSimVector Benchmark")
    print("==================\n")
    print("Configuration:")
    print(f"  - Number of sensors: {num_sensors}")
    print(f"  - Duration: {duration} seconds")
    print(f"  - Update frequency: {hz} Hz\n")

    # Create the SimVector with specified number of sensors
    print(f"Creating SimVector with {num_sensors} sensors...")
    sim = SimVector(
        n=num_sensors,
        hz=hz,
        name_prefix="bench",
        # Use smaller amplitude range for more stable readings
        amplitude_range=(0.9, 1.1),
        # Use consistent frequency for predictable behavior
        frequency_range=(0.5, 0.5),
    )

    # Start the simulation
    sim.start()
    print("Simulation started.")

    try:
        # Give the simulation a moment to initialize
        time.sleep(0.5)

        # Run single-threaded benchmark
        throughput_single = benchmark_single_thread(sim, duration)

        # Run multi-threaded benchmark
        throughput_multi = benchmark_multi_thread(sim, duration)

        # Print results
        print("\nResults:")
        print(
            f"  - Single-threaded throughput: {throughput_single:.2f} sensor reads/second"
        )
        print(
            f"  - Multi-threaded throughput: {throughput_multi:.2f} sensor reads/second"
        )
        print(f"  - Overall events: {throughput_multi:.2f} sensor updates/second")
        print(
            f"  - Per-sensor updates: {throughput_multi/num_sensors:.2f} updates/sensor/second"
        )

    finally:
        # Stop the simulation
        sim.stop()
        print("\nSimulation stopped.")


if __name__ == "__main__":
    run_benchmark(num_sensors=1000, duration=10.0, hz=30.0)
