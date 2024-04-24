import argparse
import os


CONSTANTS_GEN = {
    'server': """
from const import load_vars

load_vars(
    database_type='{database_type}',
    database_host='{database_host}',
    database_port='{database_port}',
    mongo_database_name='{mongo_database_name}',
    mongo_collection_name='{mongo_collection_name}',
    firebase_collection_name='{firebase_collection_name}',
    firebase_credentials_name='{firebase_credentials_name}',
    mongo_user='{mongo_user}',
    mongo_pass='{mongo_pass}'
)
"""
}

RUN_GEN = {
    'server': """
from server import run
run()
"""
}

CONFIGS = {
    'server': [
        '--exclude-module', 'client',
        '--exclude-module', 'matplotlib',
        '--exclude-module', 'matplotlib.pyplot',
        '--exclude-module', 'prompt_toolkit',
        '--exclude-module', 'PySide2',
        '--exclude-module', 'PyQt6',
        '--hidden-import', 'bson.raw_bson',
        '--hidden-import', 'bson'
    ]
}


def safe_env(key: str, default: any = None) -> str:
    val = os.getenv(key)
    if val:
        return val if len(val.strip()) > 0 else default
    else:
        return default


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', type=str, choices=['server', 'client'])
    parser.add_argument('--build', type=str, choices=['server', 'client'])
    args = parser.parse_args()

    if args.build is not None:
        import subprocess
        import dotenv

        tmp_file = f'{args.build}_build.py'

        with open(tmp_file, 'x') as tmp:
            dotenv.load_dotenv('.env')

            code = CONSTANTS_GEN[args.build].format(
                database_type=safe_env('DATABASE_TYPE', 'None'),
                database_host=safe_env('DATABASE_HOST', 'None'),
                database_port=safe_env('DATABASE_PORT', 'None'),
                mongo_database_name=safe_env('MONGO_DATABASE_NAME', 'None'),
                mongo_collection_name=safe_env('MONGO_COLLECTION_NAME', 'None'),
                firebase_collection_name=safe_env('FIREBASE_COLLECTION_NAME', 'None'),
                firebase_credentials_name=safe_env('FIREBASE_CREDENTIALS_PATH', 'None'),
                mongo_user=safe_env('MONGO_USER', 'None'),
                mongo_pass=safe_env('MONGO_PASS', 'None')
            )
            code += RUN_GEN[args.build]
            tmp.write(code)

        subprocess.run([
            r"C:\Users\yahry\AppData\Local\Programs\Python\Python311\Scripts\pyinstaller.exe",
            *CONFIGS[args.build],
            # '--log-level', 'TRACE',
            '--onefile',
            tmp_file
        ])
        os.remove(tmp_file)

    if args.run is not None:
        from const import load_dotenv
        load_dotenv('.env')

        if args.run == 'client':
            from client import run
            run()
        elif args.run == 'server':
            from server import run
            run()
        else:
            raise ValueError()
