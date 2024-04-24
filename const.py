import os
import dotenv
import typing as T # noqa


EnvVar = T.Union[str, None]

DATABASE_TYPE: EnvVar = None
DATABASE_HOST: EnvVar = None
DATABASE_PORT: EnvVar = None
MONGO_DATABASE_NAME: EnvVar = None
MONGO_COLLECTION_NAME: EnvVar = None
FIREBASE_COLLECTION_NAME: EnvVar = None
FIREBASE_CREDENTIALS_PATH: EnvVar = None
MONGO_USER: EnvVar = None
MONGO_PASS: EnvVar = None

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
    global MONGO_USER
    global MONGO_PASS

    DATABASE_TYPE = os.environ['DATABASE_TYPE']
    DATABASE_HOST = os.environ['DATABASE_HOST']
    DATABASE_PORT = os.environ['DATABASE_PORT']
    MONGO_DATABASE_NAME = os.environ['MONGO_DATABASE_NAME']
    MONGO_COLLECTION_NAME = os.environ['MONGO_COLLECTION_NAME']
    FIREBASE_COLLECTION_NAME = os.environ['FIREBASE_COLLECTION_NAME']
    FIREBASE_CREDENTIALS_PATH = os.environ['FIREBASE_CREDENTIALS_PATH']
    MONGO_USER = os.environ['MONGO_USER']
    MONGO_PASS = os.environ['MONGO_PASS']


def load_vars(
    database_type: EnvVar = None,
    database_host: EnvVar = None,
    database_port: EnvVar = None,
    mongo_database_name: EnvVar = None,
    mongo_collection_name: EnvVar = None,
    firebase_collection_name: EnvVar = None,
    firebase_credentials_name: EnvVar = None,
    mongo_user: EnvVar = None,
    mongo_pass: EnvVar = None
):
    global _is_env_loaded

    if _is_env_loaded:
        return
    _is_env_loaded = True

    global DATABASE_TYPE
    global DATABASE_HOST
    global DATABASE_PORT
    global MONGO_DATABASE_NAME
    global MONGO_COLLECTION_NAME
    global FIREBASE_COLLECTION_NAME
    global FIREBASE_CREDENTIALS_PATH
    global MONGO_USER
    global MONGO_PASS

    DATABASE_TYPE = database_type
    DATABASE_HOST = database_host
    DATABASE_PORT = database_port
    MONGO_DATABASE_NAME = mongo_database_name
    MONGO_COLLECTION_NAME = mongo_collection_name
    FIREBASE_COLLECTION_NAME = firebase_collection_name
    FIREBASE_CREDENTIALS_PATH = firebase_credentials_name
    MONGO_USER = mongo_user
    MONGO_PASS = mongo_pass
