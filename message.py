import json

class ENVOI_TYPE:
    TEXT = "ENVOI_TEXT"
    IMAGE = "ENVOI_IMAGE"
    AUDIO = "ENVOI_AUDIO"
    VIDEO = "ENVOI_VIDEO"
    SENSOR = "ENVOI_SENSOR"
    CLIENT_LIST = "ENVOI_CLIENT_LIST"

 

class RECEPTION_TYPE:
    TEXT = "RECEPTION_TEXT"
    IMAGE = "RECEPTION_IMAGE"
    AUDIO = "RECEPTION_AUDIO"
    VIDEO = "RECEPTION_VIDEO"
    SENSOR = "RECEPTION_SENSOR"
    CLIENT_LIST = "RECEPTION_CLIENT_LIST"

 

class ADMIN_TYPE:
    ROUTING_LOG = "ADMIN_ROUTING_LOG"
    CLIENT_CONNECTED = "ADMIN_CLIENT_CONNECTED"
    CLIENT_DISCONNECTED = "ADMIN_CLIENT_DISCONNECTED"
    CLIENT_LIST_FULL = "ADMIN_CLIENT_LIST_FULL"

 

class SensorId:
    LIGHT = "LIGHT"
    BUTTON = "BUTTON"
    JOYSTICK = "JOYSTICK"
    TEMPERATURE = "TEMPERATURE"
    RFID = "RFID"
    LED = "LED"
    ACCELEROMETER = "ACCELEROMETER"

 

class MessageType:
    DECLARATION = "DECLARATION"
    ENVOI = ENVOI_TYPE
    RECEPTION = RECEPTION_TYPE
    WARNING = "WARNING"
    SYS_MESSAGE = "SYS_MESSAGE"
    ADMIN = ADMIN_TYPE

 

class Message:
    def __init__(self, message_type: MessageType, value, emitter, receiver=None, sensor_id=None):
        self.message_type = message_type
        self.value = value
        self.emitter = emitter
        self.receiver = receiver
        self.sensor_id = sensor_id

 

    @staticmethod
    def default_message():
        return Message(MessageType.DECLARATION, "System", "This is a default message", "All")

 

    @staticmethod
    def reception(emitter, value, receiver):
        return Message(MessageType.RECEPTION.TEXT, value, emitter, receiver)

 

    @staticmethod
    def reception_image(emitter, value, receiver):
        return Message(MessageType.RECEPTION.IMAGE, value, emitter, receiver)

 

    @staticmethod
    def reception_audio(emitter, value, receiver):
        return Message(MessageType.RECEPTION.AUDIO, value, emitter, receiver)

 

    @staticmethod
    def reception_video(emitter, value, receiver):
        return Message(MessageType.RECEPTION.VIDEO, value, emitter, receiver)

 

    @staticmethod
    def warning(emitter, value, receiver):
        return Message(MessageType.WARNING, value, emitter, receiver)

 

    @staticmethod
    def sys_message(emitter, value, receiver):
        return Message(MessageType.SYS_MESSAGE, value, emitter, receiver)

 

    @staticmethod
    def ping():
        return Message(MessageType.SYS_MESSAGE, "ping", "SERVER", "")

 

    @staticmethod
    def sensor(emitter, sensor_id, value, receiver):
        return Message(MessageType.ENVOI.SENSOR, value, emitter, receiver, sensor_id)

 

    @staticmethod
    def from_json(json_data):
        data = json.loads(json_data)
        message_type = data['message_type']
        emitter = data['data']['emitter']
        receiver = data['data'].get('receiver', None)
        value = data['data']['value']
        sensor_id = data['data'].get('sensor_id', None)
        return Message(message_type, value, emitter, receiver, sensor_id)

 

    def to_json(self):
        data = {
            'message_type': self.message_type,
            'data': {
                'emitter': self.emitter,
                'receiver': self.receiver,
                'value': self.value
            }
        }
        if self.sensor_id:
            data['data']['sensor_id'] = self.sensor_id

 

        return json.dumps(data)

