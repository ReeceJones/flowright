import argparse
import subprocess
import os

# uvicorn --loop uvloop --reload --app-dir flowright server:app

def run() -> None:
    parse_args = argparse.ArgumentParser()
    parse_args.add_argument("--reload", action="store_true", default=False, help='Automatically reload the page when a change is detected in the app.')
    parse_args.add_argument("--dev-reload", action="store_true", default=False, help='Automatically reload the webserver when a change is detected in the library.')
    parse_args.add_argument("app_dir", default='.')

    server_args = parse_args.parse_args()
    env = os.environ


    args = ["uvicorn", "--app-dir", "flowright"]
    if server_args.dev_reload:
        args.extend(["--reload"])
    if server_args.reload:
        env['FLOWRIGHT_RELOAD'] = 'True'
    args.extend(["server:app"])
    print(args)

    try:
        subprocess.run(args, env=env)
    except KeyboardInterrupt:
        pass
