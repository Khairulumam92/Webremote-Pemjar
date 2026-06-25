import base64
from datetime import datetime, timezone
from flask import Blueprint, render_template, request, jsonify, abort, Response
from . import db
from .models import Server, ServerGroup, CommandSnippet
from .ssh_client import RemoteSSHClient

bp = Blueprint('main', __name__)


@bp.route('/')
def index():
    servers = Server.query.order_by(Server.created_at.desc()).all()
    groups = ServerGroup.query.order_by(ServerGroup.name).all()
    total = len(servers)
    return render_template('index.html', servers=servers, groups=groups, total=total)


@bp.route('/servers')
def servers_page():
    servers = Server.query.order_by(Server.created_at.desc()).all()
    groups = ServerGroup.query.order_by(ServerGroup.name).all()
    snippets = CommandSnippet.query.order_by(CommandSnippet.name).all()
    return render_template('servers.html', servers=servers, groups=groups, snippets=snippets)


@bp.route('/api/servers', methods=['GET'])
def list_servers():
    servers = Server.query.order_by(Server.created_at.desc()).all()
    return jsonify([s.to_dict() for s in servers])


@bp.route('/api/servers', methods=['POST'])
def add_server():
    data = request.get_json(silent=True) or request.form
    name = data.get('name', '').strip()
    host = data.get('host', '').strip()
    username = data.get('username', '').strip()
    password = data.get('password', '')
    port_str = data.get('port', '22')
    group_id_str = data.get('group_id', '')
    notes = data.get('notes', '')

    if not all([name, host, username]):
        return jsonify({'error': 'Name, host, and username are required'}), 400
    try:
        port = int(port_str)
        if not (1 <= port <= 65535):
            port = 22
    except (ValueError, TypeError):
        port = 22
    try:
        group_id = int(group_id_str) if group_id_str else None
    except (ValueError, TypeError):
        group_id = None

    server = Server(
        name=name, host=host, port=port,
        username=username, password=password,
        group_id=group_id, notes=notes,
    )
    db.session.add(server)
    db.session.commit()
    return jsonify(server.to_dict()), 201


@bp.route('/api/servers/<int:server_id>', methods=['DELETE'])
def delete_server(server_id):
    server = db.session.get(Server, server_id)
    if not server:
        abort(404)
    db.session.delete(server)
    db.session.commit()
    return jsonify({'ok': True})


@bp.route('/api/servers/<int:server_id>', methods=['PUT'])
def update_server(server_id):
    server = db.session.get(Server, server_id)
    if not server:
        abort(404)
    data = request.get_json(silent=True) or {}
    if 'group_id' in data:
        gid = data['group_id']
        server.group_id = None if gid is None else (int(gid) if gid else None)
    if 'notes' in data:
        server.notes = data['notes']
    if 'name' in data:
        server.name = data['name']
    if 'host' in data:
        server.host = data['host']
    if 'port' in data:
        server.port = int(data['port'])
    if 'username' in data:
        server.username = data['username']
    if 'password' in data:
        server.password = data['password']
    db.session.commit()
    return jsonify(server.to_dict())


@bp.route('/api/servers/<int:server_id>/test', methods=['POST'])
def test_server(server_id):
    server = db.session.get(Server, server_id)
    if not server:
        abort(404)
    client = RemoteSSHClient(server)
    ok, msg = client.test_connection()
    status = 'online' if ok else 'offline'
    if ok:
        server.last_seen = datetime.now(timezone.utc)
        db.session.commit()
    return jsonify({'status': status, 'message': msg or 'Connected successfully'})


@bp.route('/api/servers/<int:server_id>/monitor', methods=['GET'])
def monitor_server(server_id):
    server = db.session.get(Server, server_id)
    if not server:
        abort(404)
    client = RemoteSSHClient(server)
    info = client.get_system_info()
    if info:
        server.last_seen = datetime.now(timezone.utc)
        db.session.commit()
        info['server_name'] = server.name
        return jsonify(info)
    return jsonify({'error': 'Could not fetch system info'}), 500


@bp.route('/terminal/<int:server_id>')
def terminal_page(server_id):
    server = db.session.get(Server, server_id)
    if not server:
        abort(404)
    snippets = CommandSnippet.query.order_by(CommandSnippet.name).all()
    return render_template('terminal.html', server=server, snippets=snippets)


@bp.route('/batch')
def batch_page():
    servers = Server.query.order_by(Server.name).all()
    snippets = CommandSnippet.query.order_by(CommandSnippet.name).all()
    groups = ServerGroup.query.order_by(ServerGroup.name).all()
    return render_template('batch.html', servers=servers, snippets=snippets, groups=groups)


@bp.route('/api/batch/run', methods=['POST'])
def batch_run():
    data = request.get_json(silent=True) or {}
    server_ids = data.get('server_ids', [])
    command = data.get('command', '').strip()

    if not server_ids or not command:
        return jsonify({'error': 'Select servers and provide a command'}), 400

    results = []
    for sid in server_ids:
        server = db.session.get(Server, sid)
        if not server:
            results.append({'id': sid, 'name': 'Unknown', 'status': 'error', 'output': 'Server not found'})
            continue
        client = RemoteSSHClient(server)
        try:
            client.connect(timeout=8)
            out, err, code = client.exec(command, timeout=20)
            results.append({
                'id': server.id, 'name': server.name, 'host': server.host,
                'status': 'ok' if code == 0 else 'error',
                'exit_code': code, 'output': out, 'stderr': err,
            })
            if code == 0:
                server.last_seen = datetime.now(timezone.utc)
                db.session.commit()
        except Exception as e:
            results.append({
                'id': server.id, 'name': server.name, 'host': server.host,
                'status': 'error', 'exit_code': -1, 'output': '', 'stderr': str(e),
            })
        finally:
            client.close()

    return jsonify(results)


