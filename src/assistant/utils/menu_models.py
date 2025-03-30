# src/assistant/utils/menu_models.py

from pydantic import BaseModel
from typing import Optional, Dict, Callable, List, Union
from src.models.models import SystemPrompt, ModelSettings  # Import the consolidated SystemPrompt model

class MenuItem(BaseModel):
    title: str
    action: Optional[Callable] = None
    submenu: Optional[Union[Dict[str, 'MenuItem'], Dict[str, dict]]] = None
    enabled: bool = True
    key_binding: str

    class Config:
        arbitrary_types_allowed = True

class MenuState(BaseModel):
    current_menu: str = "main"
    breadcrumb: List[str] = []