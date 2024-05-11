import abc

import typing as T  # noqa

from bson import ObjectId
from datetime import datetime
from pydantic import BaseModel
from pymongo import MongoClient
from urllib.parse import quote_plus
from httpx import Client, RequestError

if T.TYPE_CHECKING:
    from google.cloud.firestore import Client
    from pymongo.collection import Collection

Value = T.Union[str, int, float, datetime]
DATETIME_FORMAT = '%d-%m-%Y %H:%M'


def format_datetime(time: datetime) -> str | None:
    if isinstance(time, str):
        return time
    if isinstance(time, datetime):
        return time.strftime(DATETIME_FORMAT)
    return None


def parse_datetime(time: str) -> datetime | None:
    if isinstance(time, datetime):
        return time
    if isinstance(time, str):
        return datetime.strptime(time, DATETIME_FORMAT)
    return None


class Item(BaseModel):
    description: str
    time: datetime
    price: float

    def __init__(self, /, description: str, price: float, time: datetime | None = None):
        super().__init__(
            description=description,
            time=datetime.now() if time is None else time,
            price=price
        )


class UserItems(BaseModel):
    items: list[Item]

    def __init__(self, /, items: list[Item] | Item | None = None):
        if isinstance(items, Item):
            items = [items]
        if items is None:
            items = []
        super().__init__(items=items)

    @classmethod
    def from_dict(cls, dict_data: T.Dict[str, T.Iterable[T.Union[datetime, float]]]) -> 'UserItems':
        items = []
        for description, time_price in dict_data.items():
            items += [Item(
                description=description,
                time=parse_datetime(time_price[0]), # noqa
                price=time_price[1] # noqa
            )]
        return cls(items=items)

    def to_dict(self) -> T.Dict[str, T.Iterable[T.Union[datetime, float]]]:
        out = {}
        for item in self.items:
            out[item.description] = (format_datetime(item.time), item.price)
        return out


class AppDatabase(abc.ABC):
    @abc.abstractmethod
    def create_user(self, user_id: str, init_data: UserItems | None = None) -> None:
        raise NotImplementedError()

    @abc.abstractmethod
    def delete_user(self, user_id: str) -> None:
        raise NotImplementedError()

    @abc.abstractmethod
    def get_data_by_id(self, user_id: str) -> UserItems:
        raise NotImplementedError()

    @abc.abstractmethod
    def add_data_by_id(self, user_id: str, data: UserItems) -> None:
        raise NotImplementedError()

    @abc.abstractmethod
    def delete_data_by_id(self, user_id: str, fields: T.List[str]) -> None:
        raise NotImplementedError()

    @abc.abstractmethod
    def iter_all_users(self, pid: int, n: int) -> T.List[str]:
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

    def create_user(self, user_id: str, init_data: UserItems | None = None) -> None:
        if init_data is None:
            data = {'_id': ObjectId(), 'user_id': user_id}
        else:
            data = {'_id': ObjectId(), 'user_id': user_id, **init_data.to_dict()}
        self._col.insert_one(data)

    def delete_user(self, user_id: str) -> None:
        self._col.delete_one({"user_id": user_id})

    def get_data_by_id(self, user_id: str) -> UserItems:
        result: dict = self._col.find_one({"user_id": user_id})

        if result is None:
            return UserItems()
        else:
            del result['_id'], result['user_id']
            return UserItems.from_dict(result)

    def add_data_by_id(self, user_id: str, data: UserItems) -> None:
        self._col.update_one({'user_id': user_id}, {'$set': data.to_dict()})

    def delete_data_by_id(self, user_id: str, fields: T.List[str]) -> None:
        self._col.update_one({'user_id': user_id}, {'$unset': {f: "" for f in fields}})

    def iter_all_users(self, pid: int, n: int) -> T.List[str]:
        query = self._col.find({}, {'user_id': True}, skip=pid*n, limit=n)
        return [data['user_id'] for data in query]

    def __del__(self):
        self._client.close()


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

    def create_user(self, user_id: str, init_data: UserItems | None = None) -> None:
        res = self._client.post(
            self._url + '/create_user',
            params=[("user_id", user_id)],
            json=None if init_data is None else init_data.to_dict()
        )

        if res.status_code != 200:
            raise RequestError(str(res.content))

    def delete_user(self, user_id: str) -> None:
        res = self._client.get(
            self._url + '/delete_user',
            params=[("user_id", user_id)]
        )

        if res.status_code != 200:
            raise RequestError(str(res.content))

    def get_data_by_id(self, user_id: str) -> UserItems:
        res = self._client.get(
            self._url + '/get_data_by_id',
            params=[("user_id", user_id)]
        )

        if res.status_code != 200:
            raise RequestError(str(res.content))
        else:
            return UserItems.from_dict(res.json())

    def add_data_by_id(self, user_id: str, data: UserItems) -> None:
        res = self._client.post(
            self._url + '/add_data_by_id',
            params=[("user_id", user_id)],
            json=data.to_dict()
        )

        if res.status_code != 200:
            raise RequestError(str(res.content))

    def delete_data_by_id(self, user_id: str, fields: T.List[str]) -> None:
        res = self._client.post(
            self._url + '/delete_data_by_id',
            params=[("user_id", user_id)],
            json=fields
        )

        if res.status_code != 200:
            raise RequestError(str(res.content))

    def iter_all_users(self, pid: int, n: int) -> T.List[str]:
        res = self._client.get(
            self._url + '/iter_all_users',
            params=[("pid", pid), ("n", n)]
        )

        return res.json()

    def __del__(self):
        self._client.close()


def Database() -> AppDatabase:  # noqa
    import const

    if not const._is_env_loaded: # noqa
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
