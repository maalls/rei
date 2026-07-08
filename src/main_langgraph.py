from src.config import settings
from src.factory.factory import Factory
import asyncio
factory = Factory(settings)
app = factory.create_langgraph_app()

async def main():
    while True:
        print("--------------------")
        user_message = input("Message: ")
        result = await app.invoke({
            "chat_id": 123,
            "text": user_message,
            "from": {
                "username": "@maalls"
            }
        })

        print('agent:', result)


if __name__ == "__main__":
    asyncio.run(main())
