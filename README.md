# rei

Rei aim to be a personal assistant agentic framework to act on your behalf in a telegram group chat.

Currently it has a rag memory that it loads from var/memory.txt
If someone request is not available in the memory, the agent will propose to forward the request to you in your private telegram chat so you can reply. The memory will be updated and the answer forwarded back to the person.


## Installation

create a telegram bot:
https://www.youtube.com/watch?v=vZtm1wuA2yc

Disable group privacy otherwise the bot wont be able to be included in a group.
And also enable "Bot to Bot communication" otherwise the bot won't see messages from other bots in the group.

Project installation:

```
git clone https://github.com/maalls/rei
cd rei

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt

```

Copy the .env.example into a .env and insert the parameters.

start the bot
```
(venv)$python -m src.main.py
```

Create or go to your Telegram private chat with your bot, and type:
```
/claim TELEGRAM_ADMIN_PASSWORD
```
replacing TELEGRAM_ADMIN_PASSWORD as defined in your .env file.

The bot will use this chat to forward you questions.

## memory
memories are store by default in var/memory.txt
each line has one fact (ex: John likes apple)
memories are loaded when the app starts and updated when bot interacts with you.


