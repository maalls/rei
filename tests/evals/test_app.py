import os
from src.config import settings
from dataclasses import replace
from src.factory.factory import Factory

def create_test_app():
    test_settings = create_test_settings()
    factory = Factory(test_settings)
    app = factory.create_langgraph_app()
    app.set_context_reply(thread_id="123", context_reply=True)
    return app

def create_test_message(text,  username="test_user", message_id=234, chat_id=123, chat_type="group", reply_to_message_id=None):
    return {
        "chat_id": chat_id,
        "message_id": message_id,
        "chat_type": chat_type,
        "text": text,
        "from": {
            "username": f"@{username}"
        },
        "reply_to": {
            "message_id": reply_to_message_id
        } if reply_to_message_id else None
    }

def create_test_settings():
    test_file = "var/memory_test.txt"
    pending_requests_file = "var/pending_requests_test.json"
    checkpoint_folder = "var/checkpoints_test"
    test_settings = replace(settings, 
        embeddings_storage_file=test_file, 
        pending_requests_file=pending_requests_file,
        telegram_bot_username="maalls_bot",
        checkpoint_folder=checkpoint_folder
    )
    create_test_memory_file(test_settings.embeddings_storage_file)

    # remove the checkpoint file if it exists
    if os.path.exists(test_settings.checkpoint_folder):
        for file in os.listdir(test_settings.checkpoint_folder):
            file_path = os.path.join(test_settings.checkpoint_folder, file)
            if os.path.isfile(file_path):
                os.remove(file_path)
    return test_settings

def create_test_memory_file(file_path):

    knownledges = '''Malo Yamakado email is dummy@gmail.com
Malo Yamakado phone number is 650-996-1234
Malo Yamakado address is 123 Main St, San Francisco, CA 94105
Malo Yamakado favorite color is blue
Malo Yamakado favorite food is sushi
Jean Dupont favorite food is pizza
Chang Lee favorite food is ramen
'''
    # delete the file if it exists

    if os.path.exists(file_path):
        os.remove(file_path)
    with open(file_path, "w") as f:
        f.write(knownledges)