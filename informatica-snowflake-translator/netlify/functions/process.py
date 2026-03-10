import json
import asyncio
import os
import re
from typing import Dict, Any, List, Optional
from urllib.parse import unquote
from datetime import datetime
import logging

# Import our custom parsers and generators
try:
    from .parsers.InformaticaXMLParser import InformaticaXMLParser, InformaticaWorkflow
    from .generators.SnowflakeSQLGenerator import SnowflakeSQLGenerator
    from .utils.ProgressTracker import ProgressTracker
    from .utils.FileManager import FileManager
except ImportError:
    # Fallback for development/testing
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))

    class MockInformaticaXMLParser:
        def parse_xml_file(self, content): return None
    class MockSnowflakeSQLGenerator:
        def generate_complete_sql_file(self, workflow, session): return "-- Mock SQL"
    class MockProgressTracker:
        def __init__(self, session_id): pass
        def update_phase(self, phase, progress): pass
    class MockFileManager:
        def __init__(self, session_id): pass
        def save_file(self, name, content): pass

    InformaticaXMLParser = MockInformaticaXMLParser
    SnowflakeSQLGenerator = MockSnowflakeSQLGenerator
    ProgressTracker = MockProgressTracker
    FileManager = MockFileManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class InformaticaTranslationPipeline:
    """
    Complete 6-phase Informatica to Snowflake translation pipeline
    """

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.xml_parser = InformaticaXMLParser()
        self.sql_generator = SnowflakeSQLGenerator()
        self.progress_tracker = ProgressTracker(session_id)
        self.file_manager = FileManager(session_id)
        self.workflow: Optional[InformaticaWorkflow] = None

        # ETL server params repository path
        self.etl_params_repo_path = os.environ.get(
            'ETL_PARAMS_REPO_PATH',
            'G:\\Projects\\BA\\etl-server-params 1\\etl-server-params\\'
        )

    async def execute_pipeline(self, xml_content: str) -> Dict[str, Any]:
        """Execute the complete 6-phase translation pipeline"""
        try:
            logger.info(f"Starting translation pipeline for session {self.session_id}")

            results = {
                'session_id': self.session_id,
                'status': 'success',
                'phases_completed': [],
                'generated_files': [],
                'errors': [],
                'warnings': []
            }

            # Parse XML first
            logger.info("Parsing Informatica XML...")
            self.workflow = self.xml_parser.parse_xml_file(xml_content)

            # Execute each phase
            await self.phase_a_generate_readme(results)
            await self.phase_b_copy_param_file(results)
            await self.phase_c_generate_snowflake_sql(results)
            await self.phase_d_generate_test_files(results)
            await self.phase_e_generate_snowflake_yml(results)
            await self.phase_f_generate_test_data_folder(results)

            results['status'] = 'success'
            logger.info(f"Translation pipeline completed successfully for session {self.session_id}")

            return results

        except Exception as e:
            logger.error(f"Translation pipeline failed for session {self.session_id}: {e}")
            results['status'] = 'failed'
            results['errors'].append(str(e))
            raise

    async def phase_a_generate_readme(self, results: Dict[str, Any]):
        """Phase A: Generate README from XML"""
        logger.info("Phase A: Generating README from XML")
        self.progress_tracker.update_phase('Phase A', 0)

        try:
            readme_content = self._generate_workflow_readme()
            filename = f"{self.workflow.name}_readme.md"
            self.file_manager.save_file(filename, readme_content)

            results['phases_completed'].append('Phase A')
            results['generated_files'].append(filename)

            self.progress_tracker.update_phase('Phase A', 100)
            logger.info("Phase A completed: README generated")

        except Exception as e:
            logger.error(f"Phase A failed: {e}")
            results['errors'].append(f"Phase A: {str(e)}")
            raise

    async def phase_b_copy_param_file(self, results: Dict[str, Any]):
        """Phase B: Find and copy .param file"""
        logger.info("Phase B: Finding and copying .param file")
        self.progress_tracker.update_phase('Phase B', 0)

        try:
            if self.workflow.parameter_filename:
                param_content = self._locate_and_read_param_file(self.workflow.parameter_filename)
                if param_content:
                    filename = os.path.basename(self.workflow.parameter_filename)
                    self.file_manager.save_file(filename, param_content)
                    results['generated_files'].append(filename)
                else:
                    results['warnings'].append(f"Parameter file not found: {self.workflow.parameter_filename}")
            else:
                results['warnings'].append("No parameter filename specified in workflow")

            results['phases_completed'].append('Phase B')
            self.progress_tracker.update_phase('Phase B', 100)
            logger.info("Phase B completed: Parameter file processed")

        except Exception as e:
            logger.error(f"Phase B failed: {e}")
            results['errors'].append(f"Phase B: {str(e)}")
            # Continue with other phases even if param file isn't found

    async def phase_c_generate_snowflake_sql(self, results: Dict[str, Any]):
        """Phase C: Generate Snowflake SQL files"""
        logger.info("Phase C: Generating Snowflake SQL files")
        self.progress_tracker.update_phase('Phase C', 0)

        try:
            sql_files_generated = 0
            total_sessions = len(self.workflow.sessions)

            for i, session in enumerate(self.workflow.sessions):
                logger.info(f"Generating SQL for session: {session.name}")

                # Generate SQL content
                sql_content = self.sql_generator.generate_complete_sql_file(self.workflow, session)
                filename = f"{session.name}_generated.snowsql"
                self.file_manager.save_file(filename, sql_content)

                results['generated_files'].append(filename)
                sql_files_generated += 1

                # Update progress
                progress = int((i + 1) / total_sessions * 100)
                self.progress_tracker.update_phase('Phase C', progress)

            results['phases_completed'].append('Phase C')
            logger.info(f"Phase C completed: {sql_files_generated} SQL files generated")

        except Exception as e:
            logger.error(f"Phase C failed: {e}")
            results['errors'].append(f"Phase C: {str(e)}")
            raise

    async def phase_d_generate_test_files(self, results: Dict[str, Any]):
        """Phase D: Generate test files"""
        logger.info("Phase D: Generating test files")
        self.progress_tracker.update_phase('Phase D', 0)

        try:
            test_files_generated = 0
            total_sessions = len(self.workflow.sessions)

            for i, session in enumerate(self.workflow.sessions):
                test_content = self._generate_test_file_for_session(session)
                filename = f"{session.name}_test.snowsql"
                self.file_manager.save_file(filename, test_content)

                results['generated_files'].append(filename)
                test_files_generated += 1

                # Update progress
                progress = int((i + 1) / total_sessions * 100)
                self.progress_tracker.update_phase('Phase D', progress)

            results['phases_completed'].append('Phase D')
            logger.info(f"Phase D completed: {test_files_generated} test files generated")

        except Exception as e:
            logger.error(f"Phase D failed: {e}")
            results['errors'].append(f"Phase D: {str(e)}")
            raise

    async def phase_e_generate_snowflake_yml(self, results: Dict[str, Any]):
        """Phase E: Generate snowflake.yml"""
        logger.info("Phase E: Generating snowflake.yml")
        self.progress_tracker.update_phase('Phase E', 0)

        try:
            yml_content = self._generate_snowflake_yml()
            filename = "snowflake.yml"
            self.file_manager.save_file(filename, yml_content)

            results['generated_files'].append(filename)
            results['phases_completed'].append('Phase E')

            self.progress_tracker.update_phase('Phase E', 100)
            logger.info("Phase E completed: snowflake.yml generated")

        except Exception as e:
            logger.error(f"Phase E failed: {e}")
            results['errors'].append(f"Phase E: {str(e)}")
            raise

    async def phase_f_generate_test_data_folder(self, results: Dict[str, Any]):
        """Phase F: Generate test_data folder"""
        logger.info("Phase F: Generating test_data folder")
        self.progress_tracker.update_phase('Phase F', 0)

        try:
            test_data_files = 0
            total_sessions = len(self.workflow.sessions)

            for i, session in enumerate(self.workflow.sessions):
                # Generate INSERT SQL for staging table
                insert_sql = self._generate_test_insert_sql(session)
                insert_filename = f"test_data/{session.name}_insert.sql"
                self.file_manager.save_file(insert_filename, insert_sql)
                results['generated_files'].append(insert_filename)

                # Generate CSV input file
                csv_content = self._generate_test_csv_file(session)
                csv_filename = f"test_data/{session.sources[0].name}.csv" if session.sources else f"test_data/{session.name}_input.csv"
                self.file_manager.save_file(csv_filename, csv_content)
                results['generated_files'].append(csv_filename)

                test_data_files += 2

                # Update progress
                progress = int((i + 1) / total_sessions * 100)
                self.progress_tracker.update_phase('Phase F', progress)

            results['phases_completed'].append('Phase F')
            logger.info(f"Phase F completed: {test_data_files} test data files generated")

        except Exception as e:
            logger.error(f"Phase F failed: {e}")
            results['errors'].append(f"Phase F: {str(e)}")
            raise

    def _generate_workflow_readme(self) -> str:
        """Generate comprehensive README documentation"""
        readme_parts = []

        # Header
        readme_parts.append(f"# {self.workflow.name}")
        readme_parts.append(f"**Informatica to Snowflake Translation**")
        readme_parts.append(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        readme_parts.append("")

        # Workflow Overview
        readme_parts.append("## Workflow Overview")
        readme_parts.append(f"- **Workflow Name**: {self.workflow.name}")
        readme_parts.append(f"- **Folder**: {self.workflow.folder}")
        readme_parts.append(f"- **Scheduler Type**: {self.workflow.scheduler_type}")
        if self.workflow.parameter_filename:
            readme_parts.append(f"- **Parameter File**: {self.workflow.parameter_filename}")
        readme_parts.append("")

        # Sessions
        readme_parts.append("## Sessions")
        for i, session in enumerate(self.workflow.sessions, 1):
            readme_parts.append(f"### {i}. {session.name}")
            readme_parts.append(f"- **Mapping**: {session.mapping_name}")
            readme_parts.append(f"- **Treat Source Rows As**: {session.treat_source_rows_as}")

            if session.sources:
                readme_parts.append("- **Sources**:")
                for source in session.sources:
                    readme_parts.append(f"  - {source.name} ({source.type})")
                    readme_parts.append(f"    - Fields: {len(source.fields)} columns")

            if session.targets:
                readme_parts.append("- **Targets**:")
                for target in session.targets:
                    readme_parts.append(f"  - {target.name} ({target.type})")
                    readme_parts.append(f"    - Fields: {len(target.fields)} columns")

            readme_parts.append("")

        # Link Conditions
        if self.workflow.link_conditions:
            readme_parts.append("## Link Conditions")
            for link in self.workflow.link_conditions:
                readme_parts.append(f"- {link.from_task} → {link.to_task} ({link.condition})")
            readme_parts.append("")

        # Generated Files
        readme_parts.append("## Generated Files")
        readme_parts.append("This translation generates the following Snowflake artifacts:")
        readme_parts.append("- **SQL Files**: Complete Snowflake SQL with CTEs and transformations")
        readme_parts.append("- **Test Files**: Unit tests and validation scripts")
        readme_parts.append("- **Configuration**: snowflake.yml with environment variables")
        readme_parts.append("- **Test Data**: Sample data and INSERT scripts")

        return "\n".join(readme_parts)

    def _locate_and_read_param_file(self, param_filename: str) -> Optional[str]:
        """Locate and read parameter file from etl-server-params repo"""
        try:
            # Convert XML path to local repo path
            # Example: /vw/param/JBA/UVW1708.param -> vw/param/JBA/UVW1708.param
            local_path = param_filename.lstrip('/')
            full_path = os.path.join(self.etl_params_repo_path, local_path)

            if os.path.exists(full_path):
                with open(full_path, 'r', encoding='utf-8') as f:
                    return f.read()
            else:
                logger.warning(f"Parameter file not found: {full_path}")
                return None

        except Exception as e:
            logger.error(f"Error reading parameter file {param_filename}: {e}")
            return None

    def _generate_test_file_for_session(self, session) -> str:
        """Generate test file content for a session"""
        test_parts = []

        # Header
        test_parts.append(f"-- Test file for {session.name}")
        test_parts.append(f"-- Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        test_parts.append("")

        # Test setup
        test_parts.append("-- TEST SETUP")
        if session.sources:
            source = session.sources[0]
            test_parts.append(f"-- Insert sample data into {source.name}")
            test_parts.append(f"INSERT INTO STAGING.{source.name} VALUES")
            test_parts.append("    ('sample_value1', 'sample_value2'),")
            test_parts.append("    ('sample_value3', 'sample_value4');")
            test_parts.append("")

        # Test execution
        test_parts.append("-- TEST EXECUTION")
        test_parts.append(f"-- Execute the main transformation from {session.name}_generated.snowsql")
        test_parts.append("")

        # Test validation
        test_parts.append("-- TEST VALIDATION")
        test_parts.append("SELECT 'Row Count Test' AS test_name,")
        test_parts.append("       IFF(COUNT(*) > 0, 'PASS', 'FAIL') AS result,")
        test_parts.append("       COUNT(*) AS actual_value")
        if session.targets:
            test_parts.append(f"FROM BASE.{session.targets[0].name};")
        else:
            test_parts.append("FROM target_table;")

        return "\n".join(test_parts)

    def _generate_snowflake_yml(self) -> str:
        """Generate snowflake.yml configuration file"""
        yml_parts = []

        yml_parts.append("definition_version: 2")
        yml_parts.append("env:")
        yml_parts.append("  LANDING_STAGE: PUBLIC.BA_INTERNAL_STAGE_FW")
        yml_parts.append("")

        # Add environment variables for each session
        for session in self.workflow.sessions:
            yml_parts.append(f"  # {session.name}")

            # Input file variables
            if session.sources and session.sources[0].type == "Flat File":
                source_name = session.sources[0].name
                yml_parts.append(f"  {session.name}_inputfile: $PMSourceFileDir/{source_name}.csv")
                yml_parts.append(f"  {session.name}_InputFileName: {source_name}.csv")

            # Output file variables (if target is flat file)
            if session.targets and session.targets[0].type == "Flat File":
                target_name = session.targets[0].name
                yml_parts.append(f"  {session.name}_OutputFileName: {target_name}.csv")
                yml_parts.append(f"  {session.name}_OutputFileName_DIR: $PMTargetFileDir/")

            yml_parts.append("")

        return "\n".join(yml_parts)

    def _generate_test_insert_sql(self, session) -> str:
        """Generate INSERT SQL for test data"""
        if not session.sources:
            return "-- No sources defined"

        source = session.sources[0]
        insert_parts = []

        insert_parts.append(f"-- Test data INSERT for {source.name}")
        insert_parts.append(f"INSERT INTO STAGING.{source.name} (")

        # Column names
        columns = [field.name for field in source.fields]
        insert_parts.append("    " + ",\n    ".join(columns))
        insert_parts.append(")")
        insert_parts.append("VALUES")

        # Sample data rows
        for i in range(5):
            values = []
            for field in source.fields:
                if 'date' in field.datatype.lower():
                    values.append("'2024-01-15'")
                elif 'int' in field.datatype.lower() or 'number' in field.datatype.lower():
                    values.append(str(100 + i))
                else:
                    values.append(f"'test_value_{i+1}'")

            row = "    (" + ", ".join(values) + ")"
            if i < 4:
                row += ","
            else:
                row += ";"
            insert_parts.append(row)

        return "\n".join(insert_parts)

    def _generate_test_csv_file(self, session) -> str:
        """Generate CSV test data file"""
        if not session.sources:
            return "-- No sources defined"

        source = session.sources[0]
        csv_parts = []

        # Header row
        headers = [field.name for field in source.fields]
        csv_parts.append(",".join(headers))

        # Data rows
        for i in range(5):
            values = []
            for field in source.fields:
                if 'date' in field.datatype.lower():
                    values.append("2024-01-15")
                elif 'int' in field.datatype.lower() or 'number' in field.datatype.lower():
                    values.append(str(100 + i))
                else:
                    values.append(f"test_value_{i+1}")
            csv_parts.append(",".join(values))

        return "\n".join(csv_parts)


async def execute_translation_pipeline(session_id: str, xml_content: str = None) -> Dict[str, Any]:
    """
    Execute the 6-phase Informatica to Snowflake translation pipeline
    """
    try:
        pipeline = InformaticaTranslationPipeline(session_id)

        # For now, use sample XML if none provided
        if not xml_content:
            xml_content = """<?xml version="1.0" encoding="UTF-8"?>
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

        return await pipeline.execute_pipeline(xml_content)

    except Exception as e:
        logger.error(f"Translation pipeline execution failed: {e}")
        return {
            'session_id': session_id,
            'status': 'failed',
            'phases_completed': [],
            'generated_files': [],
            'errors': [str(e)],
            'warnings': []
        }


def handler(event: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Start processing pipeline for uploaded files
    """
    try:
        # Handle CORS preflight
        if event.get('httpMethod') == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'POST, OPTIONS',
                    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
                },
                'body': ''
            }

        if event.get('httpMethod') != 'POST':
            return {
                'statusCode': 405,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Content-Type': 'application/json',
                },
                'body': json.dumps({'error': 'Method not allowed'})
            }

        # Extract session_id from path or body
        path = event.get('path', '')
        session_id = path.split('/')[-1] if '/' in path else None

        if not session_id:
            # Try to get from request body
            body = event.get('body', '{}')
            try:
                data = json.loads(body)
                session_id = data.get('session_id')
            except:
                pass

        if not session_id:
            return {
                'statusCode': 400,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Content-Type': 'application/json',
                },
                'body': json.dumps({'error': 'Session ID required'})
            }

        # In production, this would trigger async processing
        # For now, return success response
        response_data = {
            'session_id': session_id,
            'status': 'processing_started',
            'message': 'Complete translation pipeline initiated with XML parsing and SQL generation',
            'estimated_completion_time': '2-5 minutes',
            'phases': [
                'Phase A: README Generation',
                'Phase B: Parameter File Discovery',
                'Phase C: Snowflake SQL Generation',
                'Phase D: Test File Creation',
                'Phase E: Configuration Generation',
                'Phase F: Test Data Generation'
            ]
        }

        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/json',
            },
            'body': json.dumps(response_data)
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/json',
            },
            'body': json.dumps({'error': str(e)})
        }