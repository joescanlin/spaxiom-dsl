"""
test_safety_export_uppaal.py - Paper Parity Test

Tests UPPAAL timed automaton export:
- verify.compile_to_uppaal()
- Valid UPPAAL XML output
- Clock/timing modeling

Reference: Paper Section 7.3 "Formal semantics and denotational interpretation"
Proving Example: examples/paper/safety_export_uppaal.py
"""

import os
import tempfile
import xml.etree.ElementTree as ET

import pytest

# Skip entire module if spaxiom.safety not yet implemented (Step 5)
pytest.importorskip("spaxiom.safety", reason="Requires Step 5: safety module")

from spaxiom.safety import (
    compare,
    within,
    verifiable,
    verify,
)
from spaxiom.safety.verify import UppaalAutomaton, compile_to_uppaal


class TestUppaalExportAPI:
    """Tests for UPPAAL export API."""

    def test_verify_module_exists(self):
        """spaxiom.safety.verify module must exist."""
        assert verify is not None

    def test_compile_to_uppaal_exists(self):
        """verify.compile_to_uppaal() function must exist."""
        assert callable(compile_to_uppaal)

    def test_compile_to_uppaal_returns_automaton(self):
        """compile_to_uppaal() returns UppaalAutomaton."""
        cond = verifiable(compare("temp", "<", 100), "temp_safe")
        automaton = compile_to_uppaal([cond], name="TestMonitor")
        assert isinstance(automaton, UppaalAutomaton)


class TestUppaalAutomaton:
    """Tests for generated UPPAAL automaton."""

    def test_automaton_has_save_method(self):
        """Automaton must have save(filename) method."""
        cond = verifiable(compare("temp", "<", 100), "temp_safe")
        automaton = compile_to_uppaal([cond])
        assert hasattr(automaton, "save")
        assert callable(automaton.save)

    def test_automaton_has_to_xml_method(self):
        """Automaton must have to_xml() method."""
        cond = verifiable(compare("temp", "<", 100), "temp_safe")
        automaton = compile_to_uppaal([cond])
        xml_str = automaton.to_xml()
        assert isinstance(xml_str, str)
        assert len(xml_str) > 0

    def test_automaton_has_locations(self):
        """Automaton must have locations."""
        cond = verifiable(compare("temp", "<", 100), "temp_safe")
        automaton = compile_to_uppaal([cond])
        assert len(automaton.locations) > 0

    def test_automaton_has_transitions(self):
        """Automaton must have transitions."""
        cond = verifiable(compare("temp", "<", 100), "temp_safe")
        automaton = compile_to_uppaal([cond])
        assert len(automaton.transitions) > 0

    def test_automaton_tracks_clocks_for_temporal(self):
        """Automaton includes clocks for temporal conditions."""
        inner = compare("motion", "==", True)
        temporal = within(inner, 5.0, "motion_clk")
        cond = verifiable(temporal, "motion_sustained")
        automaton = compile_to_uppaal([cond])
        assert "motion_clk" in automaton.clocks


class TestUppaalXML:
    """Tests for UPPAAL XML output."""

    def test_xml_is_parseable(self):
        """Generated XML must be parseable."""
        cond = verifiable(compare("sensor", "<", 50), "sensor_ok")
        automaton = compile_to_uppaal([cond])
        xml_str = automaton.to_xml()

        # Should parse without error
        root = ET.fromstring(xml_str)
        assert root is not None
        assert root.tag == "nta"

    def test_xml_has_template(self):
        """UPPAAL XML must have <template> element."""
        cond = verifiable(compare("x", ">", 0), "x_positive")
        automaton = compile_to_uppaal([cond], name="TestTemplate")
        xml_str = automaton.to_xml()
        root = ET.fromstring(xml_str)

        template = root.find("template")
        assert template is not None

        name = template.find("name")
        assert name is not None
        assert name.text == "TestTemplate"

    def test_xml_has_locations(self):
        """UPPAAL XML must have <location> elements."""
        cond = verifiable(compare("val", "<", 100), "val_safe")
        automaton = compile_to_uppaal([cond])
        xml_str = automaton.to_xml()
        root = ET.fromstring(xml_str)

        template = root.find("template")
        locations = template.findall("location")
        assert len(locations) >= 1  # At least 'safe' location

    def test_xml_has_transitions(self):
        """UPPAAL XML must have <transition> elements."""
        cond = verifiable(compare("val", "<", 100), "val_safe")
        automaton = compile_to_uppaal([cond])
        xml_str = automaton.to_xml()
        root = ET.fromstring(xml_str)

        template = root.find("template")
        transitions = template.findall("transition")
        assert len(transitions) >= 1

    def test_xml_has_declaration(self):
        """UPPAAL XML must have <declaration> for variables."""
        cond = verifiable(compare("temp", "<", 100), "temp_safe")
        automaton = compile_to_uppaal([cond])
        xml_str = automaton.to_xml()
        root = ET.fromstring(xml_str)

        declaration = root.find("declaration")
        assert declaration is not None

    def test_save_creates_file(self):
        """save() must create a valid XML file."""
        cond = verifiable(compare("x", ">=", 0), "x_valid")
        automaton = compile_to_uppaal([cond], name="SaveTest")

        with tempfile.NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f:
            filename = f.name

        try:
            automaton.save(filename)
            assert os.path.exists(filename)

            # Verify file content
            with open(filename, "r") as f:
                content = f.read()

            assert "<?xml" in content
            assert "<nta>" in content
            assert "SaveTest" in content
        finally:
            if os.path.exists(filename):
                os.unlink(filename)


class TestMultipleConditions:
    """Tests for exporting multiple conditions."""

    def test_multiple_conditions_create_multiple_locations(self):
        """Multiple conditions create violation locations for each."""
        cond1 = verifiable(compare("a", "<", 10), "a_safe")
        cond2 = verifiable(compare("b", ">", 0), "b_positive")
        cond3 = verifiable(compare("c", "==", True), "c_enabled")

        automaton = compile_to_uppaal([cond1, cond2, cond3])

        # Should have safe + 3 violation locations
        assert len(automaton.locations) == 4

    def test_source_mapping_preserved(self):
        """Source rule names mapped to locations."""
        cond = verifiable(compare("temp", "<", 100), "temperature_safety")
        automaton = compile_to_uppaal([cond])

        # Source mapping should exist
        assert len(automaton.source_mapping) > 0
        assert "temperature_safety" in automaton.source_mapping.values()
