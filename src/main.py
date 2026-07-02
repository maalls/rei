from src.config import settings
from src.factory.factory import Factory

def main() -> None:
    factory = Factory(settings)
    bot = factory.create_group_bot()
    try:
        bot.run()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()