"""
Informatica XML Parser Foundation
Parses Informatica XML files and extracts workflow, session, mapping, and transformation data.
Based on the detailed specification document requirements.
"""

import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Any, Tuple
import re
import logging
from dataclasses import dataclass, field
from enum import Enum

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TransformationType(Enum):
    SOURCE_QUALIFIER = "Source Qualifier"
    EXPRESSION = "Expression"
    LOOKUP_PROCEDURE = "Lookup Procedure"
    FILTER = "Filter"
    UPDATE_STRATEGY = "Update Strategy"
    AGGREGATOR = "Aggregator"
    JOINER = "Joiner"
    SORTER = "Sorter"
    SEQUENCE_GENERATOR = "Sequence Generator"
    ROUTER = "Router"


@dataclass
class SourceField:
    name: str
    datatype: str
    precision: Optional[int] = None
    scale: Optional[int] = None
    length: Optional[int] = None
    nullable: bool = True


@dataclass
class TargetField:
    name: str
    datatype: str
    precision: Optional[int] = None
    scale: Optional[int] = None
    length: Optional[int] = None
    nullable: bool = True
    key_type: Optional[str] = None  # PRIMARY KEY, FOREIGN KEY


@dataclass
class TransformationPort:
    name: str
    port_type: str  # INPUT, OUTPUT, INPUT/OUTPUT, LOOKUP/OUTPUT
    datatype: str
    precision: Optional[int] = None
    scale: Optional[int] = None
    expression: Optional[str] = None


@dataclass
class Transformation:
    name: str
    type: TransformationType
    ports: List[TransformationPort] = field(default_factory=list)
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Connector:
    from_instance: str
    from_field: str
    to_instance: str
    to_field: str


@dataclass
class InformaticaSource:
    name: str
    type: str  # Flat File, Relational
    fields: List[SourceField] = field(default_factory=list)
    filename: Optional[str] = None
    connection: Optional[str] = None


@dataclass
class InformaticaTarget:
    name: str
    type: str  # Flat File, Relational
    fields: List[TargetField] = field(default_factory=list)
    connection: Optional[str] = None
    load_type: Optional[str] = None  # Bulk, Normal


@dataclass
class InformaticaMapping:
    name: str
    transformations: List[Transformation] = field(default_factory=list)
    connectors: List[Connector] = field(default_factory=list)


@dataclass
class SessionExtensions:
    file_reader: Optional[Dict[str, Any]] = None
    relational_writer: Optional[Dict[str, Any]] = None
    relational_lookup: Optional[Dict[str, Any]] = None
    post_session_command: Optional[str] = None


@dataclass
class InformaticaSession:
    name: str
    mapping_name: str
    treat_source_rows_as: str = "Insert"  # Insert, Update, Delete, Data driven
    sources: List[InformaticaSource] = field(default_factory=list)
    targets: List[InformaticaTarget] = field(default_factory=list)
    mapping: Optional[InformaticaMapping] = None
    extensions: Optional[SessionExtensions] = None


@dataclass
class LinkCondition:
    from_task: str
    to_task: str
    condition: str  # SUCCESS, FAILURE, UNCONDITIONAL


@dataclass
class InformaticaWorkflow:
    name: str
    folder: str
    scheduler_type: str = "On Demand"
    parameter_filename: Optional[str] = None
    sessions: List[InformaticaSession] = field(default_factory=list)
    link_conditions: List[LinkCondition] = field(default_factory=list)


