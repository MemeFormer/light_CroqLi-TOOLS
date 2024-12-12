# src/models/models.py
from pydantic import BaseModel, Field
from enum import Enum
import uuid
from typing import List, Optional
from sqlalchemy import Column, String, Boolean, Integer, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class ShellAndOS(BaseModel):
    shell: str
    os: str

class LLMModelParams(BaseModel):
    model_name: str = "llama3-70b-8192"
    max_tokens: int
    temperature: float
    top_p: float

    class Config:
        protected_namespaces = ()

class ChatMessage(BaseModel):
    role: str
    content: str

class ToolCall(BaseModel):
    tool_calls: Optional[List[dict]] = None
    input: Optional[str] = None

class CommandResult(BaseModel):
    stdout: str
    stderr: str
    exit_code: int

class HelpfulTip(BaseModel):
    explanation: str
    suggestion: str
    additional_info: str

class ModelSettings(BaseModel):
    model_name: str
    max_tokens: int
    temperature: float
    top_p: float

    class Config:
        protected_namespaces = ()

class APIKeys(BaseModel):
    groq_api_key: str

class AtuinHistoryEntry(BaseModel):
    command: str
    timestamp: int 
    
# New consolidated PromptPriority enum
class PromptPriority(str, Enum):
    NORMAL = "normal"
    HIGH = "high"
    LOW = "low"

# Base Pydantic model for system prompts
class BaseSystemPrompt(BaseModel):
    name: str
    is_active: bool = False

    class Config:
        from_attributes = True

# Specific Pydantic models for different types of prompts
class ChatSystemPrompt(BaseSystemPrompt):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    content: str
    priority: PromptPriority = PromptPriority.NORMAL
    display_index: int = 0

    class Config:
        from_attributes = True

class MenuSystemPrompt(BaseSystemPrompt):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    prompt_text: str
    priority: int = 0  # 0 for unpinned, 1 for pinned
    is_active: bool = False
    display_index: int = 0

    class Config:
        from_attributes = True

# SQLAlchemy models for database storage
class BaseSystemPromptModel(Base):
    __tablename__ = 'base_system_prompts'
    __abstract__ = True
    
    name = Column(String, nullable=False)
    is_active = Column(Boolean, default=False)

class ChatSystemPromptModel(BaseSystemPromptModel):
    __tablename__ = 'chat_system_prompts'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    content = Column(String, nullable=False)
    priority = Column(SQLEnum(PromptPriority), default=PromptPriority.NORMAL)
    display_index = Column(Integer, default=0)

class MenuSystemPromptModel(BaseSystemPromptModel):
    __tablename__ = 'menu_system_prompts'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    prompt_text = Column(String, nullable=False)
    pinned = Column(Boolean, default=False)


