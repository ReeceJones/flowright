from flowright.client import Component, component, RenderQueue

import contextlib

import markdown as python_markdown

from typing import Any, Generator, Iterable, TypeVar, Generic, Optional, overload, Union, Type


T = TypeVar('T')


@component
class text(Component[None], config_name='text'):
    def __init__(self, content: str) -> None:
        super().__init__(content=content)
        self.content = content

    def render(self) -> str:
        return self.wrap(self.content)


class ColumnContainerComponent(Component[None], config_name='column-container'):
    def __init__(self) -> None:
        super().__init__()

    def render(self) -> str:
        return self.wrap('')


class ColumnComponent(Component[None], config_name='column'):
    def __init__(self) -> None:
        super().__init__()

    def render(self) -> str:
        return self.wrap('')


@component
class divider(Component[None], config_name='divider'):
    def __init__(self) -> None:
        super().__init__()

    def render(self) -> str:
        return self.wrap('<hr>')


@component
class image(Component[None], config_name='image'):
    def __init__(self, image_url: str) -> None:
        super().__init__(image_url=image_url)
        self.image_url = image_url

    def render(self) -> str:
        return self.wrap(f'<img src="{self.image_url}" {self._ATTRIBUTES}>')


class TableComponent(Component[None], config_name='table'):
    def __init__(self) -> None:
        super().__init__()

    def render(self) -> str:
        return self.wrap('', tag='table')


class TableRowComponent(Component[None], config_name='table-row'):
    def __init__(self) -> None:
        super().__init__()
    
    def render(self) -> str:
        return self.wrap('', tag='tr')


class TableColumnComponent(Component[None], config_name='table-column'):
    def __init__(self, header: bool) -> None:
        super().__init__(header=header)
        self.header = header

    def render(self) -> str:
        return self.wrap('', tag='th' if self.header else 'td')


class TableBodyComponent(Component[None], config_name='table-body'):
    def __init__(self) -> None:
        super().__init__()

    def render(self) -> str:
        return self.wrap('', tag='tbody')
    

class TableHeaderComponent(Component[None], config_name='table-header'):
    def __init__(self) -> None:
        super().__init__()

    def render(self) -> str:
        return self.wrap('', tag='thead')


@component
class button(Component[bool], config_name='button'):
    def __init__(self, name: str) -> None:
        super().__init__(name=name)
        self.name = name
        self.value = False

    def render(self) -> str:
        return self.wrap(f'<button onclick="flush_raw(\'{self.id}\', true, true)" {self._ATTRIBUTES}>{self.name}</button>')
    
    def get_value(self) -> bool:
        x = self.value
        self.value = False
        return x
    
    def set_value(self, value: bool) -> None:
        self.value = value


@component
class slider(Component[int], config_name='slider'):
    def __init__(self, min_value: int = 0, max_value: int = 100, step: int = 10) -> None:
        super().__init__(min_value=min_value, max_value=max_value, step=step)
        self.value = min_value
        self.min_value = min_value
        self.max_value = max_value
        self.step = step

    def render(self) -> str:
        return self.wrap(f'<input type="range" min="{self.min_value}" max="{self.max_value}" step="{self.step}" onchange="flush(\'{self.id}\', this.value)" {self._ATTRIBUTES}>')
    
    def get_value(self) -> int:
        return self.value
    
    def set_value(self, value: int) -> None:
        self.value = value


@component
class textbox(Component[str], config_name='textbox'):
    def __init__(self) -> None:
        super().__init__()
        self.value: str = ''

    def render(self) -> str:
        return self.wrap(f'<input type="text" onkeypress="flush(\'{self.id}\', this.value)" onkeyup="flush(\'{self.id}\', this.value)" {self._ATTRIBUTES}>')
    
    def get_value(self) -> str:
        return self.value
    
    def set_value(self, value: str) -> None:
        self.value = value


# @component
class SelectboxComponent(Component[T], config_name='selectbox'):
    def __init__(self, options: Iterable[T]) -> None:
        opts = list(options)
        super().__init__(options=opts)
        self.options = opts
        # self.value = opts[0] if len(opts) > 0 else None
        self.value = None

    def render(self) -> str:
        options = ''.join(['<option></option>'] + [f'<option value="{id(x)}">{x}</option>' for x in self.options])
        return self.wrap(f'<select onchange="flush(\'{self.id}\', this.value)" {self._ATTRIBUTES}>{options}</select>')

    def get_value(self) -> Optional[T]:
        for x in self.options:
            if id(x) == self.value:
                return x
            
        return None
    
    def set_value(self, value: str) -> None:
        self.value = int(value) if value != '' else None


def selectbox(options: Iterable[T]) -> Optional[T]:
    c = SelectboxComponent(options)
    RenderQueue.get_instance().push_child(c)
    return c.get_value()


class MultiSelectboxComponent(Component[list[T]], config_name='multiselect'):
    def __init__(self, options: Iterable[T]) -> None:
        opts = list(options)
        super().__init__(options=opts)
        self.options = opts
        self.values = []

    def render(self) -> str:
        options = ''.join([f'<option value="{id(x)}">{x}</option>' for x in self.options])
        return self.wrap(f'<select multiple onchange="flush(\'{self.id}\', Array.from(this.querySelectorAll(\'option:checked\'),e=>e.value))" {self._ATTRIBUTES}>{options}</select>')

    def get_value(self) -> list[T]:
        selected = []
        for x in self.options:
            if id(x) in self.values:
                selected.append(x)
            
        return selected
    
    def set_value(self, value: str) -> None:
        self.values = [int(x) for x in value if x != '']


