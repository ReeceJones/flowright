import fire
import subprocess
import os
import webbrowser
import requests
import time
import pathlib
import urllib.parse
import tarfile
import tempfile
import base64

from pydantic import BaseModel

flowright_url = os.environ.get('FLOWRIGHT_URL', 'http://localhost:3000')
flowright_api_url = os.environ.get('FLOWRIGHT_API_URL', 'http://localhost:8090')
flowright_module_location = os.path.dirname(os.path.abspath(__file__))
flowright_data_location = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'flowright_data')

class PackageRequirement(BaseModel):
    name: str
    version: str

def _get_live_packages() -> list[PackageRequirement]:
    result = subprocess.run('pip freeze', shell=True, capture_output=True)
    if result.returncode != 0:
        print("Failed to detect installed packages!")
        exit(1)

    packages = []
    for line in result.stdout.decode('utf-8').strip().split('\n'):
        if len(line) == 0 or line[0] in {'#', '-'}: # skip comments and special directives
            continue
        line_components = line.split('==')
        packages.append(
            PackageRequirement(
                name=line_components[0],
                version=line_components[1]
            )
        )
    return packages

def link(name: str) -> None:
    with open(f'{flowright_data_location}/.token') as f:
        token = f.read()
    query = urllib.parse.quote(f"filter=(name='{name})")
    r = requests.get(
        f"{flowright_api_url}/api/collections/projects/records?{query}",
        headers={
            'Authorization': f'Bearer {token}'
        }
    )
    if not r.ok:
        print(f"Error occurred searching projects: {r.status_code} {r.text}")
        exit(1)

    data = r.json()

    if data['totalItems'] < 1:
        print(f"Project '{name}' not found!")
        exit(1)
    
    project = data['items'][0]

    pathlib.Path('.flowright').mkdir(parents=True, exist_ok=True)
    with open('.flowright/id', 'w') as f:
        f.write(project['id'])
    

def upload(app_dir: str) -> None:
    # get requirements
    with open(f'{flowright_data_location}/.token') as f:
        token = f.read()
    requirements = _get_live_packages()

    # get project id
    with open('.flowright/id', 'r') as f:
        project_id = f.read()

    # create tarball
    with tempfile.TemporaryDirectory() as tmpdir:
        with tarfile.open(os.path.join(tmpdir, 'tmp.tar.gz'), 'w:gz') as tar:
            tar.add(app_dir, arcname='.', filter=lambda x: None if len(x.name) > 2 and '.' == x.name[2] else x)
        # get base64 encoding of tarball
        with open(os.path.join(tmpdir, 'tmp.tar.gz'), 'rb') as f:
            b64tarball = base64.b64encode(f.read()).decode('utf-8')
        r = requests.post(
            f'{flowright_api_url}/api/flowright/upload',
            headers={
                'Authorization': f'Bearer {token}'
            },
            json={
                'project_id': project_id,
                'data': b64tarball,
                'requirements': [r.dict() for r in requirements]
            }
        )

        if not r.ok:
            print(f'Error occurred uploading project: {r.status_code} {r.text}')
            exit(1)
    
    print('Project uploaded successfully!')

def login() -> None:
    # flowright_data_location = os.path.join(__file__, '..', 'flowright_data')
    print(f'Flowright data: {flowright_data_location}')

    r = requests.post(f'{flowright_api_url}/api/flowright/auth_link')
    if not r.ok:
        print('Error occurred creating auth flow!')
        print(r.status_code, r.text)

    challenge = r.json()['id']

    webbrowser.open_new_tab(f'{flowright_url}/link?challenge={challenge}')

    resolved = False
    while not resolved:
        r = requests.get(f'{flowright_api_url}/api/flowright/auth_link/{challenge}')
        if r.ok:
            resolved = True
        time.sleep(1)

    token = r.json()['current_client_jwt']

    pathlib.Path(flowright_data_location).mkdir(parents=True, exist_ok=True)

    with open(os.path.join(flowright_data_location, '.token'), 'w') as f:
        f.write(token)

def serve(app_dir: str, *, reload: bool = False, devreload: bool = False, host: str | None = None, uds: str | None = None) -> None:
    env = os.environ

    # check path is valid
    if not os.path.exists(app_dir) or not os.path.isdir(app_dir):
        print(f'Invalid app directory: {app_dir}')
        exit(1)

    env['FLOWRIGHT_APP_DIR'] = os.path.abspath(app_dir)
    args = ["uvicorn", "--app-dir", flowright_module_location]
    if devreload:
        args.extend(["--reload"])
    if reload:
        env['FLOWRIGHT_RELOAD'] = 'True'
    if host:
        args.extend(["--host", host])
    if uds is not None:
        args.extend(["--uds", uds])

    args.extend(["server:app"]) # TODO

    try:
        subprocess.run(args, env=env)
    except KeyboardInterrupt:
        pass


def run() -> None:
    fire.Fire({
        'login': login,
        'link': link,
        'upload': upload,
        'run': serve
    })
