from src.config import settings
from src.factory.factory import Factory

factory = Factory(settings)
app = factory.create_langgraph_app()

while True:
    user_message = input("Message: ")
    result = app.invoke(user_message)

    print(result)


