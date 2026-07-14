
from pydantic.v1 import BaseModel

class Response(BaseModel):
    content: str | None
   