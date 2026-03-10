"""
Snowflake SQL Generation Engine
Converts parsed Informatica workflows to Snowflake SQL based on the detailed specification.
Handles all 6 phases of the translation pipeline.
"""

import re
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from jinja2 import Template
import logging

from ..parsers.InformaticaXMLParser import (
    InformaticaWorkflow, InformaticaSession, InformaticaMapping,
    Transformation, TransformationType, SourceField, TargetField,
    Connector
)

logger = logging.getLogger(__name__)


@dataclass
class SnowflakeSQL:
    session_name: str
    source_table: str
    target_table: str
    staging_statements: List[str]
    cte_statements: List[str]
    final_statement: str
    file_operations: List[Dict[str, str]]


class ExpressionTranslator:
    """Translates Informatica expressions to Snowflake SQL expressions."""

    # Informatica to Snowflake transformation mappings
    EXPRESSION_MAPPINGS = {
        'TO_DATE(': 'TO_TIMESTAMP(',  # When format includes time
        'TO_INTEGER(': 'CAST(',
        'TO_DECIMAL(': 'CAST(',
        'SYSTIMESTAMP()': 'CURRENT_TIMESTAMP()',
        'SESSSTARTTIME': 'CURRENT_TIMESTAMP()',
        'SYSDATE': 'CURRENT_DATE()',
        'IIF(': 'IFF(',
        'ISNULL(': ' IS NULL',
        'NVL(': 'COALESCE(',
        'DECODE(': 'DECODE(',
        'SUBSTR(': 'SUBSTR(',
        'LPAD(': 'LPAD(',
        'RPAD(': 'RPAD(',
        'CONCAT(': 'CONCAT(',
        'ROUND(': 'ROUND(',
        'TRUNC(': 'TRUNC(',
        'ABS(': 'ABS(',
        'UPPER(': 'UPPER(',
        'LOWER(': 'LOWER(',
        'LENGTH(': 'LENGTH(',
        'REPLACECHR(': 'REPLACE(',
        'REPLACESTR(': 'REPLACE(',
        'REG_REPLACE(': 'REGEXP_REPLACE(',
        'INSTR(': 'POSITION(',
        'ADD_TO_DATE(': 'DATEADD(',
        'DATE_DIFF(': 'DATEDIFF(',
        'GET_DATE_PART(': 'DATE_PART(',
    }

    DATA_TYPE_MAPPINGS = {
        'String': 'VARCHAR',
        'Integer': 'INTEGER',
        'Decimal': 'NUMBER',
        'Date/Time': 'TIMESTAMP',
        'Date': 'DATE',
        'Double': 'FLOAT',
        'BigInt': 'BIGINT',
        'Real': 'REAL',
        'Small Integer': 'SMALLINT',
    }

    def translate_expression(self, expr: str) -> str:
        """Translate Informatica expression to Snowflake SQL."""
        if not expr:
            return expr

        translated = expr

        # Apply expression mappings
        for informatica_func, snowflake_func in self.EXPRESSION_MAPPINGS.items():
            translated = translated.replace(informatica_func, snowflake_func)

        # Handle special ISNULL case
        translated = re.sub(r'ISNULL\(([^)]+)\)', r'\1 IS NULL', translated)

        # Handle REPLACECHR special syntax
        translated = re.sub(
            r'REPLACECHR\(\d+,\s*([^,]+),\s*([^,]+),\s*([^)]+)\)',
            r'REPLACE(\1, \2, \3)',
            translated
        )

        # Handle TO_DATE vs TO_TIMESTAMP logic
        # If format contains time indicators, use TO_TIMESTAMP
        time_indicators = ['HH', 'MI', 'SS', 'AM', 'PM']
        if 'TO_DATE(' in translated:
            for indicator in time_indicators:
                if indicator in translated:
                    translated = translated.replace('TO_DATE(', 'TO_TIMESTAMP(', 1)
                    break

        return translated

    def translate_datatype(self, informatica_type: str, precision: int = None, scale: int = None, length: int = None) -> str:
        """Translate Informatica data type to Snowflake data type."""
        base_type = self.DATA_TYPE_MAPPINGS.get(informatica_type, informatica_type)

        if base_type == 'VARCHAR' and length:
            return f'VARCHAR({length})'
        elif base_type == 'NUMBER' and precision is not None:
            if scale is not None:
                return f'NUMBER({precision}, {scale})'
            else:
                return f'NUMBER({precision})'
        else:
            return base_type


