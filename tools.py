import os
import dotenv

import functools
import typing as T


if T.TYPE_CHECKING:
    from PySide6.QtWidgets import QWidget

    # QWidget or it subclasses
    QType = T.Union[T.NewType('QSubType', QWidget), QWidget]


def add_on_destroy_callback(
        widget: 'QType',
        callback: T.Callable[['QType'], None],
        position: T.Literal['before', 'after'] = 'before'
) -> 'QType':
    if position == 'before':
        def new_destroy(self: 'QType'):
            callback(self)
            super(self.__class__, self).destroy()
    else:
        def new_destroy(self: 'QType'):
            super(self.__class__, self).destroy()
            callback(self)

    widget.destroy = functools.partial(new_destroy, widget)
    return widget


EnvVar = T.Union[str, None]

DATABASE_TYPE: EnvVar = None
DATABASE_HOST: EnvVar = None
DATABASE_PORT: EnvVar = None
MONGO_DATABASE_NAME: EnvVar = None
MONGO_COLLECTION_NAME: EnvVar = None
FIREBASE_COLLECTION_NAME: EnvVar = None
FIREBASE_CREDENTIALS_PATH: EnvVar = None


_is_env_loaded = False


def load_dotenv(path: str):
    global _is_env_loaded

    if _is_env_loaded:
        return

    _is_env_loaded = True
    dotenv.load_dotenv(path)

    global DATABASE_TYPE
    global DATABASE_HOST
    global DATABASE_PORT
    global MONGO_DATABASE_NAME
    global MONGO_COLLECTION_NAME
    global FIREBASE_COLLECTION_NAME
    global FIREBASE_CREDENTIALS_PATH

    DATABASE_TYPE = os.environ['DATABASE_TYPE']
    DATABASE_HOST = os.environ['DATABASE_HOST']
    DATABASE_PORT = os.environ['DATABASE_PORT']
    MONGO_DATABASE_NAME = os.environ['MONGO_DATABASE_NAME']
    MONGO_COLLECTION_NAME = os.environ['MONGO_COLLECTION_NAME']
    FIREBASE_COLLECTION_NAME = os.environ['FIREBASE_COLLECTION_NAME']
    FIREBASE_CREDENTIALS_PATH = os.environ['FIREBASE_CREDENTIALS_PATH']
