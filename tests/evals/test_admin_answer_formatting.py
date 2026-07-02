
import pytest
from src.config import settings
from src.factory.factory import Factory


@pytest.mark.evals
def test_admin_answer_formatting():
    admin_reply_handler = Factory(settings).create_admin_reply_handler()
    formatted_admin_answer = admin_reply_handler._format_admin_answer("What is your favorite color?", "My favorite color is blue.")
    print(f"Formatted admin answer: {formatted_admin_answer}")
    assert formatted_admin_answer == "The person's favorite color is blue."

    formatted_admin_answer = admin_reply_handler._format_admin_answer("Quel est la couleur préférée de Malo?", "le bleu.")
    print(f"Formatted admin answer: {formatted_admin_answer}")
    assert formatted_admin_answer == "La couleur préférée de Malo est le bleu."