class SnowflakeSQLGenerator:
    """Generates Snowflake SQL from parsed Informatica workflows."""

    def __init__(self):
        self.expression_translator = ExpressionTranslator()

    def generate_session_sql(self, workflow: InformaticaWorkflow, session: InformaticaSession) -> SnowflakeSQL:
        """Generate complete Snowflake SQL for a session."""
        try:
            # Build staging table creation
            staging_statements = self._build_staging_table(session)

            # Build file operations (PUT, COPY INTO, REMOVE)
            file_operations = self._build_file_operations(session)

            # Build CTEs from transformations
            cte_statements = self._build_cte_statements(session)

            # Build final target statement (MERGE, INSERT, UPDATE)
            final_statement = self._build_target_statement(session, cte_statements)

            return SnowflakeSQL(
                session_name=session.name,
                source_table=session.sources[0].name if session.sources else "",
                target_table=session.targets[0].name if session.targets else "",
                staging_statements=staging_statements,
                cte_statements=cte_statements,
                final_statement=final_statement,
                file_operations=file_operations
            )

        except Exception as e:
            logger.error(f"Error generating SQL for session {session.name}: {e}")
            raise

    def _build_staging_table(self, session: InformaticaSession) -> List[str]:
        """Build CREATE TABLE statements for staging tables."""
        statements = []

        for source in session.sources:
            if source.type == "Flat File":
                # Create staging table with all fields as VARCHAR
                fields_sql = []
                for field in source.fields:
                    snowflake_type = self.expression_translator.translate_datatype(
                        field.datatype, field.precision, field.scale, field.length
                    )
                    # For staging, use VARCHAR with appropriate length
                    if field.length:
                        staging_type = f"VARCHAR({field.length})"
                    else:
                        staging_type = "VARCHAR(255)"

                    fields_sql.append(f"    {field.name} {staging_type}")

                create_sql = f"""CREATE OR REPLACE TRANSIENT TABLE STAGING.{source.name} (
{','.join(fields_sql)}
);"""
                statements.append(create_sql)

        return statements

    def _build_file_operations(self, session: InformaticaSession) -> List[Dict[str, str]]:
        """Build file operations (PUT, COPY INTO, REMOVE, GET)."""
        operations = []

        # For each source file
        for source in session.sources:
            if source.type == "Flat File":
                # PUT operation
                put_sql = f"""PUT file://<% ctx.env.{session.name}_inputfile %>
    @<% ctx.env.LANDING_STAGE %>/<% ctx.env.{session.name}_InputFileName %>
    OVERWRITE=TRUE
    AUTO_COMPRESS=FALSE;"""

                operations.append({
                    "type": "PUT",
                    "statement": put_sql,
                    "description": f"Upload {session.name} input file to stage"
                })

                # COPY INTO operation
                copy_sql = f"""COPY INTO STAGING.{source.name}
FROM @<% ctx.env.LANDING_STAGE %>/<% ctx.env.{session.name}_InputFileName %>
FILE_FORMAT = STAGING.FF_CSV_SKP_HEADER;"""

                operations.append({
                    "type": "COPY_INTO",
                    "statement": copy_sql,
                    "description": f"Load data into staging table {source.name}"
                })

                # REMOVE operation
                remove_sql = f"""REMOVE @<% ctx.env.LANDING_STAGE %>/<% ctx.env.{session.name}_InputFileName %>;"""

                operations.append({
                    "type": "REMOVE",
                    "statement": remove_sql,
                    "description": f"Clean up staged input file"
                })

        # For flat file targets (output files)
        for target in session.targets:
            if target.type == "Flat File":
                # COPY INTO stage operation
                copy_out_sql = f"""COPY INTO @<% ctx.env.LANDING_STAGE %>/<% ctx.env.{session.name}_OutputFileName %>
FROM (
    {self._get_output_select_statement(session)}
)
FILE_FORMAT = (
    TYPE = CSV
    FIELD_DELIMITER = '\\t'
    SKIP_HEADER = 0
    EMPTY_FIELD_AS_NULL = FALSE
    COMPRESSION = NONE
)
SINGLE = TRUE
OVERWRITE = TRUE;"""

                operations.append({
                    "type": "COPY_INTO",
                    "statement": copy_out_sql,
                    "description": f"Export data to output file"
                })

                # GET operation
                get_sql = f"""GET @<% ctx.env.LANDING_STAGE %>/<% ctx.env.{session.name}_OutputFileName %>
    file://<% ctx.env.{session.name}_OutputFileName_DIR %>
    OVERWRITE = TRUE;"""

                operations.append({
                    "type": "GET",
                    "statement": get_sql,
                    "description": f"Download output file"
                })

                # REMOVE operation
                remove_out_sql = f"""REMOVE @<% ctx.env.LANDING_STAGE %>/<% ctx.env.{session.name}_OutputFileName %>;"""

                operations.append({
                    "type": "REMOVE",
                    "statement": remove_out_sql,
                    "description": f"Clean up output file from stage"
                })

        return operations

    def _build_cte_statements(self, session: InformaticaSession) -> List[str]:
        """Build CTE statements from mapping transformations."""
        if not session.mapping:
            return []

        cte_statements = []

        # Get data flow order
        flow_order = self._get_transformation_flow_order(session.mapping)

        for transform_name in flow_order:
            transformation = next((t for t in session.mapping.transformations if t.name == transform_name), None)
            if not transformation:
                continue

            cte_sql = self._build_transformation_cte(transformation, session.mapping)
            if cte_sql:
                cte_statements.append(cte_sql)

        return cte_statements

    def _build_transformation_cte(self, transformation: Transformation, mapping: InformaticaMapping) -> str:
        """Build CTE for a specific transformation."""
        if transformation.type == TransformationType.SOURCE_QUALIFIER:
            return self._build_source_qualifier_cte(transformation, mapping)
        elif transformation.type == TransformationType.EXPRESSION:
            return self._build_expression_cte(transformation, mapping)
        elif transformation.type == TransformationType.LOOKUP_PROCEDURE:
            return self._build_lookup_cte(transformation, mapping)
        elif transformation.type == TransformationType.FILTER:
            return self._build_filter_cte(transformation, mapping)
        elif transformation.type == TransformationType.UPDATE_STRATEGY:
            return self._build_update_strategy_cte(transformation, mapping)
        elif transformation.type == TransformationType.AGGREGATOR:
            return self._build_aggregator_cte(transformation, mapping)
        else:
            logger.warning(f"Unsupported transformation type: {transformation.type}")
            return f"-- TODO: Implement {transformation.type} transformation"

    def _build_source_qualifier_cte(self, transformation: Transformation, mapping: InformaticaMapping) -> str:
        """Build Source Qualifier CTE."""
        # Get source table name from connectors
        source_table = self._get_source_table_for_transformation(transformation, mapping)

        # Check for custom SQL query
        sql_query = transformation.attributes.get("Sql Query", "")
        if sql_query.strip():
            return f"""{transformation.name} AS (
{sql_query}
)"""

        # Build field list
        output_fields = [port.name for port in transformation.ports if port.port_type in ["OUTPUT", "INPUT/OUTPUT"]]
        fields_sql = ", ".join(output_fields) if output_fields else "*"

        # Check for source filter
        source_filter = transformation.attributes.get("Source Filter", "")
        where_clause = f"WHERE {self.expression_translator.translate_expression(source_filter)}" if source_filter.strip() else ""

        return f"""{transformation.name} AS (
    SELECT {fields_sql}
    FROM STAGING.{source_table}
    {where_clause}
)"""

    def _build_expression_cte(self, transformation: Transformation, mapping: InformaticaMapping) -> str:
        """Build Expression transformation CTE."""
        upstream_cte = self._get_upstream_transformation(transformation, mapping)

        # Build SELECT fields
        select_fields = []

        for port in transformation.ports:
            if port.port_type == "INPUT":
                # Input ports - just pass through (will be handled by connectors)
                continue
            elif port.port_type == "OUTPUT" and port.expression:
                # Output ports with expressions
                translated_expr = self.expression_translator.translate_expression(port.expression)
                select_fields.append(f"    {translated_expr} AS {port.name}")
            elif port.port_type == "INPUT/OUTPUT":
                # Pass-through fields
                # Get the actual field name from connectors
                actual_field = self._get_source_field_for_port(transformation.name, port.name, mapping)
                select_fields.append(f"    {actual_field} AS {port.name}")

        fields_sql = ",\n".join(select_fields) if select_fields else "*"

        return f"""{transformation.name} AS (
    SELECT
{fields_sql}
    FROM {upstream_cte}
)"""

    def _build_lookup_cte(self, transformation: Transformation, mapping: InformaticaMapping) -> str:
        """Build Lookup Procedure CTE and corresponding JOIN logic."""
        # First, build the lookup table CTE
        lookup_table = transformation.attributes.get("Lookup table name", "")
        lookup_sql_override = transformation.attributes.get("Lookup Sql Override", "")
        lookup_condition = transformation.attributes.get("Lookup condition", "")
        lookup_policy = transformation.attributes.get("Lookup Policy on Multiple Match", "Use Any Value")

        # Build lookup CTE
        if lookup_sql_override.strip():
            lookup_base_sql = lookup_sql_override
        else:
            # Build SELECT from lookup table
            lookup_output_ports = [port.name for port in transformation.ports if port.port_type == "LOOKUP/OUTPUT"]
            lookup_fields = ", ".join(lookup_output_ports) if lookup_output_ports else "*"
            lookup_base_sql = f"SELECT {lookup_fields} FROM BASE.{lookup_table}"

        # Apply deduplication based on lookup policy
        if lookup_policy == "Use Any Value":
            lookup_keys = self._extract_lookup_keys_from_condition(lookup_condition)
            if lookup_keys:
                partition_by = ", ".join(lookup_keys)
                lookup_sql = f"""SELECT * FROM (
    {lookup_base_sql}
) QUALIFY ROW_NUMBER() OVER (PARTITION BY {partition_by} ORDER BY 1 DESC) = 1"""
            else:
                lookup_sql = lookup_base_sql
        else:
            lookup_sql = lookup_base_sql

        lookup_cte_name = f"{transformation.name}_LKP"
        lookup_cte = f"""{lookup_cte_name} AS (
{lookup_sql}
)"""

        # Now build the main transformation CTE with LEFT JOIN
        upstream_cte = self._get_upstream_transformation(transformation, mapping)
        join_condition = self._translate_lookup_condition(lookup_condition, upstream_cte, lookup_cte_name)

        # Build SELECT with all fields
        select_fields = []
        for port in transformation.ports:
            if port.port_type in ["INPUT", "INPUT/OUTPUT"]:
                actual_field = self._get_source_field_for_port(transformation.name, port.name, mapping)
                select_fields.append(f"    {upstream_cte}.{actual_field}")
            elif port.port_type == "LOOKUP/OUTPUT":
                select_fields.append(f"    {lookup_cte_name}.{port.name}")

        fields_sql = ",\n".join(select_fields) if select_fields else f"    {upstream_cte}.*, {lookup_cte_name}.*"

        main_cte = f"""{transformation.name} AS (
    SELECT
{fields_sql}
    FROM {upstream_cte}
    LEFT JOIN {lookup_cte_name} ON {join_condition}
)"""

        # Return both CTEs
        return f"{lookup_cte},\n\n{main_cte}"

    def _build_filter_cte(self, transformation: Transformation, mapping: InformaticaMapping) -> str:
        """Build Filter transformation CTE."""
        upstream_cte = self._get_upstream_transformation(transformation, mapping)
        filter_condition = transformation.attributes.get("Filter Condition", "")

        if not filter_condition.strip():
            # No filter condition, just pass through
            return f"""{transformation.name} AS (
    SELECT *
    FROM {upstream_cte}
)"""

        translated_condition = self.expression_translator.translate_expression(filter_condition)

        return f"""{transformation.name} AS (
    SELECT *
    FROM {upstream_cte}
    WHERE {translated_condition}
)"""

    def _build_update_strategy_cte(self, transformation: Transformation, mapping: InformaticaMapping) -> str:
        """Build Update Strategy transformation CTE."""
        upstream_cte = self._get_upstream_transformation(transformation, mapping)
        update_strategy_expr = transformation.attributes.get("Update Strategy Expression", "")

        if not update_strategy_expr.strip():
            # No update strategy, default to INSERT
            update_strategy_sql = "'INSERT'"
        else:
            # Translate the update strategy expression
            # Common patterns: IIF(FLAG='I', DD_INSERT, DD_REJECT)
            translated = update_strategy_expr
            translated = translated.replace("DD_INSERT", "'INSERT'")
            translated = translated.replace("DD_UPDATE", "'UPDATE'")
            translated = translated.replace("DD_DELETE", "'DELETE'")
            translated = translated.replace("DD_REJECT", "'REJECT'")
            translated = self.expression_translator.translate_expression(translated)
            update_strategy_sql = translated

        return f"""{transformation.name} AS (
    SELECT *,
        {update_strategy_sql} AS __UPDATE_STRATEGY
    FROM {upstream_cte}
)"""

    def _build_aggregator_cte(self, transformation: Transformation, mapping: InformaticaMapping) -> str:
        """Build Aggregator transformation CTE."""
        upstream_cte = self._get_upstream_transformation(transformation, mapping)

        # Separate GROUP BY fields from aggregate fields
        group_by_fields = []
        aggregate_fields = []

        for port in transformation.ports:
            if port.port_type in ["INPUT", "INPUT/OUTPUT"] and not self._is_aggregate_expression(port.expression):
                actual_field = self._get_source_field_for_port(transformation.name, port.name, mapping)
                group_by_fields.append(actual_field)
            elif port.port_type == "OUTPUT" and port.expression:
                translated_expr = self.expression_translator.translate_expression(port.expression)
                aggregate_fields.append(f"    {translated_expr} AS {port.name}")

        # Build SELECT clause
        all_fields = group_by_fields + aggregate_fields
        fields_sql = ",\n".join(all_fields)

        # Build GROUP BY clause
        group_by_sql = ", ".join(group_by_fields) if group_by_fields else ""
        group_by_clause = f"GROUP BY {group_by_sql}" if group_by_sql else ""

        return f"""{transformation.name} AS (
    SELECT
{fields_sql}
    FROM {upstream_cte}
    {group_by_clause}
)"""

    def _build_target_statement(self, session: InformaticaSession, cte_statements: List[str]) -> str:
        """Build the final target statement (MERGE, INSERT, UPDATE)."""
        if not session.targets:
            return "-- No targets defined"

        target = session.targets[0]  # Assuming single target for now

        # Check if this is a flat file target
        if target.type == "Flat File":
            return self._build_flat_file_output_statement(session, target, cte_statements)

        # For relational targets
        return self._build_relational_target_statement(session, target, cte_statements)

    def _build_relational_target_statement(self, session: InformaticaSession, target: InformaticaTarget, cte_statements: List[str]) -> str:
        """Build MERGE/INSERT statement for relational target."""
        # Determine operation type
        treat_rows_as = session.treat_source_rows_as
        has_update_strategy = self._session_has_update_strategy(session)
        has_primary_key = any(field.key_type == "PRIMARY KEY" for field in target.fields)

        final_cte = self._get_final_cte_name(cte_statements)
        target_columns = [field.name for field in target.fields]

        # Build WITH clause
        with_clause = "WITH\n" + ",\n".join(cte_statements) if cte_statements else ""

        if treat_rows_as == "Data driven" and has_update_strategy:
            # Use MERGE for data-driven operations
            return self._build_merge_statement(target, with_clause, final_cte, target_columns)
        elif has_primary_key and treat_rows_as == "Insert":
            # Convert INSERT to MERGE when primary key exists
            return self._build_merge_statement(target, with_clause, final_cte, target_columns)
        elif treat_rows_as == "Insert":
            # Simple INSERT
            return self._build_insert_statement(target, with_clause, final_cte, target_columns)
        elif treat_rows_as == "Update":
            # UPDATE statement
            return self._build_update_statement(target, with_clause, final_cte, target_columns)
        else:
            # Default to INSERT
            return self._build_insert_statement(target, with_clause, final_cte, target_columns)

    def _build_merge_statement(self, target: InformaticaTarget, with_clause: str, final_cte: str, target_columns: List[str]) -> str:
        """Build MERGE statement."""
        # Build ON clause using primary and foreign keys
        key_fields = [field.name for field in target.fields if field.key_type in ["PRIMARY KEY", "FOREIGN KEY"]]
        if not key_fields:
            # Fallback to first field if no keys defined
            key_fields = [target_columns[0]] if target_columns else ["id"]

        on_conditions = [f"TGT.{field} = SRC.{field}" for field in key_fields]
        on_clause = " AND ".join(on_conditions)

        # Build column lists
        columns_list = ", ".join(target_columns)
        src_columns_list = ", ".join([f"SRC.{col}" for col in target_columns])
        update_assignments = [f"TGT.{col} = SRC.{col}" for col in target_columns]
        update_clause = ", ".join(update_assignments)

        return f"""MERGE INTO BASE.{target.name} AS TGT
USING (
{with_clause}
SELECT {columns_list} FROM {final_cte}
) AS SRC

ON {on_clause}

WHEN NOT MATCHED AND SRC.__UPDATE_STRATEGY = 'INSERT' THEN
    INSERT ({columns_list})
    VALUES ({src_columns_list})

WHEN MATCHED AND SRC.__UPDATE_STRATEGY = 'UPDATE' THEN
    UPDATE SET {update_clause}

WHEN MATCHED AND SRC.__UPDATE_STRATEGY = 'DELETE' THEN
    DELETE;"""

    def _build_insert_statement(self, target: InformaticaTarget, with_clause: str, final_cte: str, target_columns: List[str]) -> str:
        """Build INSERT statement."""
        columns_list = ", ".join(target_columns)

        return f"""INSERT INTO BASE.{target.name} ({columns_list})
{with_clause}
SELECT {columns_list} FROM {final_cte};"""

    def _build_update_statement(self, target: InformaticaTarget, with_clause: str, final_cte: str, target_columns: List[str]) -> str:
        """Build UPDATE statement."""
        # This is a simplified UPDATE - in practice would need WHERE clause logic
        update_assignments = [f"{col} = SRC.{col}" for col in target_columns]
        update_clause = ", ".join(update_assignments)

        return f"""UPDATE BASE.{target.name}
SET {update_clause}
FROM (
{with_clause}
SELECT * FROM {final_cte}
) SRC
WHERE BASE.{target.name}.id = SRC.id; -- TODO: Define proper join condition"""

    def _build_flat_file_output_statement(self, session: InformaticaSession, target: InformaticaTarget, cte_statements: List[str]) -> str:
        """Build COPY INTO statement for flat file output."""
        final_cte = self._get_final_cte_name(cte_statements)
        with_clause = "WITH\n" + ",\n".join(cte_statements) if cte_statements else ""

        target_columns = [field.name for field in target.fields]
        columns_list = ", ".join(target_columns)

        return f"""COPY INTO @<% ctx.env.LANDING_STAGE %>/<% ctx.env.{session.name}_OutputFileName %>
FROM (
{with_clause}
SELECT {columns_list} FROM {final_cte}
)
FILE_FORMAT = (
    TYPE = CSV
    FIELD_DELIMITER = '\\t'
    SKIP_HEADER = 0
    EMPTY_FIELD_AS_NULL = FALSE
    COMPRESSION = NONE
)
SINGLE = TRUE
OVERWRITE = TRUE;

-- Download the output file from stage to local filesystem
GET @<% ctx.env.LANDING_STAGE %>/<% ctx.env.{session.name}_OutputFileName %>
    file://<% ctx.env.{session.name}_OutputFileName_DIR %>
    OVERWRITE = TRUE;

-- Clean up the staged output file
REMOVE @<% ctx.env.LANDING_STAGE %>/<% ctx.env.{session.name}_OutputFileName %>;"""

    # Helper methods
    def _get_transformation_flow_order(self, mapping: InformaticaMapping) -> List[str]:
        """Get transformation names in execution order."""
        # Simplified topological sort based on connectors
        # This should be enhanced with proper graph traversal
        transform_names = [t.name for t in mapping.transformations]

        # For now, return in the order they appear
        # In production, implement proper topological sorting
        return transform_names

    def _get_upstream_transformation(self, transformation: Transformation, mapping: InformaticaMapping) -> str:
        """Get the upstream transformation name for this transformation."""
        # Find connectors that feed into this transformation
        for connector in mapping.connectors:
            if connector.to_instance == transformation.name:
                return connector.from_instance

        # If no connector found, assume it's the first in the chain
        return "source_data"

    def _get_source_table_for_transformation(self, transformation: Transformation, mapping: InformaticaMapping) -> str:
        """Get source table name for a Source Qualifier transformation."""
        # This would need to be determined from the XML structure
        # For now, return a placeholder
        return "source_table"

    def _get_source_field_for_port(self, transform_name: str, port_name: str, mapping: InformaticaMapping) -> str:
        """Get the actual source field name for a port through connectors."""
        for connector in mapping.connectors:
            if connector.to_instance == transform_name and connector.to_field == port_name:
                return connector.from_field
        return port_name  # Default to port name

    def _extract_lookup_keys_from_condition(self, condition: str) -> List[str]:
        """Extract lookup key fields from lookup condition."""
        # Parse condition like "field1 = field1 AND field2 = field2"
        # This is simplified - production version would need proper parsing
        keys = []
        if '=' in condition:
            parts = condition.split(' AND ')
            for part in parts:
                if '=' in part:
                    left_side = part.split('=')[0].strip()
                    keys.append(left_side)
        return keys

    def _translate_lookup_condition(self, condition: str, upstream_cte: str, lookup_cte: str) -> str:
        """Translate lookup condition to JOIN condition."""
        # Simple translation - production would need proper parsing
        translated = condition
        translated = translated.replace(' = ', f' = {lookup_cte}.')
        return f"{upstream_cte}.{translated}"

    def _session_has_update_strategy(self, session: InformaticaSession) -> bool:
        """Check if session has Update Strategy transformation."""
        if not session.mapping:
            return False
        return any(t.type == TransformationType.UPDATE_STRATEGY for t in session.mapping.transformations)

    def _is_aggregate_expression(self, expression: str) -> bool:
        """Check if expression contains aggregate functions."""
        if not expression:
            return False
        aggregates = ['SUM(', 'COUNT(', 'MAX(', 'MIN(', 'AVG(']
        return any(agg in expression.upper() for agg in aggregates)

    def _get_final_cte_name(self, cte_statements: List[str]) -> str:
        """Get the name of the final CTE in the chain."""
        if not cte_statements:
            return "source_data"

        # Extract CTE name from the last statement
        last_cte = cte_statements[-1]
        if ' AS (' in last_cte:
            return last_cte.split(' AS (')[0].strip()
        return "final_data"

    def _get_output_select_statement(self, session: InformaticaSession) -> str:
        """Get SELECT statement for output file generation."""
        # This would build the complete WITH...SELECT statement for output
        # For now, return placeholder
        return "SELECT * FROM final_transformation"

    def generate_complete_sql_file(self, workflow: InformaticaWorkflow, session: InformaticaSession) -> str:
        """Generate the complete .snowsql file content."""
        snowflake_sql = self.generate_session_sql(workflow, session)

        # Build complete SQL file
        sql_parts = []

        # Header comment
        sql_parts.append(f"""-- Generated Snowflake SQL for {session.name}
-- Source mapping: {session.mapping_name}
-- Generated on: {self._get_current_timestamp()}
--
-- Session: {session.name}
-- Mapping: {session.mapping_name}
-- Source(s): {', '.join([s.name for s in session.sources])}
-- Target(s): {', '.join([t.name for t in session.targets])}
-- Treat source rows as: {session.treat_source_rows_as}
--""")

        # Staging table creation
        sql_parts.extend(snowflake_sql.staging_statements)
        sql_parts.append("")

        # File operations
        for operation in snowflake_sql.file_operations:
            sql_parts.append(f"-- {operation['description']}")
            sql_parts.append(operation['statement'])
            sql_parts.append("")

        # Final transformation and target statement
        sql_parts.append("-- Main transformation and target loading")
        sql_parts.append(snowflake_sql.final_statement)

        return "\n".join(sql_parts)

    def _get_current_timestamp(self) -> str:
        """Get current timestamp for file headers."""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# Example usage
if __name__ == "__main__":
    # This would be called with actual parsed workflow data
    generator = SnowflakeSQLGenerator()

    # Test with sample data
    from ..parsers.InformaticaXMLParser import create_sample_workflow

    workflow = create_sample_workflow()
    if workflow.sessions:
        sql = generator.generate_complete_sql_file(workflow, workflow.sessions[0])
        print("Generated SQL:")
        print(sql)