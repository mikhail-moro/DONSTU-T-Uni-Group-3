import abc

import typing as T  # noqa

from bson import ObjectId
from pymongo import MongoClient
from urllib.parse import quote_plus
from httpx import Client, RequestError

if T.TYPE_CHECKING:
    from google.cloud.firestore import Client
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
            uri = "mongodb://%s:%s@%s" % (quote_plus(user), quote_plus(password), host)
        else:
            uri = 'localhost'

        self._client = MongoClient(
            host=uri,
            port=port
        )

        if collection not in self._client[database].list_collection_names():
            self._client[database].create_collection(collection)

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


def Database():  # noqa
    import const

    if not const._is_env_loaded:
        raise ImportError('Call `const.load_env` or `const.load_vars` before')

    match const.DATABASE_TYPE:
        case "MONGO_DB":
            return MongoDatabase(
                database=const.MONGO_DATABASE_NAME,
                collection=const.MONGO_COLLECTION_NAME,
                host=const.DATABASE_HOST,
                port=int(const.DATABASE_PORT),
                user=const.MONGO_USER,
                password=const.MONGO_PASS
            )
        case "WEB_DB":
            return WebDatabase(
                host=const.DATABASE_HOST,
                port=const.DATABASE_PORT
            )
        case _:
            raise ValueError("Database type not selected")
