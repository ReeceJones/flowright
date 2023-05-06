from flowright.config import THEME


_default_attribute_map = {
    'barebones': {
        'container-attributes': {
            'root': {
                'style': 'flex-direction: column; display: flex; flex: 1 1 0'
            },
            'column-container': {
                'style': 'flex-direction: row; display: flex; justify-content: space-between; flex: 1 1 0'
            },
            'column': {
                'style': 'flex-direction: column; display: flex'
            }
        }
    },
    'bootstrap': {
        'preload': [
            '<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha3/dist/css/bootstrap.min.css" rel="stylesheet" integrity="sha384-KK94CHFLLe+nY2dmCWGMq91rCGa5gtU4mk92HdvYe+M/SXH301p5ILy+dN9+nJOZ" crossorigin="anonymous">',
            '<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha3/dist/js/bootstrap.bundle.min.js" integrity="sha384-ENjdO4Dr2bkBIFxQpeoTz1HIcje39Wm4jDKdf19U8gI4ddQ3GYNS7NTKfAdVQSZe" crossorigin="anonymous"></script>'
        ],
        'container-attributes': {
            'root': {
                'class': 'container'
            },
            'column-container': {
                'class': 'row'
            },
            'column': {
                'class': 'col'
            },
            'table': {
                'class': 'table table-hover'
            },
            'table-row': {
                'scope': 'row'
            },
            'table-column': {
                'scope': 'col'
            },
            'checkbox': {
                'class': 'form-check'
            },
            'radio': {
                'class': 'form-check'
            }
        },
        'attributes': {
            'button': {
                'class': 'btn btn-primary'
            },
            'selectbox': {
                'class': 'form-control form-select'
            },
            'textbox': {
                'class': 'form-control'
            },
            'image': {
                'class': 'rounded mx-auto d-block'
            },
            'multiselect': {
                'class': 'form-control form-select'
            },
            'checkbox': {
                'class': 'form-check-input'
            },
            'radio': {
                'class': 'form-check-input'
            }
        }
    }
}


def build_preload() -> str:
    preload = _default_attribute_map[THEME].get('preload')
    if preload is None:
        return ''
    return '\n'.join(preload)


def build_attributes(config_name: str) -> str:
    attr_map = _default_attribute_map[THEME].get('attributes', {}).get(config_name)
    if attr_map is None:
        return ''
    return ' '.join([f'{attr_name}="{attr_value}"' for attr_name, attr_value in attr_map.items()])


def build_container_attributes(config_name: str) -> str:
    attr_map = _default_attribute_map[THEME].get('container-attributes', {}).get(config_name)
    if attr_map is None:
        return ''
    return ' '.join([f'{attr_name}="{attr_value}"' for attr_name, attr_value in attr_map.items()])
