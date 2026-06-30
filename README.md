# rei

Rei aim to be a personal assistant agentic framework to act on your behalf in a telegram group chat.

At the current stage, it behaves like a simple LLM agent where you can include information about yourself in the system prompt.
If it can't reply based on these informations, it's asking you the question in a private channel and transmit back your reply to the user.

## Installation

```
git clone https://github.com/maalls/rei
cd rei

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt

```

Copy the prompts/system.default.md into prompts/system.md and fill it with your own profile informations. 
This is where you store the information about yourself you agree to share.

Copy the .env.example into a .env and insert the parameters.

start the bot
```
(venv)$python -m src.main.py
```

Create or go to your Telegram private chat with your bot, and type:
```
/claim_admin TELEGRAM_ADMIN_PASSWORD
```
replacing TELEGRAM_ADMIN_PASSWORD as defined in your .env file.

The bot will use this chat to forward you questions.



