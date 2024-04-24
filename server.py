import json
import fastapi
import functools
import typing as T  # noqa

from starlette.responses import Response


db: T.Any
app = fastapi.FastAPI()
RequestArgsKwargs = tuple[T.Any, ...], dict[str, T.Any]


def request(target: T.Callable[[RequestArgsKwargs], T.Any]) -> T.Callable[[RequestArgsKwargs], Response]:
    @functools.wraps(target)
    def _(*arg, **kwargs):
        try:
            res = target(*arg, **kwargs)
            if isinstance(res, dict):
                res = json.dumps(res)
            return Response(content=json.dumps(res), status_code=200)
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
    db.create_user(user_id, **body)
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
    db.add_data_by_id(user_id, **body)
    return 'Success'


@app.get('/iter_all_users')
@request
def iter_all_users(
    pid: int = fastapi.Query(),
    n: int = fastapi.Query()
):
    data = db.iter_all_users(n)
    pid_need = pid
    users = next(data, None)

    for _ in range(pid_need):
        users = next(data, None)

    if users is None or len(users) == 0:
        return {"users": None, 'end_iteration': True}
    else:
        return {"users": users, 'end_iteration': False}


def run():
    global db, app

    import tools
    tools.load_dotenv('server/.env')

    from ..database import Database
    db = Database()

    import uvicorn
    uvicorn.run(app=app)


if __name__ == '__main__':
    run()
