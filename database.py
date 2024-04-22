import os
import abc

import typing as T
import firebase_admin as fba
import firebase_admin.firestore as fs

from bson import ObjectId
from pymongo import MongoClient
from urllib.parse import quote_plus
from httpx import Client, RequestError

if T.TYPE_CHECKING:
    from google.cloud.firestore import CollectionReference, Client
    from pymongo.collection import Collection


Value = T.Union[str, int, float]


class AppDatabase(abc.ABC):
    @abc.abstractmethod
    def create_user(self, user_id: str, **init_data: Value) -> None:
        raise NotImplementedError()

    @abc.abstractmethod
    def get_data_by_id(self, user_id: str) -> dict:
        raise NotImplementedError()

    @abc.abstractmethod
    def add_data_by_id(self, user_id: str, **update_data: Value) -> None:
        raise NotImplementedError()

    @abc.abstractmethod
    def iter_all_users(self, n: int) -> T.Generator[T.List[str], None, None]:
        raise NotImplementedError()


class MongoDatabase(AppDatabase):

    _col: 'Collection'
    _client: MongoClient

    def __init__(
        self,
        database: str,
        collection: str,
        host: str = None,
        port: int = 27017,
        user: str = None,
        password: str = None,
    ):
        if user and password:
            uri = "mongodb://%s:%s@%s" % (
                quote_plus(user), quote_plus(password), host
            )
        else:
            uri = 'localhost'

        self._client = MongoClient(
            host=uri,
            port=port,
        )
        self._col = self._client[database][collection]
        self._col.create_index('user_id')

    def create_user(self, user_id: str, **init_data: Value) -> None:
        self._col.insert_one({'_id': ObjectId(), 'user_id': user_id, **init_data})

    def get_data_by_id(self, user_id: str) -> dict:
        result: dict = self._col.find_one({"user_id": user_id})

        if result is None:
            return {}
        else:
            del result['_id'], result['user_id']
            return result

    def add_data_by_id(self, user_id: str, **update_data: Value) -> None:
        self._col.update_one({'user_id': user_id}, {'$set': update_data})

    def iter_all_users(self, n: int) -> T.Generator[T.List[str], None, None]:
        query = self._col.find({}, {'user_id': True})

        while True:
            batch = []
            try:
                for _ in range(n):
                    batch.append(next(query)['user_id'])
                yield batch
            except StopIteration:
                yield batch; return


class FireBaseDatabase(AppDatabase):
    _col: 'CollectionReference'
    _client: 'Client'

    def __init__(
        self,
        credentials: T.Union[str, os.PathLike, fba.credentials.Certificate],
        collection_name: str
    ):
        if not isinstance(credentials, fba.credentials.Certificate):
            credentials = fba.credentials.Certificate(credentials)

        app = fba.initialize_app(credential=credentials)
        self._client = fs.client(app=app)
        self._col = self._client.collection(collection_name)

    def create_user(self, user_id: str, **init_data: Value) -> None:
        self._col.document(user_id).set(init_data)

    def get_data_by_id(self, user_id: str) -> dict[str, Value]:
        data = self._col.document(user_id).get().to_dict()
        return {} if data is None else data

    def add_data_by_id(self, user_id: str, **update_data: Value) -> None:
        self._col.document(user_id).set(update_data, merge=True)

    def iter_all_users(self, n: int) -> T.Generator[T.List[str], None, None]:
        query = self._col.list_documents()

        while True:
            batch = []
            try:
                for _ in range(n):
                    batch.append(next(query).id)
                yield batch
            except StopIteration:
                yield batch
                return


class WebDatabase(AppDatabase):
    host: str
    port: str

    _url: str
    _client: Client

    def __init__(self, host: str, port: str):
        self.host = host
        self.port = port
        self._url = f"http://{host}:{port}"
        self._client = Client(http2=True)

    def create_user(self, user_id: str, **init_data: Value) -> None:
        res = self._client.post(
            self._url + '/create_user',
            params=[("user_id", user_id)],
            json=init_data
        )

        if res.status_code != 200:
            raise RequestError(str(res.content))

    def get_data_by_id(self, user_id: str) -> dict:
        res = self._client.get(
            self._url + '/get_data_by_id',
            params=[("user_id", user_id)]
        )

        if res.status_code != 200:
            raise RequestError(str(res.content))
        else:
            return res.json()

    def add_data_by_id(self, user_id: str, **update_data: Value) -> None:
        res = self._client.post(
            self._url + '/add_data_by_id',
            params=[("user_id", user_id)],
            json=update_data
        )

        if res.status_code != 200:
            raise RequestError(str(res.content))

    def iter_all_users(self, n: int) -> T.Generator[T.List[str], None, None]:
        pid = 0

        while True:
            res = self._client.get(
                self._url + '/iter_all_users',
                params=[("n", n), ("pid", pid)]
            )

            if res.status_code != 200:
                raise RequestError(str(res.content))

            data = res.json()
            pid += 1

            if data["end_iteration"]:
                break
            else:
                yield data["users"]
        return

    def __del__(self):
        self._client.close()

def Database():
    import tools

    match tools.DATABASE_TYPE:
        case "MONGO_DB":
            return MongoDatabase(
                database=tools.MONGO_DATABASE_NAME,
                collection=tools.MONGO_COLLECTION_NAME,
                host=tools.DATABASE_HOST,
                port=int(tools.DATABASE_PORT),
                user=tools.MONGO_USER,
                password=tools.MONGO_PASS
            )
        case "FIREBASE":
            return FireBaseDatabase(
                credentials=tools.FIREBASE_CREDENTIALS_PATH,
                collection_name=tools.FIREBASE_COLLECTION_NAME
            )
        case "WEB_DB":
            return WebDatabase(
                host=tools.DATABASE_HOST,
                port=tools.DATABASE_PORT
            )
        case _:
            raise ValueError("Database type not selected")
