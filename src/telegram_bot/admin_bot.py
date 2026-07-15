from telegram import Bot
from src.agent.admin_agent import AdminAgent
import os
import json
class AdminBot(AdminAgent):
    def __init__(self, bot: Bot, username: str, 
            admin_password: str, pending_request_file: str | None = None) -> None:
        super().__init__()
        self.bot = bot
        self.username = username
        self.admin_password = admin_password
        self.pending_request_file = pending_request_file or "var/pending_request.json"
        self.admin_info_file = "var/admin_info.txt"
        
    async def  request_admin(self, from_channel_id: str, from_message_id: str, text: str):

        print("[request_admin] request_admin", from_channel_id, text)
        chat_id = self.get_admin_chat_id()

        message = await self.send_message(chat_id=chat_id, text=text)
        self.store_pending_request(message_id=message.id, request=text, from_channel_id=from_channel_id, from_message_id=from_message_id)

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
            
    async def send_message(self, chat_id:str, text:str, reply_to_message_id: str | None = None):
        print("[send_message] sending message to chat_id:", chat_id, "text:", text, "reply_to_message_id:", reply_to_message_id)
        return await self.bot.send_message(chat_id=chat_id, text=text, reply_to_message_id=reply_to_message_id)

    def find_pending_request(self, message_id):
        print("[find_pending_request] searching pending request for ", message_id)
        requests = self.get_storage_content()
        for request in requests:
            if request.get("message_id") == message_id:
                return request
        
        return False

    def remove_pending_request(self, message_id):
        requests = self.get_storage_content()
        requests = [item for item in requests if item["message_id"] != message_id]
        self.store_pending_requests(requests)

    def store_pending_request(self, message_id, request, from_channel_id, from_message_id):
        content = self.get_storage_content()
        content.append({
                "message_id": message_id,
                "request": request,
                "reply_to_channel_id": from_channel_id,
                "from_message_id": from_message_id
            })
        self.store_pending_requests(content)

    def get_storage_content(self):
        os.makedirs(os.path.dirname(self.pending_request_file), exist_ok=True)
        if os.path.exists(self.pending_request_file):
            with open(self.pending_request_file, "r") as f:
                raw = f.read().strip()
                content = json.loads(raw) if raw else []
        else:
            content = []
        return content
    
    def store_pending_requests(self, requests: dict):
        with open(self.pending_request_file, "w") as f:
            print("writing request to the pending request file")
            f.writelines(json.dumps(requests, indent=2))

    def store_admin_info(self, chat_id, username, display_name):
        admin_info = {
            "chat_id": chat_id,
            "username": username,
            "display_name": display_name,
        }
        os.makedirs(os.path.dirname(self.admin_info_file), exist_ok=True)
        with open(self.admin_info_file, "w") as f:
            json.dump(admin_info, f)

    def get_admin_info(self):
        if not os.path.exists(self.admin_info_file):
            return None
        
        with open(self.admin_info_file, "r") as f:
            admin_info = json.load(f)
        return admin_info
    
    def get_admin_display_name(self):
        admin_info = self.get_admin_info()
        if not admin_info:
            return None
        return admin_info["display_name"]
    
    def get_admin_username(self):
        admin_info = self.get_admin_info()
        if not admin_info:
            return None
        return admin_info["username"]
   
    def get_admin_chat_id(self):
        admin_info = self.get_admin_info()
        if not admin_info:
            return None
        return admin_info["chat_id"]
        