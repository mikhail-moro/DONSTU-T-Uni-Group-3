import flask
import typing as T # noqa
from database import Database


app = flask.Flask(__name__)
db: Database


def request(target: T.Callable[[], str]) -> T.Callable[..., T.Tuple[str, int]]:
    def _():
        try:
            target()
        except Exception as ex:
            return str(ex), 404
    return _


@app.route('/create_user', methods=['POST'])
@request
def create_user():
    db.create_user(flask.request.args['user_id'], **flask.request.json)
    return 'Success'


@app.route('/get_data_by_id', methods=['GET'])
@request
def get_data_by_id():
    data = db.get_data_by_id(flask.request.args['user_id'])
    return flask.jsonify(data)


@app.route('/add_data_by_id', methods=['POST'])
@request
def add_data_by_id():
    db.add_data_by_id(flask.request.args['user_id'], **flask.request.json)
    return 'Success'


@app.route('/iter_all_users', methods=['GET'])
@request
def iter_all_users():
    data = db.iter_all_users(int(flask.request.args['n']))
    pid_need = int(flask.request.args['pid'])
    users = next(data, None)

    for _ in range(pid_need):
        users = next(data, None)

    if users is None or len(users) == 0:
        return flask.jsonify({"users": None, 'end_iteration': True})
    else:
        return flask.jsonify({"users": users, 'end_iteration': False})


def run():
    global db, app

    import tools
    tools.load_dotenv('server/.flaskenv')

    db = Database()
    app.run(load_dotenv=True)


if __name__ == '__main__':
    run()
