import json
import fastapi
import functools

import typing as T  # noqa

from starlette.responses import Response
from database import AppDatabase, UserItems


db: AppDatabase
app = fastapi.FastAPI()
RequestArgsKwargs = tuple[T.Any, ...], dict[str, T.Any]


def request(
    target: T.Callable[[RequestArgsKwargs], T.Union[str, UserItems]]
) -> T.Callable[[RequestArgsKwargs], Response]:
    @functools.wraps(target)
    def _(*arg, **kwargs):
        try:
            res = target(*arg, **kwargs)

            if isinstance(res, UserItems):
                res = json.dumps(res.to_dict())
            return Response(content=res, status_code=200)

        except Exception as ex:
            return Response(content=str(ex), status_code=404)

    _.__annotations__ = target.__annotations__  # noqa
    _.__name__ = target.__name__
    return _


@app.post('/create_user')
@request
def create_user(
    body: dict = fastapi.Body(dict()),
    user_id: str = fastapi.Query()
):
    db.create_user(user_id, UserItems.from_dict(body))
    return 'Success'


@app.get('/delete_user')
@request
def delete_user(
    user_id: str = fastapi.Query()
):
    db.delete_user(user_id)
    return 'Success'


@app.get('/get_data_by_id')
@request
def get_data_by_id(
    user_id: str = fastapi.Query()
):
    data = db.get_data_by_id(user_id)
    return data


@app.post('/add_data_by_id')
@request
def add_data_by_id(
    body: dict = fastapi.Body(),
    user_id: str = fastapi.Query()
):
    db.add_data_by_id(user_id, UserItems.from_dict(body))
    return 'Success'


@app.post('/delete_data_by_id')
@request
def delete_data_by_id(
    body: list = fastapi.Body(),
    user_id: str = fastapi.Query()
):
    db.delete_data_by_id(user_id, body)
    return 'Success'


@app.get('/iter_all_users')
@request
def iter_all_users(
    pid: int = fastapi.Query(),
    n: int = fastapi.Query()
):
    data = db.iter_all_users(pid, n)
    return data


def run(dotenv_path: str = None):
    global db, app
    import const

    if dotenv_path:
        const.load_dotenv(dotenv_path)

    from database import Database
    db = Database()

    import uvicorn
    uvicorn.run(app=app, host=const.SERVER_HOST, port=int(const.SERVER_PORT))


if __name__ == '__main__':
    run('.env')
