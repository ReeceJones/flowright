from flowright.messages import ComponentFlushMessage, ComponentRemoveMessage, ComponentUpdateMessage, IterationCompleteMessage, IterationStartMessage, PageRedirectMessage
from flowright.customization import build_attributes, build_container_attributes
from flowright.config import FIFO_POLL_DELAY

import abc
import functools
import uuid
import os
import copy
import json
import time
import urllib.parse

from typing import Generic, Any, Callable, TypeVar, ParamSpec, Optional, Generator


T = TypeVar('T')
P = ParamSpec('P')


class Component(abc.ABC, Generic[T]):
    _CONTAINER_ATTRIBUTES = ''
    _ATTRIBUTES = ''
    _CONFIG_NAME = ''

    def __init__(self, **signature: Any) -> None:
        self.kind = self.__class__.__name__
        self.id = f"{self._CONFIG_NAME}-{uuid.uuid4().hex[:10]}"
        self._signature = signature
    
    def __init_subclass__(cls, config_name: str) -> None:
        cls._CONFIG_NAME = config_name
        cls._CONTAINER_ATTRIBUTES = build_container_attributes(config_name)
        cls._ATTRIBUTES = build_attributes(config_name)

    def __repr__(self) -> str:
        return f"{self.kind}({self._signature})"

    def __eq__(self, __value: object) -> bool:
        if not isinstance(__value, Component):
            return False

        return __value.kind == self.kind and __value._signature == self._signature

    def render(self) -> str:
        raise NotImplementedError()
    
    def wrap(self, content: str, *, no_attr: bool = False, tag: str = 'div') -> str:
        # style_args = "; ".join([f"{k}: {v}" for k, v in style.items()])
        return f"<{tag} id=\"{self.id}\" {self._CONTAINER_ATTRIBUTES if not no_attr else ''}>{content}</{tag}>"

    def get_value(self) -> T:
        """
        Get the value of the component. Used for inputs. You may assume this method is called exactly once during rendering.
        """
        raise NotImplementedError()

    def set_value(self, value: str) -> None:
        """
        Set the value of the component. Used for inputs.
        """
        raise NotImplementedError()
    
def component(cls: Callable[P, Component[T]]) -> Callable[P, T]:
    def stub_type() -> Any:
        pass
    @functools.wraps(cls)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        c = cls(*args, **kwargs)
        RenderQueue.get_instance().push_child(c)
        try:
            x = c.get_value()
            return x
        except NotImplementedError:
            return stub_type()
    return wrapper


class RootComponent(Component, config_name='root'):
    def __init__(self) -> None:
        super().__init__()

    def render(self) -> str:
        return self.wrap('')

class RenderTree:
    def __init__(self, component: Component) -> None:
        self.component = component
        self.parent: Optional["RenderTree"] = None
        self.children: list["RenderTree"] = []

    def __repr__(self) -> str:
        return '\n'.join([repr(self.component)] + (['\n'.join(['    ' + y for x in self.children for y in repr(x).split('\n')])] if len(self.children) > 0 else []))

    @property
    def parent_id(self) -> str:
        return "root" if self.parent is None else self.parent.component.id

    def push_child(self, component: Component) -> "RenderTree":
        node = RenderTree(component)
        node.parent = self
        self.children.append(node)
        return self

    def push_parent(self, i: int = -1) -> "RenderTree":
        return self.children[i]

    def pop_parent(self) -> Optional["RenderTree"]:
        if self.parent is None:
            return None
        return self.parent

    def dfs(self) -> Generator["RenderTree", None, None]:
        yield self
        for child in self.children:
            yield from child.dfs()

