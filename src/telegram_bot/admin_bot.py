from telegram import Bot
import os
import json
class AdminBot():
    def __init__(self, bot: Bot, username: str, 
            admin_password: str,):
        self.bot = bot
        self.username = username
        self.admin_password = admin_password
        self.pending_request_file = "var/pending_request.json"
        
        

    async def  request_admin(self, from_channel_id: str, text: str):

        chat_id = self.get_admin_chat_id()

        message = await self.send_message(chat_id=chat_id, text=text)
        self.store_pending_request(message_id=message.id, from_id=from_channel_id)

    async def review_pending_request(self, message):

        chat_id = message["chat_id"]
        admin_chat_id = self.get_admin_chat_id()
        if(chat_id != admin_chat_id):
            print("message is not from admin chat")
            return False
        
        pending_request = self.find_pending_request(message["message_id"])
        if pending_request:
            chat_id = pending_request["chat_id"]
            text = message.text
            
            message = await self.send_message(chat_id=chat_id, text=text)
            self.remove_pending_request(message["message_id"])
            

    async def send_message(self, chat_id:str, text:str):
        return await self.bot.send_message(chat_id=chat_id, text=text)

    def find_pending_request(self, message_id):
        pass

    def remove_pending_request(self, message_id):
        pass

    def store_pending_request(self, message_id, from_id):
        os.makedirs(os.path.dirname(self.pending_request_file), exist_ok=True)
        if os.path.exists(self.pending_request_file):
            with open(self.pending_request_file, "r") as f:
                raw = f.read().strip()
                content = json.loads(raw) if raw else []
        else:
            content = []

        with open(self.pending_request_file, "w") as f:
            content.append({
                "message_id": message_id,
                "reply_to_channel_id": from_id
            })
            print("writing request to the pending request file")
            f.writelines(json.dumps(content, indent=2))

    
    def get_admin_chat_id(self):
        id_file_path = "var/admin_chat_id.txt"
        with open(id_file_path, "r") as f:
            chat_id = str(f.readline())

        if not chat_id:
            raise ValueError("chat id is not defined.")
        