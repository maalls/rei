from openai import APIError, OpenAI
import json
import os
class LLMService:
    def __init__(
        self,
        client: OpenAI,
        model: str,
        history_file: str | None = None,
        system_prompt: str | None = None,
    ):
        self.client = client
        self.model = model
        self.history_file = history_file
        self.system_prompt = system_prompt

    def chat(self, user_message: str):

        messages = []
        if self.history_file:
            if not os.path.exists(self.history_file):
                print(f"History file {self.history_file} does not exist. Creating a new one.")
                with open(self.history_file, "w", encoding="utf-8") as f:
                    json.dump([], f, indent=2)
                messages.append({"role": "system", "content": self.system_prompt})
            try:
                with open(self.history_file, "r", encoding="utf-8") as f:
                    history = json.load(f)
            except FileNotFoundError:
                raise FileNotFoundError(f"History file {self.history_file} not found.")
            except json.JSONDecodeError:
                raise ValueError(f"History file {self.history_file} is not a valid JSON file.")
            
            messages.extend(history)
        else:
            messages.append({"role": "system", "content": self.system_prompt})
        
        messages.append({"role": "user", "content": user_message})

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=[
                    {
                        "type": "function",
                        "function": {
                            "name": "ask_human",
                            "description": (
                                "Ask Malo a question and wait for his answer. "
                                "Use this tool only when the user asks for information "
                                "that Malo can know and that you don't already know."
                                "If you already know the answer, do not use this tool."
                            ),
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "question": {
                                        "type": "string",
                                    }
                                },
                                "required": ["question"],
                            },
                        },
                    },
                    {
                        "type": "function",
                        "function": {
                            "name": "aiaiai",
                            "description": (
                                "Use this tool when user says 'chikachika'"
                            )
                        },
                    }
                ],
            )
            # display indented formatted JSON response for debugging
            message = response.choices[0].message

            messages.append({"role": message.role, "content": message.content})

            if self.history_file:
                with open(self.history_file, "w", encoding="utf-8") as f:
                    json.dump(messages, f, indent=2)

            
            #print("LLM response:", json.dumps(response.choices[0].message.model_dump(), indent=2))
            return message

        except APIError as error:
            print(f"LLM API error: {error}")
            return None