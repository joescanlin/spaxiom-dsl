"""
File Sensor module for reading data from CSV files in Spaxiom DSL.
"""

import csv
import os
from typing import Optional, Dict, Any, Tuple, List, Union

from spaxiom.sensor import Sensor


class FileSensor(Sensor):
    """
    A sensor that streams numeric values from a CSV file.

    This sensor reads one row per call to `read()`, allowing you to
    process CSV data as if it were coming from a real-time sensor.

    Attributes:
        file_path: Path to the CSV file
        column_name: Name of the column containing the numeric data
        delimiter: CSV delimiter character
        unit: Optional unit for the data (e.g., "m", "s", "degC")
        skip_header: Whether to skip the header row
        loop: Whether to loop back to the beginning after reaching the end
        current_row: Current row index in the file
        data: Cached data from the CSV file
    """

    def __init__(
        self,
        name: str,
        file_path: str,
        column_name: str,
        location: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        delimiter: str = ",",
        unit: Optional[str] = None,
        skip_header: bool = True,
        loop: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize a file sensor.

        Args:
            name: Unique name for the sensor
            file_path: Path to the CSV file
            column_name: Name of the column containing the numeric data
            location: Spatial coordinates (x, y, z) of the sensor
            delimiter: CSV delimiter character
            unit: Optional unit for the data (e.g., "m", "s", "degC")
            skip_header: Whether to skip the header row
            loop: Whether to loop back to the beginning after reaching the end
            metadata: Optional metadata dictionary
        """
        # First call the parent constructor to register the sensor
        super().__init__(
            name=name, sensor_type="file", location=location, metadata=metadata
        )

        # Then set additional attributes
        self.file_path = file_path
        self.column_name = column_name
        self.delimiter = delimiter
        self.unit_str = unit
        self.skip_header = skip_header
        self.loop = loop
        self.current_row = 0
        self.data: List[float] = []
        self.column_index = -1

        # Ensure the file exists
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"CSV file not found: {file_path}")

        # Load the data from the file
        self._load_data()

    def _load_data(self) -> None:
        """
        Load data from the CSV file and cache it.
        """
        self.data = []

        with open(self.file_path, "r", newline="") as file:
            reader = csv.reader(file, delimiter=self.delimiter)

            # Read the header row to find the column index
            if self.skip_header:
                header = next(reader)
                if self.column_name not in header:
                    raise ValueError(
                        f"Column '{self.column_name}' not found in CSV header. "
                        f"Available columns: {', '.join(header)}"
                    )
                self.column_index = header.index(self.column_name)

            # Read all rows and store the values from the specified column
            for row in reader:
                try:
                    # If no header was specified, use the column index directly
                    if self.column_index == -1:
                        try:
                            # Try to parse the column name as an integer index
                            col_idx = int(self.column_name)
                            if col_idx < 0 or col_idx >= len(row):
                                raise ValueError(
                                    f"Column index {col_idx} out of range (0-{len(row)-1})"
                                )
                            value = float(row[col_idx])
                        except ValueError:
                            # If column_name isn't an integer, treat it as a string index
                            # This would be uncommon without a header, but still possible
                            if self.column_name not in row:
                                raise ValueError(
                                    f"Column '{self.column_name}' not found in row"
                                )
                            value = float(row[row.index(self.column_name)])
                    else:
                        # Use the column index determined from the header
                        value = float(row[self.column_index])

                    self.data.append(value)
                except (ValueError, IndexError) as e:
                    # Skip rows with invalid data
                    print(f"Warning: Skipping row with invalid data: {e}")

    def _read_raw(self) -> Union[float, None]:
        """
        Read the next value from the CSV data.

        Returns:
            The next numeric value from the CSV file, or None if the end is reached
            and loop is False
        """
        if not self.data:
            return None

        # Check if we've reached the end of the data
        if self.current_row >= len(self.data):
            if self.loop:
                # Reset to the beginning if looping is enabled
                self.current_row = 0
            else:
                # Return None if we're at the end and not looping
                return None

        # Get the current value and advance the row counter
        value = self.data[self.current_row]
        self.current_row += 1

        return value

    def reset(self) -> None:
        """
        Reset the sensor to the first row of data.
        """
        self.current_row = 0

    def __repr__(self) -> str:
        """Return a string representation of the file sensor."""
        return (
            f"FileSensor(name='{self.name}', file='{os.path.basename(self.file_path)}', "
            f"column='{self.column_name}', row={self.current_row}/{len(self.data)})"
        )
