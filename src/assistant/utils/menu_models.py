# src/assistant/utils/menu_models.py
from pydantic import BaseModel
from typing import Optional, Dict, Callable, List

class MenuItem(BaseModel):
    title: str
    action: Optional[Callable] = None
    submenu: Optional[Dict[str, 'MenuItem']] = None
    enabled: bool = True
    key_binding: str

    class Config:
        arbitrary_types_allowed = True  # To allow Callable

class SystemPrompt(BaseModel):
    name: str
    prompt_text: str
    is_active: bool = False
    pinned: bool = False

class MenuState(BaseModel):
    current_menu: str = "main"
    breadcrumb: List[str] = []