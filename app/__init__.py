import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO

db = SQLAlchemy()
socketio = SocketIO()


def create_app():
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    data_dir = os.path.join(base, 'data')
    os.makedirs(data_dir, exist_ok=True)

    app = Flask(__name__,
                static_folder=os.path.join(base, 'static'),
                template_folder=os.path.join(base, 'templates'))
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'webremote-change-me-in-production')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(data_dir, 'webremote.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['PERMANENT_SESSION_LIFETIME'] = 86400

    db.init_app(app)
    socketio.init_app(app, cors_allowed_origins='*', async_mode='gevent')  # NOTE: restrict in production

    with app.app_context():
        from . import models
        db.create_all()

    from . import routes
    app.register_blueprint(routes.bp)

    from . import terminal_events
    from . import monitor

    return app
