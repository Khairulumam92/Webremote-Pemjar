import re
import threading
import time
from flask import request
from flask_socketio import emit, disconnect
from . import socketio, db
from .models import Server
from .ssh_client import RemoteSSHClient

clients = {}


@socketio.on('connect', namespace='/terminal')
def on_connect():
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

    ssh = RemoteSSHClient(server)
    try:
        ssh.connect(timeout=10)
    except Exception as e:
        emit('error', {'message': f'SSH connection failed: {e}'})
        disconnect()
        return

    sid = request.sid
    os_type = ssh.detect_os()

    channel, mode = ssh.open_shell()

    clients[sid] = {'ssh': ssh, 'server_id': server_id, 'mode': mode, 'os': os_type}
    emit('mode', {'mode': mode, 'os': os_type})

    if mode == 'shell':
        time.sleep(0.2)
        _start_shell_reader(ssh, sid)
    else:
        emit('output', {'data': f'\r\n\x1b[36m[Command Mode - {os_type.upper()}]\x1b[0m\r\n'
                                 f'\x1b[33mType commands and press Enter. Use interactive commands with care.\x1b[0m\r\n\r\n'})

    emit('output', {'data': ''})


def _start_shell_reader(ssh, sid):
    def reader():
        while True:
            if sid not in clients:
                break
            try:
                data = ssh.shell_recv(4096)
                if data:
                    socketio.emit('output', {'data': data}, to=sid, namespace='/terminal')
                else:
                    time.sleep(0.1)
            except Exception:
                break

        socketio.emit('output', {'data': '\r\n[Connection closed]\r\n'}, to=sid, namespace='/terminal')

    thread = threading.Thread(target=reader, daemon=True)
    thread.start()


@socketio.on('input', namespace='/terminal')
def on_input(data):
    sid = request.sid
    entry = clients.get(sid)
    if not entry:
        return

    payload = data.get('data', '')
    ssh = entry['ssh']
    mode = entry['mode']

    if mode == 'shell':
        ssh.shell_send(payload)
    else:
        if payload == '\r' or payload == '\n':
            _flush_command_buffer(sid, entry)
        elif payload == '\x7f':
            if 'cmd_buffer' not in entry:
                entry['cmd_buffer'] = ''
            entry['cmd_buffer'] = entry['cmd_buffer'][:-1]
            socketio.emit('output', {'data': '\b \b'}, to=sid, namespace='/terminal')
        elif payload == '\t':
            cmd = entry.get('cmd_buffer', '')
            _auto_complete(ssh, sid, cmd)
        else:
            if 'cmd_buffer' not in entry:
                entry['cmd_buffer'] = ''
            entry['cmd_buffer'] += payload
            socketio.emit('output', {'data': payload}, to=sid, namespace='/terminal')


def _flush_command_buffer(sid, entry):
    cmd = entry.get('cmd_buffer', '')
    entry['cmd_buffer'] = ''
    ssh = entry['ssh']

    socketio.emit('output', {'data': '\r\n'}, to=sid, namespace='/terminal')
    if not cmd.strip():
        return

    if cmd.strip().lower() in ('exit', 'logout'):
        entry['ssh'].close()
        socketio.emit('output', {'data': '\r\n[Session ended]\r\n'}, to=sid, namespace='/terminal')
        disconnect()
        return

    try:
        out, code = ssh.exec_one(cmd)
        if out:
            socketio.emit('output', {'data': out + '\r\n'}, to=sid, namespace='/terminal')
        prompt = 'PS ' if entry.get('os') == 'windows' else '$ '
        socketio.emit('output', {'data': prompt}, to=sid, namespace='/terminal')
    except Exception as e:
        socketio.emit('output', {'data': f'\r\n[Error: {e}]\r\n'}, to=sid, namespace='/terminal')


def _auto_complete(ssh, sid, cmd):
    safe_cmd = re.sub(r'[;&|`$(){}\[\]!\\''\"<>\n\r]', '', cmd)
    try:
        out, _, _ = ssh.exec(f'compgen -c {safe_cmd} 2>/dev/null || echo "{safe_cmd}"')
        matches = [l for l in out.strip().split('\n') if l]
        if len(matches) > 1:
            socketio.emit('output', {'data': '\r\n' + '  '.join(matches) + '\r\n'}, to=sid, namespace='/terminal')
            entry = clients.get(sid)
            if entry:
                entry['cmd_buffer'] = cmd
                socketio.emit('output', {'data': cmd}, to=sid, namespace='/terminal')
    except Exception:
        pass


@socketio.on('resize', namespace='/terminal')
def on_resize(data):
    sid = request.sid
    entry = clients.get(sid)
    if entry and entry['mode'] == 'shell':
        cols = data.get('cols', 80)
        rows = data.get('rows', 24)
        entry['ssh'].resize_pty(cols, rows)


@socketio.on('switch_mode', namespace='/terminal')
def on_switch_mode():
    sid = request.sid
    entry = clients.get(sid)
    if not entry:
        return
    if entry['mode'] == 'shell':
        entry['mode'] = 'command'
    else:
        try:
            channel, _ = entry['ssh'].open_shell()
            if channel:
                entry['mode'] = 'shell'
                _start_shell_reader(entry['ssh'], sid)
            else:
                emit('output', {'data': '\r\n[Cannot switch to shell mode on this host]\r\n'}, to=sid, namespace='/terminal')
                return
        except Exception:
            emit('output', {'data': '\r\n[Cannot switch to shell mode]\r\n'}, to=sid, namespace='/terminal')
            return
    emit('mode', {'mode': entry['mode'], 'os': entry.get('os', 'linux')}, to=sid)


@socketio.on('disconnect', namespace='/terminal')
def on_disconnect():
    sid = request.sid
    entry = clients.pop(sid, None)
    if entry:
        entry['ssh'].close()
