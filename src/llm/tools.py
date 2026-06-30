AIAIAI_TOOL = {
    "type": "function",
    "function": {
        "name": "aiaiai",
        "description": "Use this tool when user says 'Chiki chiki'.",
        "parameters": {
            "type": "object",
            "properties": {},
        },
    },
}


def get_tools() -> list[dict]:
    return [
        AIAIAI_TOOL,
    ]