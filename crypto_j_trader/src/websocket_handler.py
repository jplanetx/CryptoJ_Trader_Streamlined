class WebsocketHandler:
    def __init__(self):
        # ...existing code...
        self.connected = False  # initialize connection state

    async def connect(self):
        # ...existing connect logic...
        self.connected = True

    async def disconnect(self):
        # ...existing disconnect logic...
        self.connected = False

    async def send_message(self, message: str):
        if not self.connected:
            raise ConnectionError("Not connected")
        # ...existing code to send message...
