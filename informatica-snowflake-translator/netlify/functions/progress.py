import json
import logging
from typing import Dict, Any
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def handler(event: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get processing progress for a session
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

        # Extract session_id from path
        path = event.get('path', '')
        session_id = path.split('/')[-1] if '/' in path else None

        if not session_id:
            return {
                'statusCode': 400,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Content-Type': 'application/json',
                },
                'body': json.dumps({'error': 'Session ID required'})
            }

        # Return completed progress data
        # In production, this would check actual processing status from storage
        progress_data = {
            'sessionId': session_id,
            'overallProgress': 100,
            'currentPhase': 'Phase F',
            'status': 'completed',
            'phases': {
                'Phase A': {'status': 'completed', 'progress': 100, 'message': 'README Generation Complete'},
                'Phase B': {'status': 'completed', 'progress': 100, 'message': 'Parameter Discovery Complete'},
                'Phase C': {'status': 'completed', 'progress': 100, 'message': 'SQL Generation Complete'},
                'Phase D': {'status': 'completed', 'progress': 100, 'message': 'Test Creation Complete'},
                'Phase E': {'status': 'completed', 'progress': 100, 'message': 'YAML Configuration Complete'},
                'Phase F': {'status': 'completed', 'progress': 100, 'message': 'Test Data Generation Complete'},
            },
            'errors': [],
            'warnings': ['Parameter file not found in repository - using default values'],
            'startedAt': datetime.now(timezone.utc).isoformat(),
            'completedAt': datetime.now(timezone.utc).isoformat()
        }

        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/json',
            },
            'body': json.dumps(progress_data)
        }

    except Exception as e:
        logger.error(f"Progress tracking failed for session: {e}")
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/json',
            },
            'body': json.dumps({'error': str(e)})
        }