from pydantic import BaseModel, Field


class AssistantMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str = Field(..., min_length=1, max_length=32000)


class EngineeringAssistantChatRequest(BaseModel):
    messages: list[AssistantMessage] = Field(default_factory=list, max_length=50)
    prompt: str = Field(..., min_length=1, max_length=32000)


class EngineeringAssistantChatResponse(BaseModel):
    reply: str
    provider: str
    model: str


class EngineeringAssistantStatusResponse(BaseModel):
    enabled: bool
    configured: bool
    provider: str | None = None
