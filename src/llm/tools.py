import string


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

TRANSMIT_REQUEST_TOOL = {
    "type": "function",
    "function": {
        "name": "transmit_request",
        "description": "Use this tool to transmit a request to a person. "
            "You should use this tool if you don't know the answer to a question regarding a person. "
            "You should also use this tool if the user asks you to transmit a request to a person. "
            "Always use the profile tool to get the person's profile information before transmitting a request if you don't know the answer."
            "You should not use this tool if you know the answer to the question. "
            "Do not make up the answer. If you don't know the answer, transmit the request to the person and wait for their response. "
            "Do not make up any details. Just say that you transmitted the information and don't fabricate any details. "
            "For example, if the user user asks Alice email address, and you don't know it, you should use the profile tool to get Alice's email address. "
            "If the profile tool doesn't have Alice's email address, you should use this tool to transmit the request to Alice and wait for her response.",
        "parameters": {
            "type": "object",
            "properties": {
                "person": {
                    "type": "string",
                    "description": "The name of the person to whom the request is being transmitted."
                },
                "details": {
                    "type": "string",
                    "description": "The details of the request."
                },
            },
        },
    },
}

PROFILE_TOOL = {
    "type": "function",
    "function": {
        "name": "search_profile",
        "description": (
            "Use this tool whenever the user asks about a person's profile, "
            "identity, contact information, preferences, biography, personal details, "
            "or says things like 'check his profile', 'look in her profile', "
            "'what do you know about Malo', 'search his profile'. "
            "Always call this tool before claiming you do not know."
                ),
        "parameters": {
            "type": "object",
            "properties": {
                "person": {
                    "type": "string",
                    "description": "The name of the person whose profile information is being requested."
                },
                "query": {
                    "type": "string",
                    "description": "The description of the information requested."
                }
            }
        },
    },
}

CALENDAR_AVAILABILITY_TOOL = {
    "type": "function",
    "function": {
        "name": "calendar_availability",
        "description": "Use this tool to check calendar availability over the given user. Do not assume the requested time or duration. Always ask the user for the required information.",
        "parameters": {
            "type": "object",
            "properties": {
                "person": {
                    "type": "string",
                    "description": "The name of the person whose calendar availability is being checked."
                },
                "date": {
                    "type": "string",
                    "description": "The date for which the availability is being checked in YYYY-MM-DD format."
                },
                "start_time": {
                    "type": "string",
                    "description": "The start time of the availability check in ISO 8601 format."
                },
                "duration": {
                    "type": "string",
                    "description": "The duration for which the availability is being checked, in ISO 8601 duration format."
                },
                
            },
        },
        "required": ["person", "date", "start_time", "duration"],
    },
}


def get_tools() -> list[dict]:
    return [
        AIAIAI_TOOL,
        CALENDAR_AVAILABILITY_TOOL,
        PROFILE_TOOL,
        TRANSMIT_REQUEST_TOOL
    ]