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
            "Do not make up any details. Just say that you transmitted the information and don't fabricate any details.",
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
        "name": "profile",
        "description": "Use this tool when user requests profile information about a person, such as email, phone number, address, favorite color etc. "
        "Anything related to the person's profile. "
        "If the information is not available, transmit the request to the person using the transmit_request tool. "
        "Do not make up the requested information. "
        "Just say that you transmitted the information and don't fabricate any details.",
        "parameters": {
            "type": "object",
            "properties": {
                "person": {
                    "type": "string",
                    "description": "The name of the person whose profile information is being requested."
                },
                "label": {
                    "type": "string",
                    "description": "The label of the information requested, such as 'email', 'phone number', 'address', etc."
                },
                "details": {
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