import json
import logging
import time
from models import MessageTypes

logger = logging.getLogger()

class MessageHandler:
    """
    Processes different types of WebSocket messages and routes them accordingly.
    """

    def __init__(self, connection_manager):
        self.connection_manager = connection_manager

    def process_message(self, connection_id, message_data):
        if not isinstance(message_data, dict):
            logger.error(f"Invalid message format: {message_data}")
            return {'statusCode': 400, 'body': 'Invalid message format'}

        message_type = message_data.get('type')
        data = message_data.get('data', {})

        if not message_type:
            logger.error("Message missing 'type' field")
            return {'statusCode': 400, 'body': 'Message missing type'}

        if message_type == MessageTypes.CHAT:
            return self.handle_chat_message(connection_id, data)

        elif message_type == MessageTypes.JOIN_ROOM:
            return self.handle_join_room(connection_id, data)

        elif message_type == MessageTypes.LEAVE_ROOM:
            return self.handle_leave_room(connection_id, data)

        elif message_type == MessageTypes.PING:
            return self.handle_ping(connection_id)

        else:
            logger.warning(f"Unknown message type: {message_type}")
            return {'statusCode': 400, 'body': f'Unknown message type: {message_type}'}

    def handle_chat_message(self, connection_id, data):
        if not data.get('message'):
            return {'statusCode': 400, 'body': 'Chat message is empty'}

        room_id = data.get('room_id', 'default')
        username = data.get('username', 'Anonymous')
        message_text = data.get('message')

        response = {
            'type': MessageTypes.CHAT,
            'data': {
                'room_id': room_id,
                'username': username,
                'message': message_text,
                'timestamp': int(time.time())
            }
        }

        self.connection_manager.broadcast_message(
            response,
            exclude_connection_ids=[connection_id]
        )

        return {'statusCode': 200, 'body': 'Message sent'}

    def handle_join_room(self, connection_id, data):
        room_id = data.get('room_id')
        username = data.get('username', 'Anonymous')

        if not room_id:
            return {'statusCode': 400, 'body': 'Room ID is required'}

        # Update connection with room information
        # This would typically update the DynamoDB item with room info

        # Notify all
        notification = {
            'type': MessageTypes.SYSTEM,
            'data': {
                'message': f"{username} has joined the room",
                'room_id': room_id,
                'timestamp': int(time.time())
            }
        }

        self.connection_manager.broadcast_message(
            notification,
            exclude_connection_ids=[connection_id]
        )

        return {'statusCode': 200, 'body': 'Joined room'}

    def handle_leave_room(self, connection_id, data):
        room_id = data.get('room_id')
        username = data.get('username', 'Anonymous')

        if not room_id:
            return {'statusCode': 400, 'body': 'Room ID is required'}

        # Update connection to remove from room
        # This would typically update the DynamoDB item

        # Notify all
        notification = {
            'type': MessageTypes.SYSTEM,
            'data': {
                'message': f"{username} has left the room",
                'room_id': room_id,
                'timestamp': int(time.time())
            }
        }

        self.connection_manager.broadcast_message(
            notification,
            exclude_connection_ids=[connection_id]
        )

        return {'statusCode': 200, 'body': 'Left room'}

    def handle_ping(self, connection_id):
        pong_response = {
            'type': MessageTypes.PONG,
            'data': {
                'timestamp': int(time.time())
            }
        }

        self.connection_manager.send_message(connection_id, pong_response)
        return {'statusCode': 200, 'body': 'Pong sent'}

    def handle_custom_route(self, route_key, connection_id, event):
        logger.info(f"Custom route handler for: {route_key}")

        body = event.get('body')
        body_data = {}

        if body:
            try:
                body_data = json.loads(body)
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON in custom route body: {body}")
                return {'statusCode': 400, 'body': 'Invalid JSON'}

        if route_key == 'sendToUser':
            target_user = body_data.get('targetUser')
            message = body_data.get('message')

            if not target_user or not message:
                return {'statusCode': 400, 'body': 'Missing targetUser or message'}

            # Implementation would look up the target user's connection
            # and send the message

            return {'statusCode': 200, 'body': 'Message sent to user'}

        elif route_key == 'sendToRoom':
            room_id = body_data.get('roomId')
            message = body_data.get('message')

            if not room_id or not message:
                return {'statusCode': 400, 'body': 'Missing roomId or message'}

            # Implementation would send the message to all connections in the room

            return {'statusCode': 200, 'body': 'Message sent to room'}

        else:
            logger.warning(f"Unhandled custom route: {route_key}")
            return {'statusCode': 400, 'body': f'Unhandled route: {route_key}'}
