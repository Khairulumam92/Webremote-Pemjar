import threading
import time
from flask import request
from flask_socketio import emit, disconnect
from . import socketio, db
from .models import Server
from .ssh_client import RemoteSSHClient

monitor_sessions = {}


@socketio.on('connect', namespace='/monitor')
def on_monitor_connect():
    server_id = request.args.get('server_id', type=int)
    if not server_id:
        emit('error', {'message': 'No server_id provided'})
        disconnect()
        return

    server = db.session.get(Server, server_id)
    if not server:
        emit('error', {'message': 'Server not found'})
        disconnect()
        return

    sid = request.sid
    monitor_sessions[sid] = {'server': server, 'running': True}

    def poll_loop():
        srv = monitor_sessions[sid]['server']
        client = RemoteSSHClient(srv)
        try:
            client.connect(timeout=8)
            os_type = client.detect_os()
        except Exception:
            return

        while monitor_sessions.get(sid, {}).get('running'):
            try:
                info = client.poll_system_info(os_type)
                if info:
                    socketio.emit('stats', info, to=sid, namespace='/monitor')
            except Exception:
                try:
                    client.connect(timeout=8)
                except Exception:
                    time.sleep(5)
                    continue
            time.sleep(5)

        client.close()

    thread = threading.Thread(target=poll_loop, daemon=True)
    thread.start()
    monitor_sessions[sid]['thread'] = thread


@socketio.on('disconnect', namespace='/monitor')
def on_monitor_disconnect():
    sid = request.sid
    if sid in monitor_sessions:
        monitor_sessions[sid]['running'] = False
        monitor_sessions.pop(sid, None)
