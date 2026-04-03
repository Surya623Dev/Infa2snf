import json
import os
import zipfile
import io
from typing import Dict, Any
from urllib.parse import unquote


def handler(event: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle file downloads for generated files
    """
    try:
        # Handle CORS preflight
        if event.get('httpMethod') == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'GET, OPTIONS',
                    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
                },
                'body': ''
            }

        if event.get('httpMethod') != 'GET':
            return {
                'statusCode': 405,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Content-Type': 'application/json',
                },
                'body': json.dumps({'error': 'Method not allowed'})
            }

        # Parse path to extract session_id and file_id/action
        path = event.get('path', '')
        path_parts = path.strip('/').split('/')

        if len(path_parts) < 4:  # api/download/session_id/action
            return {
                'statusCode': 400,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Content-Type': 'application/json',
                },
                'body': json.dumps({'error': 'Invalid path format'})
            }

        session_id = path_parts[2]
        action = path_parts[3]

        if action == 'all':
            # Download all files as ZIP
            return handle_download_all(session_id)
        elif action == 'files' and len(path_parts) >= 5:
            # Download specific file or preview
            file_id = path_parts[4]
            is_preview = len(path_parts) > 5 and path_parts[5] == 'preview'
            return handle_download_file(session_id, file_id, is_preview)
        else:
            return {
                'statusCode': 400,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Content-Type': 'application/json',
                },
                'body': json.dumps({'error': 'Invalid download action'})
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


def handle_download_all(session_id: str) -> Dict[str, Any]:
    """Create and return ZIP file with all generated files"""
    try:
        # For now, create a sample ZIP with mock files
        # In production, this would read from file storage

        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Add sample files (in production, read from storage)
            files_to_add = [
                ('README.md', '# Generated Workflow Documentation\n\nThis is a sample generated README file.'),
                ('snowflake.sql', '-- Generated Snowflake SQL\nCREATE OR REPLACE TABLE staging_table (\n    id INTEGER,\n    name VARCHAR(255)\n);'),
                ('snowflake.yml', 'definition_version: 2\nenv:\n  LANDING_STAGE: PUBLIC.BA_INTERNAL_STAGE_FW'),
                ('test_data.csv', 'id,name,date\n1,Test Data,2024-01-01\n2,Sample Row,2024-01-02'),
            ]

            for filename, content in files_to_add:
                zip_file.writestr(filename, content)

        zip_data = zip_buffer.getvalue()

        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/zip',
                'Content-Disposition': f'attachment; filename="{session_id}-files.zip"',
                'Content-Length': str(len(zip_data)),
            },
            'body': zip_data.hex(),  # Convert binary to hex for Netlify
            'isBase64Encoded': False
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/json',
            },
            'body': json.dumps({'error': f'Failed to create ZIP file: {str(e)}'})
        }


def handle_download_file(session_id: str, file_id: str, is_preview: bool = False) -> Dict[str, Any]:
    """Download specific file or return preview content"""
    try:
        # Mock file content based on file_id
        # In production, this would read from file storage

        if 'readme' in file_id.lower():
            content = """# Workflow Documentation

## Overview
This is a generated README for the Informatica to Snowflake translation.

## Generated Files
- SQL files with complete transformations
- Test files for validation
- Configuration files for deployment
"""
            content_type = 'text/markdown'
            filename = f'{session_id}_README.md'

        elif 'sql' in file_id.lower() or 'snowsql' in file_id.lower():
            content = """-- Generated Snowflake SQL
-- Session: {}

CREATE OR REPLACE TRANSIENT TABLE STAGING.workflow_table (
    field1 VARCHAR(255),
    field2 VARCHAR(100),
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
);

-- Sample transformation logic
INSERT INTO BASE.target_table
SELECT
    UPPER(field1) as field1_transformed,
    COALESCE(field2, 'DEFAULT') as field2_clean,
    created_date
FROM STAGING.workflow_table
WHERE field1 IS NOT NULL;
""".format(session_id)
            content_type = 'text/plain'
            filename = f'{session_id}_generated.sql'

        elif 'yaml' in file_id.lower() or 'yml' in file_id.lower():
            content = f"""definition_version: 2
env:
  LANDING_STAGE: PUBLIC.BA_INTERNAL_STAGE_FW
  session_inputfile: /data/input_{session_id}.csv
  session_outputfile: /data/output_{session_id}.csv
"""
            content_type = 'text/yaml'
            filename = f'{session_id}_snowflake.yml'

        elif 'csv' in file_id.lower():
            content = """id,name,status,created_date
1,Sample Data 1,Active,2024-01-01
2,Sample Data 2,Inactive,2024-01-02
3,Sample Data 3,Active,2024-01-03
"""
            content_type = 'text/csv'
            filename = f'{session_id}_test_data.csv'

        else:
            content = f"Generated file content for {file_id}"
            content_type = 'text/plain'
            filename = f'{session_id}_{file_id}.txt'

        if is_preview:
            # Return content as JSON for preview
            return {
                'statusCode': 200,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Content-Type': 'application/json',
                },
                'body': json.dumps(content)
            }
        else:
            # Return file for download
            return {
                'statusCode': 200,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Content-Type': content_type,
                    'Content-Disposition': f'attachment; filename="{filename}"',
                },
                'body': content
            }

    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/json',
            },
            'body': json.dumps({'error': f'Failed to download file: {str(e)}'})
        }