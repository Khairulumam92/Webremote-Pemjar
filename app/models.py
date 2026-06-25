from datetime import datetime, timezone
from . import db


class ServerGroup(db.Model):
    __tablename__ = 'server_groups'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    color = db.Column(db.String(7), default='#6e7681')

    servers = db.relationship('Server', backref='group', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'color': self.color,
            'server_count': len(self.servers),
        }


class Server(db.Model):
    __tablename__ = 'servers'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    host = db.Column(db.String(255), nullable=False)
    port = db.Column(db.Integer, nullable=False, default=22)
    username = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(255), default='')
    group_id = db.Column(db.Integer, db.ForeignKey('server_groups.id'), nullable=True)
    notes = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    last_seen = db.Column(db.DateTime, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'host': self.host,
            'port': self.port,
            'username': self.username,
            'group_id': self.group_id,
            'group_name': self.group.name if self.group else None,
            'group_color': self.group.color if self.group else None,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_seen': self.last_seen.isoformat() if self.last_seen else None,
        }


class CommandSnippet(db.Model):
    __tablename__ = 'command_snippets'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    command = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text, default='')
    category = db.Column(db.String(80), default='General')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'command': self.command,
            'description': self.description,
            'category': self.category,
        }
