import json
import os
import logging
from typing import Dict, Any
from urllib.parse import unquote

try:
    from .utils.FileManager import FileManager
except ImportError:
    import sys
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from utils.FileManager import FileManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def handler(event: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Files endpoint for listing generated files

    Routes:
    - GET /api/files/{sessionId} - List all generated files with metadata
    - GET /api/files/{sessionId}/preview/{filename} - Get file preview
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

        path = event.get('path', '')
        path_parts = [p for p in path.split('/') if p]

        if len(path_parts) < 2:
            return {
                'statusCode': 400,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Content-Type': 'application/json',
                },
                'body': json.dumps({'error': 'Invalid path'})
            }

        session_id = unquote(path_parts[-1]) if len(path_parts) == 2 else unquote(path_parts[-2])
        query_params = event.get('queryStringParameters', {}) or {}

        file_manager = FileManager(session_id)

        if len(path_parts) >= 3 and path_parts[-2] == 'preview':
            filename = unquote(path_parts[-1])
            preview = file_manager.get_file_preview(filename, max_lines=100)

            if preview is None:
                return {
                    'statusCode': 404,
                    'headers': {
                        'Access-Control-Allow-Origin': '*',
                        'Content-Type': 'application/json',
                    },
                    'body': json.dumps({'error': 'File not found'})
                }

            return {
                'statusCode': 200,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Content-Type': 'application/json',
                },
                'body': json.dumps({
                    'filename': filename,
                    'preview': preview,
                    'session_id': session_id
                })
            }
        else:
            files_metadata = file_manager.list_files()
            stats = file_manager.get_session_stats()
            download_links = file_manager.generate_download_links()

            return {
                'statusCode': 200,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Content-Type': 'application/json',
                },
                'body': json.dumps({
                    'session_id': session_id,
                    'files': files_metadata,
                    'stats': stats,
                    'download_links': download_links
                })
            }

    except Exception as e:
        logger.error(f"Files endpoint error: {e}")
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/json',
            },
            'body': json.dumps({'error': str(e)})
        }
