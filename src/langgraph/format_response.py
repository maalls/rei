import json
import time
from datetime import date
def format_response(messages, response, from_username):
    previous_content = json.loads(messages[-1].content)
    content = {
        "chat_id": previous_content["chat_id"],
        "text": response.content,
        "from": {
            "username": from_username
        },
        "date": date.today().isoformat(),
        "timestamp": int(time.time())
    }
    return {
        'role': 'assistant',
        'content': json.dumps(content)
    }