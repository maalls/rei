# rei

Rei is a personal assistant framework to act on your behalf in a telegram group chat.
If it can't reply, it will ask you what to do in a private channel in order to pursue.

## Installation

```
git clone https://github.com/maalls/rei
cd rei

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt

```

Copy the .env.example into a .env and insert the parameters.

Create or go to your Telegram private chat with your bot, and type:
```
/claim_admin TELEGRAM_ADMIN_PASSWORD
```
replacing TELEGRAM_ADMIN_PASSWORD as defined in your .env file.

The bot will use this chat to forward you questions.

Copy the prompts/system.default.md into prompts/system.md and fill it with your own profile informations. 
This is where you store the information about yourself you agree to share.


