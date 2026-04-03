import json

def handler(event, context):
    """
    Simple test function to verify Netlify Functions are working
    """
    return {
        'statusCode': 200,
        'headers': {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json',
        },
        'body': json.dumps({
            'message': 'Hello from Netlify Functions!',
            'status': 'success',
            'event': event.get('httpMethod', 'unknown')
        })
    }