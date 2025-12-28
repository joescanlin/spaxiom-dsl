"""
UPPAAL timed automaton export for verifiable conditions.

Exports verifiable conditions to UPPAAL XML format for formal verification.
This is export-only; we don't parse or validate against UPPAAL.

Reference: Paper Section 7.3 "Formal semantics and denotational interpretation"
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Dict, List, Optional, TYPE_CHECKING
from xml.dom import minidom

if TYPE_CHECKING:
    from spaxiom.safety.ir import VerifiableCondition


@dataclass
class UppaalLocation:
    """A location (state) in the UPPAAL automaton."""

    id: str
    name: str
    x: int = 0
    y: int = 0
    initial: bool = False
    committed: bool = False
    invariant: str = ""


@dataclass
class UppaalTransition:
    """A transition (edge) in the UPPAAL automaton."""

    source: str
    target: str
    guard: str = ""
    sync: str = ""
    update: str = ""


@dataclass
class UppaalAutomaton:
    """Represents an UPPAAL timed automaton.

    This is a simplified representation focused on export.
    """

    name: str
    locations: List[UppaalLocation] = field(default_factory=list)
    transitions: List[UppaalTransition] = field(default_factory=list)
    clocks: List[str] = field(default_factory=list)
    variables: List[tuple] = field(default_factory=list)  # (name, type, init)
    source_mapping: Dict[str, str] = field(
        default_factory=dict
    )  # id -> source rule name

    def to_xml(self) -> str:
        """Convert automaton to UPPAAL XML string.

        Returns:
            XML string in UPPAAL format
        """
        # Root element
        nta = ET.Element("nta")

        # Global declarations (clocks and variables)
        declaration = ET.SubElement(nta, "declaration")
        decl_lines = []

        # Add clocks
        if self.clocks:
            decl_lines.append(f"clock {', '.join(self.clocks)};")

        # Add variables
        for var_name, var_type, var_init in self.variables:
            decl_lines.append(f"{var_type} {var_name} = {var_init};")

        declaration.text = "\n".join(decl_lines)

        # Template (the automaton)
        template = ET.SubElement(nta, "template")
        name_elem = ET.SubElement(template, "name")
        name_elem.text = self.name

        # Local declarations (none for now)
        local_decl = ET.SubElement(template, "declaration")
        local_decl.text = ""

        # Locations
        for loc in self.locations:
            loc_elem = ET.SubElement(template, "location")
            loc_elem.set("id", loc.id)
            loc_elem.set("x", str(loc.x))
            loc_elem.set("y", str(loc.y))

            name_elem = ET.SubElement(loc_elem, "name")
            name_elem.set("x", str(loc.x - 10))
            name_elem.set("y", str(loc.y - 30))
            name_elem.text = loc.name

            if loc.invariant:
                label = ET.SubElement(loc_elem, "label")
                label.set("kind", "invariant")
                label.text = loc.invariant

            if loc.committed:
                ET.SubElement(loc_elem, "committed")

        # Initial location
        for loc in self.locations:
            if loc.initial:
                init_elem = ET.SubElement(template, "init")
                init_elem.set("ref", loc.id)
                break

        # Transitions
        for trans in self.transitions:
            trans_elem = ET.SubElement(template, "transition")

            source = ET.SubElement(trans_elem, "source")
            source.set("ref", trans.source)

            target = ET.SubElement(trans_elem, "target")
            target.set("ref", trans.target)

            if trans.guard:
                guard = ET.SubElement(trans_elem, "label")
                guard.set("kind", "guard")
                guard.text = trans.guard

            if trans.sync:
                sync = ET.SubElement(trans_elem, "label")
                sync.set("kind", "synchronisation")
                sync.text = trans.sync

            if trans.update:
                update = ET.SubElement(trans_elem, "label")
                update.set("kind", "assignment")
                update.text = trans.update

        # System declaration
        system = ET.SubElement(nta, "system")
        system.text = f"system {self.name};"

        # Convert to string with pretty printing
        rough_string = ET.tostring(nta, encoding="unicode")
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ")

    def save(self, filename: str) -> None:
        """Save automaton to UPPAAL XML file.

        Args:
            filename: Path to output file
        """
        xml_content = self.to_xml()

        # Add XML header if not present
        if not xml_content.startswith("<?xml"):
            xml_content = '<?xml version="1.0" encoding="utf-8"?>\n' + xml_content

        # Add UPPAAL DOCTYPE
        lines = xml_content.split("\n")
        if len(lines) > 1:
            lines.insert(
                1,
                '<!DOCTYPE nta PUBLIC "-//Uppaal Team//DTD Flat System 1.1//EN" "http://www.it.uu.se/research/group/darts/uppaal/flat-1_1.dtd">',
            )
            xml_content = "\n".join(lines)

        with open(filename, "w") as f:
            f.write(xml_content)


def compile_to_uppaal(
    conditions: List["VerifiableCondition"],
    name: str = "SpaxiomMonitor",
    zones: Optional[List[str]] = None,
) -> UppaalAutomaton:
    """Compile verifiable conditions to a UPPAAL timed automaton.

    Creates a monitor automaton that tracks the state of all conditions
    and can detect violations.

    Args:
        conditions: List of verifiable conditions to monitor
        name: Name for the automaton
        zones: Optional list of zone names (for metadata)

    Returns:
        UppaalAutomaton instance ready for export
    """

    automaton = UppaalAutomaton(name=name)

    # Collect all clocks from conditions
    all_clocks = set()
    for cond in conditions:
        all_clocks.update(cond.get_clocks())
    automaton.clocks = list(all_clocks)

    # Collect all signals as boolean variables
    all_signals = set()
    for cond in conditions:
        all_signals.update(cond.get_signals())

    for sig in sorted(all_signals):
        automaton.variables.append((sig, "bool", "false"))

    # Create a simple monitor structure:
    # - Initial "safe" location
    # - One location per condition for "violated" state
    # - Transitions when condition becomes false

    # Initial safe location
    safe_loc = UppaalLocation(
        id="id0",
        name="safe",
        x=0,
        y=0,
        initial=True,
    )
    automaton.locations.append(safe_loc)

    # Create violation locations and transitions for each condition
    for i, cond in enumerate(conditions):
        loc_id = f"id{i + 1}"
        cond_name = cond.name if hasattr(cond, "name") else f"cond_{i}"

        # Violation location
        violation_loc = UppaalLocation(
            id=loc_id,
            name=f"violated_{cond_name}",
            x=200,
            y=i * 100,
        )
        automaton.locations.append(violation_loc)

        # Map source rule
        automaton.source_mapping[loc_id] = cond_name

        # Transition from safe to violated when condition is NOT true
        # (safety property violation = condition becomes false)
        guard = f"!({cond.to_uppaal_guard()})"
        trans = UppaalTransition(
            source="id0",
            target=loc_id,
            guard=guard,
        )
        automaton.transitions.append(trans)

        # Self-loop to stay in safe state when condition is true
        stay_guard = cond.to_uppaal_guard()
        stay_trans = UppaalTransition(
            source="id0",
            target="id0",
            guard=stay_guard,
        )
        automaton.transitions.append(stay_trans)

    return automaton
