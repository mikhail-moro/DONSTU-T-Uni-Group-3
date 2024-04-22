import flask
from database import Database


app = flask.Flask(__name__)
db: Database


@app.route('/create_user', methods=['POST'])
def create_user():
    try:
        db.create_user(flask.request.args['user_id'], **flask.request.json)
        return 'Success', 200
    except Exception as ex:
        return str(ex), 404


@app.route('/get_data_by_id', methods=['GET'])
def get_data_by_id():
    try:
        data = db.get_data_by_id(flask.request.args['user_id'])
        return flask.jsonify(data)
    except Exception as ex:
        return str(ex), 404


@app.route('/add_data_by_id', methods=['POST'])
def add_data_by_id():
    try:
        db.add_data_by_id(flask.request.args['user_id'], **flask.request.json)
        return 'Success', 200
    except Exception as ex:
        return str(ex), 404


@app.route('/iter_all_users', methods=['GET'])
def iter_all_users():
    try:
        data = db.iter_all_users(int(flask.request.args['n']))
        pid_need = int(flask.request.args['pid'])
        users = next(data, None)

        for _ in range(pid_need):
            users = next(data, None)

        if users is None or len(users) == 0:
            return flask.jsonify({"users": None, 'end_iteration': True}), 200
        else:
            return flask.jsonify({"users": users, 'end_iteration': False}), 200

    except Exception as ex:
        return str(ex), 404


def run():
    global app, db

    import tools
    tools.load_dotenv('server/.flaskenv')

    db = Database()
    app.run(load_dotenv=True)


if __name__ == '__main__':
    run()