class RenderQueue:
    _instance: Optional['RenderQueue'] = None

    def __init__(self) -> None:
        server_fifo = os.getenv('SERVER_FIFO')
        if server_fifo is not None:
            self.server = open(server_fifo, 'w')
        else:
            self.server = None

        client_fifo = os.getenv('CLIENT_FIFO')
        if client_fifo is not None:
            self.client = open(client_fifo, 'r')
        else:
            self.client = None

        self.values: dict[str, Any] = {}
        self.force_refresh = True

        self.tree_pointer: Optional[RenderTree] = None
        self.shadow_tree_pointer: Optional[RenderTree] = None
        self.hard_reset()

    @classmethod
    def get_instance(cls) -> 'RenderQueue':
        if cls._instance is None:
            cls._instance = RenderQueue()
        return cls._instance

    def reset(self) -> None:
        if self.tree_pointer is not None:
            self.shadow_tree_pointer = self.tree_pointer
            while self.shadow_tree_pointer.parent is not None:
                self.shadow_tree_pointer = self.shadow_tree_pointer.parent
        self.tree_pointer = None

        self.push_child(RootComponent())

    def hard_reset(self) -> None:
        self.force_refresh = True
        self.tree_pointer = None
        self.shadow_tree_pointer = None
        self.values: dict[str, Any] = {}

    def send_message(self, msg: str) -> None:
        if self.server is not None:
            self.server.write(f'{msg}\n')
            self.server.flush()
        else:
            raise RuntimeError("Server pipe not created")

    def recv_message(self) -> IterationStartMessage:
        if self.client is not None and self.server is not None:
            self.send_message(IterationCompleteMessage(force_refresh=self.force_refresh).json())
            self.force_refresh = False
            msg = self.client.readline()
            obj = {} if len(msg.strip()) == 0 else json.loads(msg)
            while obj.get('kind') != 'IterationStartMessage':
                if obj.get('kind') == 'ComponentFlushMessage':
                    flush_msg = ComponentFlushMessage(**obj)
                    # print(flush_msg)
                    self.values[flush_msg.component_id] = flush_msg.value
                msg = self.client.readline()
                if len(msg.strip()) == 0:
                    time.sleep(FIFO_POLL_DELAY)
                    continue
                obj = json.loads(msg)
            start = IterationStartMessage.parse_obj(obj)
            # print(start)
            self.send_message(start.json())
            return start
        else:
            raise RuntimeError("Communication pipes not created")

    def _update_component(self, component: Component, parent: str = "root") -> None:
        self.send_message(ComponentUpdateMessage(
            component_id=component.id,
            component_parent=parent,
            component_data=component.render()
        ).json())

    def _remove_components(self, components: list[Component]) -> None:
        for comp in components:
            if comp.id in self.values:
                del self.values[comp.id]
        self.send_message(ComponentRemoveMessage(
            marked_components=[x.id for x in components]
        ).json())

    def push_child(self, component: Component) -> None:
        if self.tree_pointer is None or self.shadow_tree_pointer is None:
            if self.shadow_tree_pointer is not None:
                # component.id = self.shadow_tree_pointer.component.id
                component.__dict__ = copy.deepcopy(self.shadow_tree_pointer.component.__dict__)
            self.tree_pointer = RenderTree(component)
            if self.shadow_tree_pointer is None:
                self._update_component(component)
                self.shadow_tree_pointer = copy.deepcopy(self.tree_pointer)
        elif len(self.shadow_tree_pointer.children) == len(self.tree_pointer.children) or (len(self.shadow_tree_pointer.children) > len(self.tree_pointer.children) and self.shadow_tree_pointer.children[len(self.tree_pointer.children)].component != component):
            # re-render and update shadow tree pointer and root
            self.tree_pointer.push_child(component)
            remove = [x.component for x in self.shadow_tree_pointer.children[len(self.tree_pointer.children)-1:]]
            if len(remove) > 0:
                self._remove_components(remove)
                self.shadow_tree_pointer.children = self.shadow_tree_pointer.children[:-len(remove)]
            self.shadow_tree_pointer.push_child(component)
            self._update_component(component, self.tree_pointer.component.id)
        else:
            tail = self.shadow_tree_pointer.children[len(self.tree_pointer.children)]
            # component.id = tail.component.id
            component.__dict__ = copy.deepcopy(tail.component.__dict__)
            self.tree_pointer.push_child(component)
        
        # handle value submission
        if component.id in self.values:
            component.set_value(self.values[component.id])
            del self.values[component.id]
            
    def prune_terminal(self, shadow_pointer: Optional[RenderTree], tree_pointer: Optional[RenderTree]) -> None:
        if shadow_pointer is None or tree_pointer is None:
            return
        
        # if previous shadow RenderTree has more children than previous RenderTree
        if len(tree_pointer.children) > 1:
            # there may be children that are parents, but were not the previous tree
            for prev_shadow, prev in zip(shadow_pointer.children[:-1], tree_pointer.children[:-1]):
                self.prune(prev_shadow, prev)

    def prune(self, shadow_pointer: RenderTree, tree_pointer: RenderTree) -> None:
        # print(len(shadow_pointer.children), len(tree_pointer.children))
        if len(shadow_pointer.children) > len(tree_pointer.children):
            remove = [x.component for x in shadow_pointer.children[len(tree_pointer.children):]]
            self._remove_components(remove)
            shadow_pointer.children = shadow_pointer.children[:len(tree_pointer.children)]

        # recurse on nested trees that may not have seen a push_parent
        for x, y in zip(shadow_pointer.children, tree_pointer.children):
            self.prune(x, y)

    def push_parent(self) -> None:
        self.prune_terminal(self.shadow_tree_pointer, self.tree_pointer)
        if self.shadow_tree_pointer is None or self.tree_pointer is None:
            raise RuntimeError("Missing root component")
        # apply push
        self.shadow_tree_pointer = self.shadow_tree_pointer.push_parent(len(self.tree_pointer.children)-1)
        self.tree_pointer = self.tree_pointer.push_parent()

    def get_parent(self) -> Optional[Component]:
        if self.tree_pointer is None:
            return None
        parent_pointer = self.tree_pointer.parent
        return None if parent_pointer is None else parent_pointer.component
    
    def pop_parent(self) -> None:
        if self.tree_pointer is None or self.shadow_tree_pointer is None:
            raise RuntimeError("Called pop_parent() when no root component exists.")

        new_pointer = self.tree_pointer.pop_parent()
        if new_pointer is None:
            raise RuntimeError("Called pop_parent() when no parent exists.")
        self.tree_pointer = new_pointer
        self.shadow_tree_pointer = self.shadow_tree_pointer.pop_parent()

    def get_previous(self, node: Optional[RenderTree] = None) -> Optional[Component]:
        parent_pointer = self.tree_pointer if node is None else node
        if parent_pointer is None:
            return None
        if len(parent_pointer.children) < 1:
            return None
        return parent_pointer.children[-1].component


def get_redirect(path: str, params: Optional[dict[str, Any]] = None) -> str:
    if params is None or len(params) == 0:
        return urllib.parse.quote(f'/{path}')
    return f'/{urllib.parse.quote(path)}?' + '&'.join(f'{urllib.parse.quote(k)}={urllib.parse.quote(json.dumps(v))}' for k, v in params.items())


def redirect(path: str, params: Optional[dict[str, Any]] = None) -> None:
    redirect_url = get_redirect(path, params)
    RenderQueue.get_instance().send_message(PageRedirectMessage(url=redirect_url).json())


def running() -> bool:
    msg = RenderQueue.get_instance().recv_message()
    if msg.terminated:
        return False
    RenderQueue.get_instance().reset()
    return True

def get_params() -> dict[str, Any]:
    return json.loads(os.getenv('PARAMS', '{}'))


def refresh() -> None:
    RenderQueue().get_instance().force_refresh = True
