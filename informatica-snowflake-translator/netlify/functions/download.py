import json
import os
import base64
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

MIME_TYPES = {
    '.sql': 'text/plain',
    '.snowsql': 'text/plain',
    '.md': 'text/markdown',
    '.csv': 'text/csv',
    '.yml': 'text/yaml',
    '.yaml': 'text/yaml',
    '.txt': 'text/plain',
    '.json': 'application/json',
    '.zip': 'application/zip',
}

def get_mime_type(filename: str) -> str:
    """Determine MIME type from filename"""
    _, ext = os.path.splitext(filename.lower())
    return MIME_TYPES.get(ext, 'application/octet-stream')

def handler(event: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Download endpoint for generated files

    Routes:
    - GET /api/download/{sessionId}/{filename} - Download single file
    - GET /api/download/all/{sessionId} - Download all files as ZIP
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

        if len(path_parts) < 3:
            return {
                'statusCode': 400,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Content-Type': 'application/json',
                },
                'body': json.dumps({'error': 'Invalid path'})
            }

        session_id = unquote(path_parts[-2])
        filename_or_all = unquote(path_parts[-1])

        file_manager = FileManager(session_id)

        if filename_or_all == 'all':
            zip_buffer = file_manager.create_zip_archive()
            if not zip_buffer:
                return {
                    'statusCode': 404,
                    'headers': {
                        'Access-Control-Allow-Origin': '*',
                        'Content-Type': 'application/json',
                    },
                    'body': json.dumps({'error': 'No files found'})
                }

            zip_content = zip_buffer.getvalue()
            encoded_zip = base64.b64encode(zip_content).decode('utf-8')

            return {
                'statusCode': 200,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Content-Type': 'application/zip',
                    'Content-Disposition': f'attachment; filename="translation_{session_id}.zip"',
                    'Content-Length': str(len(zip_content)),
                },
                'body': encoded_zip,
                'isBase64Encoded': True
            }
        else:
            file_content = file_manager.get_file_content(filename_or_all)
            if file_content is None:
                return {
                    'statusCode': 404,
                    'headers': {
                        'Access-Control-Allow-Origin': '*',
                        'Content-Type': 'application/json',
                    },
                    'body': json.dumps({'error': 'File not found'})
                }

            mime_type = get_mime_type(filename_or_all)

            if mime_type.startswith('text/') or mime_type == 'application/json':
                if isinstance(file_content, bytes):
                    file_content = file_content.decode('utf-8')

                return {
                    'statusCode': 200,
                    'headers': {
                        'Access-Control-Allow-Origin': '*',
                        'Content-Type': mime_type,
                        'Content-Disposition': f'attachment; filename="{os.path.basename(filename_or_all)}"',
                    },
                    'body': file_content
                }
            else:
                if isinstance(file_content, str):
                    file_content = file_content.encode('utf-8')

                encoded_content = base64.b64encode(file_content).decode('utf-8')

                return {
                    'statusCode': 200,
                    'headers': {
                        'Access-Control-Allow-Origin': '*',
                        'Content-Type': mime_type,
                        'Content-Disposition': f'attachment; filename="{os.path.basename(filename_or_all)}"',
                        'Content-Length': str(len(file_content)),
                    },
                    'body': encoded_content,
                    'isBase64Encoded': True
                }

    except Exception as e:
        logger.error(f"Download endpoint error: {e}")
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/json',
            },
            'body': json.dumps({'error': str(e)})
        }
