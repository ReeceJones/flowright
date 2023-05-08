from flowright.config import THEME


_default_attribute_map = {
    'barebones': {
        'components': {
            'root': {
                'container-attributes': {
                    'style': 'flex-direction: column; display: flex; flex: 1 1 0'
                }
            },
            'column-container': {
                'container-attributes': {
                    'style': 'flex-direction: row; display: flex; justify-content: space-between; flex: 1 1 0'
                }
            },
            'column': {
                'container-attributes': {
                    'style': 'flex-direction: column; display: flex'
                }
            }
        }
    },
    'bootstrap': {
        'preload': [
            '<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha3/dist/css/bootstrap.min.css" rel="stylesheet" integrity="sha384-KK94CHFLLe+nY2dmCWGMq91rCGa5gtU4mk92HdvYe+M/SXH301p5ILy+dN9+nJOZ" crossorigin="anonymous">',
            '<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha3/dist/js/bootstrap.bundle.min.js" integrity="sha384-ENjdO4Dr2bkBIFxQpeoTz1HIcje39Wm4jDKdf19U8gI4ddQ3GYNS7NTKfAdVQSZe" crossorigin="anonymous"></script>'
        ],
        'components': {
            'root': {
                'container-attributes': {
                    'class': 'container'
                }
            },
            'column-container': {
                'container-attributes': {
                    'class': 'row'
                }
            },
            'column': {
                'container-attributes': {
                    'class': 'col'
                }
            },
            'table': {
                'container-attributes': {
                    'class': 'table table-hover'
                }
            },
            'table-row': {
                'container-attributes': {
                    'scope': 'row'
                }
            },
            'table-column': {
                'container-attributes': {
                    'scope': 'col'
                }
            },
            'checkbox': {
                'container-attributes': {
                    'class': 'form-check'
                },
                'attributes': {
                    'class': 'form-check-input'
                }
            },
            'radio': {
                'container-attributes': {
                    'class': 'form-check'
                },
                'attributes': {
                    'class': 'form-check-input'
                }
            },
            'button': {
                'attributes': {
                    'class': 'btn btn-primary'
                }
            },
            'selectbox': {
                'attributes': {
                    'class': 'form-control form-select'
                }
            },
            'textbox': {
                'attributes': {
                    'class': 'form-control'
                }
            },
            'image': {
                'attributes': {
                    'class': 'rounded mx-auto d-block'
                }
            },
            'multiselect': {
                'attributes': {
                    'class': 'form-control form-select'
                }
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
    attr_map = _default_attribute_map[THEME].get('components', {}).get(config_name, {}).get('attributes')
    if attr_map is None:
        return ''
    return ' '.join([f'{attr_name}="{attr_value}"' for attr_name, attr_value in attr_map.items()])


def build_container_attributes(config_name: str) -> str:
    attr_map = _default_attribute_map[THEME].get('components', {}).get(config_name, {}).get('container-attributes')
    if attr_map is None:
        return ''
    return ' '.join([f'{attr_name}="{attr_value}"' for attr_name, attr_value in attr_map.items()])
