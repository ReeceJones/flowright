from pydantic import BaseModel
from typing import Any


class ServerSocketMessage(BaseModel):
    kind: str
    seqno: int


class ComponentUpdateMessage(ServerSocketMessage):
    kind: str = "ComponentUpdateMessage"
    component_id: str
    component_parent: str
    component_data: str


class ComponentRemoveMessage(ServerSocketMessage):
    kind: str = "ComponentRemoveMessage"
    marked_components: list[str]


class IterationStartMessage(ServerSocketMessage):
    kind: str = "IterationStartMessage"
    terminated: bool
    preload_data: str = ''


class IterationCompleteMessage(ServerSocketMessage):
    kind: str = "IterationCompleteMessage"


class ComponentFlushMessage(ServerSocketMessage):
    kind: str = "ComponentFlushMessage"
    component_id: str
    value: Any
    refresh: bool = False
