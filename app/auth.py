import os
from functools import wraps
from flask import session, redirect, url_for, request, jsonify


WEBREMOTE_USER = os.environ.get('WEBREMOTE_USER', 'admin')
WEBREMOTE_PASS = os.environ.get('WEBREMOTE_PASS', 'webremote')


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logged_in'):
            if request.path.startswith('/api/') or request.path.startswith('/terminal') or request.path.startswith('/files'):
                return jsonify({'error': 'Unauthorized'}), 401
            return redirect(url_for('main.login_page'))
        return f(*args, **kwargs)
    return decorated
