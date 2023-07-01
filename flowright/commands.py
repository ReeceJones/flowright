import fire
import subprocess
import os
import webbrowser
import requests
import time
import pathlib

# uvicorn --loop uvloop --reload --app-dir flowright server:app

def login() -> None:
    flowright_url = os.environ.get('FLOWRIGHT_URL', 'http://localhost:3000')
    flowright_api_url = os.environ.get('FLOWRIGHT_API_URL', 'http://localhost:8090')
    # flowright_data_location = os.path.join(__file__, '..', 'flowright_data')
    flowright_data_location = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'flowright_data')
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

def serve(app_dir: str, *, reload: bool = False, devreload: bool = False, uds: str | None = None) -> None:
    env = os.environ

    # check path is valid
    if not os.path.exists(app_dir) or not os.path.isdir(app_dir):
        print(f'Invalid app directory: {app_dir}')
        exit(1)

    env['FLOWRIGHT_APP_DIR'] = os.path.abspath(app_dir)
    args = ["uvicorn", "--app-dir", "flowright"]
    if devreload:
        args.extend(["--reload"])
    if reload:
        env['FLOWRIGHT_RELOAD'] = 'True'
    if uds is not None:
        args.extend(["--uds", uds])

    args.extend(["server:app"])

    try:
        subprocess.run(args, env=env)
    except KeyboardInterrupt:
        pass


def run() -> None:
    fire.Fire({
        'login': login,
        'serve': serve
    })