class InformaticaXMLParser:
    """
    Comprehensive Informatica XML Parser that handles all workflow components
    according to the detailed specification document.
    """

    def __init__(self):
        self.xml_root: Optional[ET.Element] = None
        self.namespace_map: Dict[str, str] = {}

    def parse_xml_file(self, xml_content: str) -> InformaticaWorkflow:
        """
        Parse Informatica XML content and return structured workflow data.

        Args:
            xml_content: Raw XML content as string

        Returns:
            InformaticaWorkflow object with all parsed data
        """
        try:
            # Parse XML
            self.xml_root = ET.fromstring(xml_content)
            self._extract_namespaces()

            # Parse workflow
            workflow = self._parse_workflow()

            # Parse sessions
            sessions = self._parse_sessions()
            workflow.sessions = sessions

            # For each session, parse its mapping
            for session in sessions:
                session.mapping = self._parse_mapping(session.mapping_name)
                session.sources = self._parse_sources_for_session(session.name)
                session.targets = self._parse_targets_for_session(session.name)
                session.extensions = self._parse_session_extensions(session.name)

            # Parse link conditions
            workflow.link_conditions = self._parse_link_conditions()

            logger.info(f"Successfully parsed workflow: {workflow.name}")
            return workflow

        except ET.ParseError as e:
            logger.error(f"XML parsing error: {e}")
            raise ValueError(f"Invalid XML format: {e}")
        except Exception as e:
            logger.error(f"Unexpected error during parsing: {e}")
            raise ValueError(f"Failed to parse XML: {e}")

    def _extract_namespaces(self):
        """Extract XML namespaces for proper element lookup."""
        for event, elem in ET.iterparse(ET.StringIO(ET.tostring(self.xml_root, encoding='unicode')), events=['start-ns']):
            if event == 'start-ns':
                prefix, uri = elem
                self.namespace_map[prefix or 'default'] = uri

    def _parse_workflow(self) -> InformaticaWorkflow:
        """Parse workflow-level information."""
        workflow_elem = self.xml_root.find('.//WORKFLOW')
        if workflow_elem is None:
            raise ValueError("No WORKFLOW element found in XML")

        name = workflow_elem.get('NAME', '')
        folder = workflow_elem.get('FOLDERNAME', '')

        # Extract parameter filename
        param_filename = None
        param_attr = workflow_elem.find('.//ATTRIBUTE[@NAME="Parameter Filename"]')
        if param_attr is not None:
            param_filename = param_attr.get('VALUE', '')

        # Determine scheduler type
        scheduler_type = "On Demand"  # Default
        scheduler_attr = workflow_elem.find('.//ATTRIBUTE[@NAME="Scheduler type"]')
        if scheduler_attr is not None:
            scheduler_type = scheduler_attr.get('VALUE', 'On Demand')

        return InformaticaWorkflow(
            name=name,
            folder=folder,
            scheduler_type=scheduler_type,
            parameter_filename=param_filename
        )

    def _parse_sessions(self) -> List[InformaticaSession]:
        """Parse all sessions in the workflow."""
        sessions = []
        session_elements = self.xml_root.findall('.//SESSION')

        for session_elem in session_elements:
            name = session_elem.get('NAME', '')
            mapping_name = session_elem.get('MAPPINGNAME', '')

            # Get "Treat source rows as" setting
            treat_rows_as = "Insert"  # Default
            treat_attr = session_elem.find('.//ATTRIBUTE[@NAME="Treat source rows as"]')
            if treat_attr is not None:
                treat_rows_as = treat_attr.get('VALUE', 'Insert')

            session = InformaticaSession(
                name=name,
                mapping_name=mapping_name,
                treat_source_rows_as=treat_rows_as
            )
            sessions.append(session)

        return sessions

    def _parse_mapping(self, mapping_name: str) -> Optional[InformaticaMapping]:
        """Parse mapping by name."""
        mapping_elem = self.xml_root.find(f'.//MAPPING[@NAME="{mapping_name}"]')
        if mapping_elem is None:
            logger.warning(f"Mapping {mapping_name} not found")
            return None

        transformations = self._parse_transformations(mapping_elem)
        connectors = self._parse_connectors(mapping_elem)

        return InformaticaMapping(
            name=mapping_name,
            transformations=transformations,
            connectors=connectors
        )

    def _parse_transformations(self, mapping_elem: ET.Element) -> List[Transformation]:
        """Parse all transformations in a mapping."""
        transformations = []
        transform_elements = mapping_elem.findall('.//TRANSFORMATION')

        for transform_elem in transform_elements:
            name = transform_elem.get('NAME', '')
            type_str = transform_elem.get('TYPE', '')

            # Convert type string to enum
            try:
                transform_type = TransformationType(type_str)
            except ValueError:
                logger.warning(f"Unknown transformation type: {type_str}")
                continue

            # Parse ports
            ports = self._parse_transformation_ports(transform_elem)

            # Parse attributes (expressions, conditions, etc.)
            attributes = self._parse_transformation_attributes(transform_elem)

            transformation = Transformation(
                name=name,
                type=transform_type,
                ports=ports,
                attributes=attributes
            )
            transformations.append(transformation)

        return transformations

    def _parse_transformation_ports(self, transform_elem: ET.Element) -> List[TransformationPort]:
        """Parse ports for a transformation."""
        ports = []
        port_elements = transform_elem.findall('.//TRANSFORMFIELD')

        for port_elem in port_elements:
            name = port_elem.get('NAME', '')
            port_type = port_elem.get('PORTTYPE', '')
            datatype = port_elem.get('DATATYPE', '')
            precision = self._safe_int(port_elem.get('PRECISION'))
            scale = self._safe_int(port_elem.get('SCALE'))

            # Get expression if it exists
            expression = None
            expr_elem = port_elem.find('.//EXPRESSION')
            if expr_elem is not None:
                expression = expr_elem.text

            port = TransformationPort(
                name=name,
                port_type=port_type,
                datatype=datatype,
                precision=precision,
                scale=scale,
                expression=expression
            )
            ports.append(port)

        return ports

    def _parse_transformation_attributes(self, transform_elem: ET.Element) -> Dict[str, Any]:
        """Parse transformation-specific attributes."""
        attributes = {}

        # Parse TABLEATTRIBUTE elements (contains SQL queries, conditions, etc.)
        table_attrs = transform_elem.findall('.//TABLEATTRIBUTE')
        for attr_elem in table_attrs:
            name = attr_elem.get('NAME', '')
            value = attr_elem.get('VALUE', '')

            # Decode XML entities
            value = self._decode_xml_entities(value)

            attributes[name] = value

        # Parse regular ATTRIBUTE elements
        attr_elements = transform_elem.findall('.//ATTRIBUTE')
        for attr_elem in attr_elements:
            name = attr_elem.get('NAME', '')
            value = attr_elem.get('VALUE', '')
            attributes[name] = value

        return attributes

    def _parse_connectors(self, mapping_elem: ET.Element) -> List[Connector]:
        """Parse data flow connectors between transformations."""
        connectors = []
        connector_elements = mapping_elem.findall('.//CONNECTOR')

        for conn_elem in connector_elements:
            from_instance = conn_elem.get('FROMINSTANCE', '')
            from_field = conn_elem.get('FROMFIELD', '')
            to_instance = conn_elem.get('TOINSTANCE', '')
            to_field = conn_elem.get('TOFIELD', '')

            connector = Connector(
                from_instance=from_instance,
                from_field=from_field,
                to_instance=to_instance,
                to_field=to_field
            )
            connectors.append(connector)

        return connectors

    def _parse_sources_for_session(self, session_name: str) -> List[InformaticaSource]:
        """Parse sources for a specific session."""
        sources = []
        source_elements = self.xml_root.findall('.//SOURCE')

        for source_elem in source_elements:
            name = source_elem.get('NAME', '')
            db_type = source_elem.get('DATABASETYPE', '')

            # Parse source fields
            fields = []
            field_elements = source_elem.findall('.//SOURCEFIELD')
            for field_elem in field_elements:
                field_name = field_elem.get('NAME', '')
                datatype = field_elem.get('DATATYPE', '')
                precision = self._safe_int(field_elem.get('PRECISION'))
                scale = self._safe_int(field_elem.get('SCALE'))
                length = self._safe_int(field_elem.get('LENGTH'))

                field = SourceField(
                    name=field_name,
                    datatype=datatype,
                    precision=precision,
                    scale=scale,
                    length=length
                )
                fields.append(field)

            source = InformaticaSource(
                name=name,
                type=db_type,
                fields=fields
            )
            sources.append(source)

        return sources

    def _parse_targets_for_session(self, session_name: str) -> List[InformaticaTarget]:
        """Parse targets for a specific session."""
        targets = []
        target_elements = self.xml_root.findall('.//TARGET')

        for target_elem in target_elements:
            name = target_elem.get('NAME', '')
            db_type = target_elem.get('DATABASETYPE', '')

            # Parse target fields
            fields = []
            field_elements = target_elem.findall('.//TARGETFIELD')
            for field_elem in field_elements:
                field_name = field_elem.get('NAME', '')
                datatype = field_elem.get('DATATYPE', '')
                precision = self._safe_int(field_elem.get('PRECISION'))
                scale = self._safe_int(field_elem.get('SCALE'))
                length = self._safe_int(field_elem.get('LENGTH'))
                key_type = field_elem.get('KEYTYPE')

                field = TargetField(
                    name=field_name,
                    datatype=datatype,
                    precision=precision,
                    scale=scale,
                    length=length,
                    key_type=key_type
                )
                fields.append(field)

            target = InformaticaTarget(
                name=name,
                type=db_type,
                fields=fields
            )
            targets.append(target)

        return targets

    def _parse_session_extensions(self, session_name: str) -> Optional[SessionExtensions]:
        """Parse session extensions (file readers, writers, lookups, etc.)."""
        session_elem = self.xml_root.find(f'.//SESSION[@NAME="{session_name}"]')
        if session_elem is None:
            return None

        extensions = SessionExtensions()

        # Parse session attributes for extensions
        session_attrs = session_elem.findall('.//ATTRIBUTE')
        for attr in session_attrs:
            name = attr.get('NAME', '')
            value = attr.get('VALUE', '')

            # Categorize attributes
            if 'file' in name.lower() and 'reader' in name.lower():
                if extensions.file_reader is None:
                    extensions.file_reader = {}
                extensions.file_reader[name] = value
            elif 'writer' in name.lower():
                if extensions.relational_writer is None:
                    extensions.relational_writer = {}
                extensions.relational_writer[name] = value
            elif 'lookup' in name.lower():
                if extensions.relational_lookup is None:
                    extensions.relational_lookup = {}
                extensions.relational_lookup[name] = value
            elif 'post' in name.lower() and 'command' in name.lower():
                extensions.post_session_command = value

        return extensions

    def _parse_link_conditions(self) -> List[LinkCondition]:
        """Parse workflow link conditions between tasks."""
        link_conditions = []

        # Look for workflow task links
        task_links = self.xml_root.findall('.//TASKLINK')
        for link_elem in task_links:
            from_task = link_elem.get('FROMTASK', '')
            to_task = link_elem.get('TOTASK', '')

            # Default to SUCCESS condition
            condition = "SUCCESS"
            cond_attr = link_elem.find('.//ATTRIBUTE[@NAME="Link Condition"]')
            if cond_attr is not None:
                condition = cond_attr.get('VALUE', 'SUCCESS')

            link_condition = LinkCondition(
                from_task=from_task,
                to_task=to_task,
                condition=condition
            )
            link_conditions.append(link_condition)

        return link_conditions

    def _decode_xml_entities(self, text: str) -> str:
        """Decode XML entities like &apos;, &#xD;&#xA;, etc."""
        if not text:
            return text

        # Common XML entity mappings
        entity_map = {
            '&apos;': "'",
            '&quot;': '"',
            '&lt;': '<',
            '&gt;': '>',
            '&amp;': '&',
            '&#xD;&#xA;': '\n',
            '&#xD;': '\r',
            '&#xA;': '\n',
        }

        for entity, replacement in entity_map.items():
            text = text.replace(entity, replacement)

        # Handle numeric character references
        text = re.sub(r'&#(\d+);', lambda m: chr(int(m.group(1))), text)
        text = re.sub(r'&#x([0-9A-Fa-f]+);', lambda m: chr(int(m.group(1), 16)), text)

        return text

    def _safe_int(self, value: Optional[str]) -> Optional[int]:
        """Safely convert string to int, return None if conversion fails."""
        if value is None or value == '':
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None

    def get_data_flow_order(self, mapping: InformaticaMapping) -> List[str]:
        """
        Determine the order of transformations in the data flow.
        Returns transformation names in execution order.
        """
        if not mapping or not mapping.connectors:
            return []

        # Build adjacency graph
        graph = {}
        in_degree = {}

        # Initialize graph
        for transformation in mapping.transformations:
            graph[transformation.name] = []
            in_degree[transformation.name] = 0

        # Build edges from connectors
        for connector in mapping.connectors:
            if connector.from_instance in graph and connector.to_instance in graph:
                graph[connector.from_instance].append(connector.to_instance)
                in_degree[connector.to_instance] += 1

        # Topological sort
        queue = [node for node, degree in in_degree.items() if degree == 0]
        result = []

        while queue:
            node = queue.pop(0)
            result.append(node)

            for neighbor in graph[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        return result


def create_sample_workflow() -> InformaticaWorkflow:
    """Create a sample workflow for testing."""
    return InformaticaWorkflow(
        name="Wf_vw1708_JBA_Outbound_file_details",
        folder="Wave3/Drishal/vw_JBA_Feeds",
        parameter_filename="/vw/param/JBA/UVW1708.param",
        sessions=[
            InformaticaSession(
                name="S_vw1708_JBA_Outbound_file_details",
                mapping_name="m_vw1708_JBA_Outbound_file_details",
                treat_source_rows_as="Data driven"
            )
        ]
    )


# Example usage and testing
if __name__ == "__main__":
    parser = InformaticaXMLParser()

    # This would normally be called with actual XML content
    sample_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <POWERMART>
        <REPOSITORY>
            <FOLDER NAME="Wave3/Drishal/vw_JBA_Feeds">
                <WORKFLOW NAME="Wf_vw1708_JBA_Outbound_file_details">
                    <ATTRIBUTE NAME="Parameter Filename" VALUE="/vw/param/JBA/UVW1708.param"/>
                    <SESSION NAME="S_vw1708_JBA_Outbound_file_details" MAPPINGNAME="m_vw1708_JBA_Outbound_file_details">
                        <ATTRIBUTE NAME="Treat source rows as" VALUE="Data driven"/>
                    </SESSION>
                </WORKFLOW>
            </FOLDER>
        </REPOSITORY>
    </POWERMART>"""

    try:
        workflow = parser.parse_xml_file(sample_xml)
        print(f"Parsed workflow: {workflow.name}")
        print(f"Sessions: {[s.name for s in workflow.sessions]}")
    except Exception as e:
        print(f"Parser test failed: {e}")