def multiselect(options: Iterable[T]) -> list[T]:
    c = MultiSelectboxComponent(options)
    RenderQueue.get_instance().push_child(c)
    return c.get_value()


@component
class checkbox(Component[bool], config_name='checkbox'):
    def __init__(self, text: str, default: bool = False) -> None:
        super().__init__(text=text)
        self.text = text
        self.value = default

    def render(self) -> str:
        check_id = f'{self.id}-checkbox'
        return self.wrap(f'<input type="checkbox" id="{check_id}" {"checked" if self.value else ""} onchange="flush(\'{self.id}\', this.checked)" {self._ATTRIBUTES}><label for="{check_id}">{self.text}</label>')
    
    def get_value(self) -> bool:
        x = self.value
        return x
    
    def set_value(self, value: bool) -> None:
        self.value = value


class RadioComponent(Component[T], config_name='radio'):
    def __init__(self, options: Iterable[T]) -> None:
        opts = list(options)
        super().__init__(options=opts)
        self.options = opts
        self.value = None

    def render(self) -> str:
        radio_name = self.id

        radios = [
            f'<div {self._CONTAINER_ATTRIBUTES}><input {self._ATTRIBUTES} onchange="flush(\'{self.id}\', [{id(x)}, this.checked])" type="radio" name="{radio_name}" id="{id(x)}"><label for="{id(x)}">{x}</label></div>'
            for x in self.options
        ]

        return self.wrap(''.join(radios))
    
    def get_value(self) -> Optional[T]:
        for x in self.options:
            if id(x) == self.value:
                return x

        return None
    
    def set_value(self, value: tuple[int, bool]) -> None:
        if value[1]:
            self.value = value[0]

def radio(options: Iterable[T]) -> Optional[T]:
    c = RadioComponent(options)
    RenderQueue.get_instance().push_child(c)
    return c.get_value()


@contextlib.contextmanager
def column():
    try:
        prev = RenderQueue.get_instance().get_previous()
        if prev is None or not isinstance(prev, ColumnContainerComponent):
            container = ColumnContainerComponent()
            RenderQueue.get_instance().push_child(container)
            RenderQueue.get_instance().push_parent()
        else:
            RenderQueue.get_instance().push_parent()
        c = ColumnComponent()
        RenderQueue.get_instance().push_child(c)
        RenderQueue.get_instance().push_parent()
        yield None
    finally:
        RenderQueue.get_instance().pop_parent() # column
        RenderQueue.get_instance().pop_parent() # container


def table(rows: Iterable[T], header: bool = False) -> Generator[T, None, None]:
    table = TableComponent()
    RenderQueue.get_instance().push_child(table)
    RenderQueue.get_instance().push_parent()
    for i, x in enumerate(rows):
        if i > 0 and isinstance(RenderQueue.get_instance().get_previous(), TableBodyComponent):
            p = RenderQueue.get_instance().get_previous()
        else:
            p = TableHeaderComponent() if header and i == 0 else TableBodyComponent()
            RenderQueue.get_instance().push_child(p)
        RenderQueue.get_instance().push_parent()
        c = TableRowComponent()
        RenderQueue.get_instance().push_child(c)
        RenderQueue.get_instance().push_parent()
        yield x
        RenderQueue.get_instance().pop_parent()
        RenderQueue.get_instance().pop_parent()
    RenderQueue.get_instance().pop_parent()


def columns(cols: Iterable[T], header: bool = False) -> Generator[T, None, None]:
    for i in cols:
        c = TableColumnComponent(header=header)
        RenderQueue.get_instance().push_child(c)
        RenderQueue.get_instance().push_parent()
        yield i
        RenderQueue.get_instance().pop_parent()


@component
class link(Component[None], config_name='link'):
    def __init__(self, text: str, link: str) -> None:
        super().__init__(text=text, link=link)
        self.text = text
        self.link = link

    def render(self) -> str:
        return self.wrap(f'<a href={self.link}>{self.text}</a>')


@component
class markdown(Component[None], config_name='markdown'):
    def __init__(self, text: str) -> None:
        super().__init__(text=text)
        self.text = text

    def render(self) -> str:
        return self.wrap(python_markdown.markdown(self.text, extensions=['fenced_code', 'tables', 'toc', 'smarty', 'codehilite']))


@component
class html(Component[None], config_name='html'):
    def __init__(self, text: str) -> None:
        super().__init__(text=text)
        self.text = text

    def render(self) -> str:
        return self.wrap(self.text)


class TextRenderProcessor:
    def __init__(self, contents: str) -> None:
        self._contents = contents

    def markdown(self) -> None:
        markdown(self._contents)

    def html(self) -> None:
        html(self._contents)


def render(contents: str) -> TextRenderProcessor:
    return TextRenderProcessor(contents)


class OverlayComponent(Component[None], config_name='overlay'):
    def __init__(self):
        super().__init__()

    def render(self) -> str:
        return self.wrap('')


class DialogComponent(Component[None], config_name='dialog'):
    def __init__(self):
        super().__init__()
    
    def render(self) -> str:
        return self.wrap('', tag='dialog')
    

@contextlib.contextmanager
def dialog():
    try:
        o = OverlayComponent()
        d = DialogComponent()
        RenderQueue.get_instance().push_child(o)
        RenderQueue.get_instance().push_parent()
        RenderQueue.get_instance().push_child(d)
        RenderQueue.get_instance().push_parent()
        yield None
    finally:
        RenderQueue.get_instance().pop_parent()
        RenderQueue.get_instance().pop_parent()
