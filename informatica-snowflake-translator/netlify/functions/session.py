import json
from typing import Dict, Any
from datetime import datetime, timezone


def handler(event: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle session-related requests (get session results, status, etc.)
    """
    try:
        # Handle CORS preflight
        if event.get('httpMethod') == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
                    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
                },
                'body': ''
            }

        # Parse path to extract session_id and action
        path = event.get('path', '')
        path_parts = path.strip('/').split('/')

        if len(path_parts) < 3:  # api/session/session_id
            return {
                'statusCode': 400,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Content-Type': 'application/json',
                },
                'body': json.dumps({'error': 'Session ID required'})
            }

        session_id = path_parts[2]
        action = path_parts[3] if len(path_parts) > 3 else 'status'

        if event.get('httpMethod') == 'GET':
            if action == 'results':
                return handle_get_session_results(session_id)
            elif action == 'status':
                return handle_get_session_status(session_id)
            else:
                return {
                    'statusCode': 400,
                    'headers': {
                        'Access-Control-Allow-Origin': '*',
                        'Content-Type': 'application/json',
                    },
                    'body': json.dumps({'error': 'Invalid action'})
                }

        return {
            'statusCode': 405,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/json',
            },
            'body': json.dumps({'error': 'Method not allowed'})
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


def handle_get_session_results(session_id: str) -> Dict[str, Any]:
    """Get complete processing results for a session"""
    try:
        # In production, this would fetch from database/storage
        # For now, return realistic mock data based on the actual pipeline

        results = {
            'sessionId': session_id,
            'status': 'success',
            'phasesCompleted': [
                'Phase A: README Generation',
                'Phase B: Parameter Discovery',
                'Phase C: SQL Generation',
                'Phase D: Test Creation',
                'Phase E: YAML Configuration',
                'Phase F: Test Data'
            ],
            'generatedFiles': [
                {
                    'id': 'readme-1',
                    'name': f'Wf_{session_id}_readme.md',
                    'type': 'readme',
                    'phase': 'Phase A',
                    'size': 15240,
                    'path': f'/generated/{session_id}/readme.md',
                    'createdAt': datetime.now(timezone.utc).isoformat(),
                    'preview': '# Workflow Overview\n\nThis workflow processes JBA outbound file details with complete Informatica to Snowflake translation...',
                },
                {
                    'id': 'param-1',
                    'name': f'{session_id.upper()}.param',
                    'type': 'param',
                    'phase': 'Phase B',
                    'size': 2048,
                    'path': f'/generated/{session_id}/params.param',
                    'createdAt': datetime.now(timezone.utc).isoformat(),
                },
                {
                    'id': 'sql-1',
                    'name': f'S_{session_id}_generated.snowsql',
                    'type': 'snowsql',
                    'phase': 'Phase C',
                    'size': 8945,
                    'path': f'/generated/{session_id}/main.sql',
                    'createdAt': datetime.now(timezone.utc).isoformat(),
                    'preview': f'-- Generated Snowflake SQL for {session_id}\n-- Complete transformation with CTEs and data quality checks\n\nCREATE OR REPLACE TRANSIENT TABLE STAGING.{session_id}_staging (\n    field1 VARCHAR(255),\n    field2 VARCHAR(100),\n    load_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP()\n);',
                },
                {
                    'id': 'test-1',
                    'name': f'S_{session_id}_test.snowsql',
                    'type': 'test',
                    'phase': 'Phase D',
                    'size': 3245,
                    'path': f'/generated/{session_id}/test.sql',
                    'createdAt': datetime.now(timezone.utc).isoformat(),
                    'preview': f'-- Test file for {session_id}\n-- Comprehensive validation and data quality tests\n\n-- Row count validation\nSELECT COUNT(*) as row_count FROM BASE.{session_id}_target;',
                },
                {
                    'id': 'yaml-1',
                    'name': 'snowflake.yml',
                    'type': 'yaml',
                    'phase': 'Phase E',
                    'size': 1854,
                    'path': f'/generated/{session_id}/snowflake.yml',
                    'createdAt': datetime.now(timezone.utc).isoformat(),
                    'preview': f'definition_version: 2\nenv:\n  LANDING_STAGE: PUBLIC.BA_INTERNAL_STAGE_FW\n  {session_id}_inputfile: /data/input_{session_id}.csv\n  {session_id}_outputdir: /data/output/',
                },
                {
                    'id': 'csv-1',
                    'name': f'{session_id}_test_data.csv',
                    'type': 'csv',
                    'phase': 'Phase F',
                    'size': 521,
                    'path': f'/generated/{session_id}/test_data.csv',
                    'createdAt': datetime.now(timezone.utc).isoformat(),
                    'preview': 'id,name,status,created_date\n1,Sample Data 1,Active,2024-01-01\n2,Sample Data 2,Inactive,2024-01-02',
                },
            ],
            'summary': {
                'workflowsProcessed': 1,
                'sessionsProcessed': 2,
                'sqlFilesGenerated': 2,
                'testFilesGenerated': 2,
                'errorsFound': 0,
                'warningsFound': 1,
                'processingTimeMs': 285000,
            },
            'completedAt': datetime.now(timezone.utc).isoformat(),
        }

        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/json',
            },
            'body': json.dumps(results)
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/json',
            },
            'body': json.dumps({'error': f'Failed to get session results: {str(e)}'})
        }


def handle_get_session_status(session_id: str) -> Dict[str, Any]:
    """Get session processing status"""
    try:
        # In production, this would check actual processing status
        status_data = {
            'sessionId': session_id,
            'status': 'completed',
            'currentPhase': 'Phase F',
            'progress': 100,
            'message': 'Translation completed successfully',
            'startedAt': datetime.now(timezone.utc).isoformat(),
            'completedAt': datetime.now(timezone.utc).isoformat(),
        }

        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/json',
            },
            'body': json.dumps(status_data)
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/json',
            },
            'body': json.dumps({'error': f'Failed to get session status: {str(e)}'})
        }