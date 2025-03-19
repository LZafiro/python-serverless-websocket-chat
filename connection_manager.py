import boto3
import json
import logging
from botocore.exceptions import ClientError

logger = logging.getLogger()

class ConnectionManager:
    """
    Manages WebSocket connections using DynamoDB for storage
    and API Gateway Management API for sending messages.
    """

    def __init__(self, table_name):
        self.table_name = table_name
        self.dynamodb = boto3.resource('dynamodb')
        self.table = self.dynamodb.Table(table_name) # type: ignore
        self.apigw_management = None

    def set_endpoint_url(self, endpoint_url):
        self.apigw_management = boto3.client(
            'apigatewaymanagementapi',
            endpoint_url=endpoint_url
        )

    def add_connection(self, connection_id, user_data=None):
        try:
            item = {
                'connectionId': connection_id,
                'connected': True
            }

            if user_data:
                item['userData'] = user_data

            self.table.put_item(Item=item)
            logger.info(f"Connection added: {connection_id}")
            return True
        except ClientError as e:
            logger.error(f"Error adding connection {connection_id}: {str(e)}")
            return False

    def remove_connection(self, connection_id):
        try:
            self.table.delete_item(Key={'connectionId': connection_id})
            logger.info(f"Connection removed: {connection_id}")
            return True
        except ClientError as e:
            logger.error(f"Error removing connection {connection_id}: {str(e)}")
            return False

    def get_all_connections(self):
        try:
            response = self.table.scan(
                FilterExpression='connected = :connected',
                ExpressionAttributeValues={':connected': True}
            )
            return response.get('Items', [])
        except ClientError as e:
            logger.error(f"Error retrieving connections: {str(e)}")
            return []

    def send_message(self, connection_id, message):
        if not self.apigw_management:
            logger.error("API Gateway Management API client not initialized")
            return False

        try:
            if isinstance(message, dict):
                message = json.dumps(message)

            self.apigw_management.post_to_connection(
                ConnectionId=connection_id,
                Data=message.encode('utf-8') if isinstance(message, str) else message
            )
            logger.info(f"Message sent to connection {connection_id}")
            return True
        except self.apigw_management.exceptions.GoneException:
            # Connection is no longer available
            logger.info(f"Connection {connection_id} is gone, removing")
            self.remove_connection(connection_id)
            return False
        except Exception as e:
            logger.error(f"Error sending message to connection {connection_id}: {str(e)}")
            return False

    def broadcast_message(self, message, exclude_connection_ids=None):
        if not exclude_connection_ids:
            exclude_connection_ids = []

        connections = self.get_all_connections()
        successful_broadcasts = 0

        for connection in connections:
            connection_id = connection.get('connectionId')
            if connection_id and connection_id not in exclude_connection_ids:
                if self.send_message(connection_id, message):
                    successful_broadcasts += 1

        logger.info(f"Broadcast message to {successful_broadcasts} connections")
        return successful_broadcasts
