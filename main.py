import os
import abc
import dotenv
import argparse
import subprocess

import typing as T # noqa


CONSTANTS_GEN = """
from const import load_vars

load_vars(
    mongo_user={mongo_user},
    mongo_pass={mongo_pass},
    server_host={server_host},
    server_port={server_port},
    database_type={database_type},
    database_host={database_host},
    database_port={database_port},
    mongo_database_name={mongo_database_name},
    mongo_collection_name={mongo_collection_name},
    firebase_collection_name={firebase_collection_name},
    firebase_credentials_name={firebase_credentials_name}
)
"""

RUN_GEN = {
    'server': """
from server import run
run()
""",
    'client': """
__version__ = "alpha-0.1" 
from client import run
run(config={platform})
"""
}

CONFIGS = {
    'server': [
        '--exclude-module', 'matplotlib',
        '--exclude-module', 'matplotlib.pyplot',
        '--exclude-module', 'prompt_toolkit',
        '--exclude-module', 'PySide2',
        '--exclude-module', 'PyQt6',
        '--hidden-import', 'bson.raw_bson',
        '--hidden-import', 'bson'
    ],
    'client': []
}


PLATFORMS = {
    'linux': 'desktop',
    'windows': 'desktop',
    'android': 'mobile',
    'ios': 'mobile'
}


def safe_env(key: str, default: str | None = None) -> str:
    val = os.getenv(key)
    if val:
        return val if len(val.strip()) > 0 else default
    else:
        return 'None' if default is None else f"'{default}'"


def run(runnable: T.Literal['client', 'server']):
    from const import load_dotenv
    load_dotenv('.env')

    if runnable == 'client':
        from client import run
        run()
    elif runnable == 'server':
        from server import run
        run()
    else:
        raise ValueError("runnable arg must be one of ['client', 'server']")


class Builder(abc.ABC):
    def _init_tmp(self, build_config: str) -> str: # noqa

        if not os.path.exists('tmp'):
            os.mkdir('tmp')

        tmp_file = 'tmp\\main.py'

        with open(tmp_file, 'x') as tmp:
            dotenv.load_dotenv('.env')

            code = CONSTANTS_GEN.format(
                mongo_user=safe_env('MONGO_USER'),
                mongo_pass=safe_env('MONGO_PASS'),
                server_host=safe_env('SERVER_HOST'),
                server_port=safe_env('SERVER_PORT'),
                database_type=safe_env('DATABASE_TYPE'),
                database_host=safe_env('DATABASE_HOST'),
                database_port=safe_env('DATABASE_PORT'),
                mongo_database_name=safe_env('MONGO_DATABASE_NAME'),
                mongo_collection_name=safe_env('MONGO_COLLECTION_NAME'),
                firebase_collection_name=safe_env('FIREBASE_COLLECTION_NAME'),
                firebase_credentials_name=safe_env('FIREBASE_CREDENTIALS_PATH')
            )
            code += RUN_GEN[build_config]
            tmp.write(code)
        return tmp_file

    @abc.abstractmethod
    def build(self, build_config: str) -> None:
        raise NotImplementedError()


class DesktopBuilder(Builder):
    def build(self, build_config: str) -> None:
        tmp_file = self._init_tmp(build_config)

        subprocess.run([
            'pyinstaller',
            *CONFIGS[build_config],
            '--log-level', 'TRACE',
            '--onefile',
            tmp_file
        ])
        os.remove(tmp_file)


class MobileBuilder(Builder):
    def build(self, build_config: str) -> None:
        tmp_file = self._init_tmp(build_config)

        subprocess.run(['buildozer', 'init'])

        with open('buildozer.spec', 'r') as spec:
            spec_text = spec.read()

        spec_text = spec_text.replace(
            'title = My Application',
            'title = Kivy Application'
        )
        spec_text = spec_text.replace(
            'package.name = myapp',
            'package.name = kivyapp'
        )
        spec_text = spec_text.replace(
            'package.domain = org.test',
            'package.domain = org.karasik_software'
        )
        spec_text = spec_text.replace(
            'source.dir = .',
            'source.dir = tmp'
        )

        with open('buildozer.spec', 'w') as spec:
            spec.write(spec_text)

        subprocess.run([
            'buildozer',
            'android',
            'debug'
        ])
        os.remove(tmp_file)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', type=str, default=None, choices=['server', 'client'])
    parser.add_argument('--build', type=str, default=None, choices=['server', 'client'])
    parser.add_argument('--platform', type=str, default=None, choices=['desktop', 'mobile'])
    args = parser.parse_args()

    if args.build is not None:
        builder: Builder

        if args.platform == 'desktop':
            builder = DesktopBuilder()
        elif args.platform == 'mobile':
            builder = MobileBuilder()
        else:
            raise ValueError("for build --platform arg must be passed")
        builder.build(args.build)

    if args.run is not None:
        run(args.run)
