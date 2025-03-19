import json
import os
import logging
from connection_manager import ConnectionManager
from message_handler import MessageHandler

logger = logging.getLogger()
logger.setLevel(logging.INFO)

connection_manager = ConnectionManager(
    table_name=os.environ.get('CONNECTIONS_TABLE_NAME')
)
message_handler = MessageHandler(connection_manager)

def lambda_handler(event, context):
    logger.info(f"Event received: {json.dumps(event)}")

    # Extract required information from the event
    route_key = event.get('requestContext', {}).get('routeKey')
    connection_id = event.get('requestContext', {}).get('connectionId')
    domain_name = event.get('requestContext', {}).get('domainName')
    stage = event.get('requestContext', {}).get('stage')

    if not connection_id or not domain_name or not stage:
        logger.error("Missing required WebSocket event information")
        return {'statusCode': 400, 'body': 'Invalid request'}

    endpoint_url = f"https://{domain_name}/{stage}"
    connection_manager.set_endpoint_url(endpoint_url)

    try:
        if route_key == '$connect':
            # Auth not implemented - only a test app!
            # auth_token = event.get('queryStringParameters', {}).get('token')
            # if not auth_token or not validate_token(auth_token):
            #     return {'statusCode': 401, 'body': 'Unauthorized'}

            connection_manager.add_connection(connection_id)
            return {'statusCode': 200, 'body': 'Connected'}

        elif route_key == '$disconnect':
            connection_manager.remove_connection(connection_id)
            return {'statusCode': 200, 'body': 'Disconnected'}

        elif route_key == '$default':
            body = event.get('body')
            if not body:
                return {'statusCode': 400, 'body': 'Empty message'}

            try:
                message_data = json.loads(body)
                return message_handler.process_message(connection_id, message_data)
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON in message: {body}")
                return {'statusCode': 400, 'body': 'Invalid JSON'}
        else:
            return message_handler.handle_custom_route(route_key, connection_id, event)

    except Exception as e:
        logger.error(f"Error processing WebSocket event: {str(e)}")
        return {'statusCode': 500, 'body': f'Internal error: {str(e)}'}