# ── SFTP File Manager ──

@bp.route('/files/<int:server_id>')
def files_page(server_id):
    server = db.session.get(Server, server_id)
    if not server:
        abort(404)
    return render_template('files.html', server=server)


@bp.route('/api/sftp/<int:server_id>/list', methods=['POST'])
def sftp_list(server_id):
    server = db.session.get(Server, server_id)
    if not server:
        abort(404)
    data = request.get_json(silent=True) or {}
    path = data.get('path', '/')
    client = RemoteSSHClient(server)
    try:
        client.connect()
        entries = client.sftp_list(path)
        return jsonify({'path': path, 'entries': entries, 'parent': '/'.join(path.rstrip('/').split('/')[:-1]) or '/'})
    except Exception as e:
        return jsonify({'error': str(e), 'path': path, 'entries': []}), 500
    finally:
        client.close()


@bp.route('/api/sftp/<int:server_id>/download', methods=['POST'])
def sftp_download(server_id):
    server = db.session.get(Server, server_id)
    if not server:
        abort(404)
    data = request.get_json(silent=True) or {}
    path = data.get('path', '')
    client = RemoteSSHClient(server)
    try:
        client.connect()
        content = client.sftp_get_bytes(path)
        fname = path.rsplit('/', 1)[-1]
        return Response(
            content,
            mimetype='application/octet-stream',
            headers={'Content-Disposition': f'attachment; filename="{fname}"'}
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        client.close()


@bp.route('/api/sftp/<int:server_id>/upload', methods=['POST'])
def sftp_upload(server_id):
    server = db.session.get(Server, server_id)
    if not server:
        abort(404)
    file = request.files.get('file')
    dest = request.form.get('path', '/')
    if not file:
        return jsonify({'error': 'No file provided'}), 400
    fname = file.filename or 'uploaded_file'
    remote_path = dest.rstrip('/') + '/' + fname
    client = RemoteSSHClient(server)
    try:
        client.connect()
        client.sftp_put_bytes(remote_path, file.read())
        return jsonify({'ok': True, 'path': remote_path})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        client.close()


@bp.route('/api/sftp/<int:server_id>/delete', methods=['POST'])
def sftp_delete(server_id):
    server = db.session.get(Server, server_id)
    if not server:
        abort(404)
    data = request.get_json(silent=True) or {}
    path = data.get('path', '')
    client = RemoteSSHClient(server)
    try:
        client.connect()
        ok = client.sftp_delete(path)
        return jsonify({'ok': ok})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        client.close()


@bp.route('/api/sftp/<int:server_id>/mkdir', methods=['POST'])
def sftp_mkdir(server_id):
    server = db.session.get(Server, server_id)
    if not server:
        abort(404)
    data = request.get_json(silent=True) or {}
    path = data.get('path', '')
    client = RemoteSSHClient(server)
    try:
        client.connect()
        client.sftp_mkdir(path)
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        client.close()


@bp.route('/api/sftp/<int:server_id>/content', methods=['POST'])
def sftp_content(server_id):
    server = db.session.get(Server, server_id)
    if not server:
        abort(404)
    data = request.get_json(silent=True) or {}
    path = data.get('path', '')
    client = RemoteSSHClient(server)
    try:
        client.connect()
        raw = client.sftp_get_bytes(path)
        try:
            text = raw.decode('utf-8')
            content_type = 'text'
        except Exception:
            text = base64.b64encode(raw).decode('ascii')
            content_type = 'binary'
        return jsonify({'filename': path.rsplit('/', 1)[-1], 'content': text, 'type': content_type})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        client.close()


# ── Server Groups ──

@bp.route('/api/groups', methods=['GET'])
def list_groups():
    groups = ServerGroup.query.order_by(ServerGroup.name).all()
    return jsonify([g.to_dict() for g in groups])


@bp.route('/api/groups', methods=['POST'])
def add_group():
    data = request.get_json(silent=True) or {}
    name = data.get('name', '').strip()
    color = data.get('color', '#6e7681')
    if not name:
        return jsonify({'error': 'Name required'}), 400
    grp = ServerGroup(name=name, color=color)
    db.session.add(grp)
    db.session.commit()
    return jsonify(grp.to_dict()), 201


@bp.route('/api/groups/<int:group_id>', methods=['DELETE'])
def delete_group(group_id):
    grp = db.session.get(ServerGroup, group_id)
    if not grp:
        abort(404)
    Server.query.filter_by(group_id=group_id).update({Server.group_id: None})
    db.session.delete(grp)
    db.session.commit()
    return jsonify({'ok': True})


# ── Command Snippets ──

@bp.route('/api/snippets', methods=['GET'])
def list_snippets():
    snippets = CommandSnippet.query.order_by(CommandSnippet.name).all()
    return jsonify([s.to_dict() for s in snippets])


@bp.route('/api/snippets', methods=['POST'])
def add_snippet():
    data = request.get_json(silent=True) or {}
    name = data.get('name', '').strip()
    command = data.get('command', '').strip()
    description = data.get('description', '').strip()
    category = data.get('category', 'General').strip()
    if not name or not command:
        return jsonify({'error': 'Name and command required'}), 400
    snip = CommandSnippet(name=name, command=command, description=description, category=category)
    db.session.add(snip)
    db.session.commit()
    return jsonify(snip.to_dict()), 201


@bp.route('/api/snippets/<int:snippet_id>', methods=['DELETE'])
def delete_snippet(snippet_id):
    snip = db.session.get(CommandSnippet, snippet_id)
    if not snip:
        abort(404)
    db.session.delete(snip)
    db.session.commit()
    return jsonify({'ok': True})
