#!/usr/bin/env python3
"""
SimVector Benchmark

This script measures the throughput (sensor value updates per second) for a SimVector
with 1,000 sensors running for 10 seconds.
"""

import time
import json
import platform
import argparse
import os
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


def get_system_info():
    """Get basic system information for context."""
    return {
        "platform": platform.platform(),
        "processor": platform.processor(),
        "python_version": platform.python_version(),
        "cpu_count": os.cpu_count(),
    }


def run_benchmark(
    num_sensors: int = 1000,
    duration: float = 10.0,
    hz: float = 30.0,
    output_json: bool = False,
    json_file: str = None,
    num_threads: int = 4,
):
    """
    Run the SimVector benchmark.

    Args:
        num_sensors: Number of sensors to include in the benchmark
        duration: Duration of the benchmark in seconds
        hz: Update frequency for the SimVector
        output_json: Whether to output results as JSON
        json_file: Path to save JSON results (if None, prints to stdout)
        num_threads: Number of threads to use for multi-threaded benchmark
    """
    print("\nSimVector Benchmark")
    print("==================\n")
    print("Configuration:")
    print(f"  - Number of sensors: {num_sensors}")
    print(f"  - Duration: {duration} seconds")
    print(f"  - Update frequency: {hz} Hz")
    print(f"  - Threads: {num_threads}\n")

    # Store benchmark configuration
    benchmark_config = {
        "num_sensors": num_sensors,
        "duration_seconds": duration,
        "update_frequency_hz": hz,
        "num_threads": num_threads,
    }

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

    # Store the results
    benchmark_results = {}

    try:
        # Give the simulation a moment to initialize
        time.sleep(0.5)

        # Run single-threaded benchmark
        throughput_single = benchmark_single_thread(sim, duration)

        # Run multi-threaded benchmark
        throughput_multi = benchmark_multi_thread(sim, duration, num_threads)

        # Store results
        benchmark_results = {
            "system_info": get_system_info(),
            "config": benchmark_config,
            "results": {
                "single_thread_throughput": throughput_single,
                "multi_thread_throughput": throughput_multi,
                "overall_events_per_second": throughput_multi,
                "updates_per_sensor_per_second": throughput_multi / num_sensors,
                "timestamp": time.time(),
                "timestamp_formatted": time.strftime("%Y-%m-%d %H:%M:%S"),
            },
        }

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

        # Output JSON if requested
        if output_json:
            if json_file:
                with open(json_file, "w") as f:
                    json.dump(benchmark_results, f, indent=2)
                print(f"\nResults saved to {json_file}")
            else:
                print("\nJSON Output:")
                print(json.dumps(benchmark_results, indent=2))

    finally:
        # Stop the simulation
        sim.stop()
        print("\nSimulation stopped.")

    return benchmark_results


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="SimVector performance benchmark")
    parser.add_argument(
        "--sensors", type=int, default=1000, help="Number of sensors (default: 1000)"
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=10.0,
        help="Benchmark duration in seconds (default: 10.0)",
    )
    parser.add_argument(
        "--hz",
        type=float,
        default=30.0,
        help="SimVector update frequency (default: 30.0)",
    )
    parser.add_argument(
        "--threads",
        type=int,
        default=4,
        help="Number of threads for multi-threaded benchmark (default: 4)",
    )
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    parser.add_argument(
        "--output", type=str, default=None, help="Output file for JSON results"
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_benchmark(
        num_sensors=args.sensors,
        duration=args.duration,
        hz=args.hz,
        output_json=args.json,
        json_file=args.output,
        num_threads=args.threads,
    )
