# WebRemote — Web-Based Remote Server Management Console

![License](https://img.shields.io/badge/license-MIT-blue)
![Python](https://img.shields.io/badge/python-3.11+-blue)
![Flask](https://img.shields.io/badge/flask-3.1-black)
![Docker](https://img.shields.io/badge/docker-ready-brightgreen)

A modern web-based dashboard for managing remote servers via SSH. Built as a final project for **Pemrograman Jaringan** (Network Programming).

---

## Screenshot

```
 ┌─────────────────────────────────────────────────────────────┐
 │  ■ WebRemote          │  Dashboard   Servers   Batch        │
 │                       │─────────────────────────────────────│
 │  ▸ Dashboard          │  ┌──────┐ ┌──────┐ ┌──────┐ ┌─────┐│
 │  ▸ Terminal           │  │  3   │ │  2   │ │  1   │ │  2  ││
 │  ▸ Servers            │  │Total │ │Online│ │Offln │ │Grps ││
 │  ▸ Batch              │  └──────┘ └──────┘ └──────┘ └─────┘│
 │  ▸ Files              │─────────────────────────────────────│
 │                       │  Live System Monitor               │
 │  v1.0        8090     │  ┌─────────┐ ┌─────────┐          │
 │                       │  │Srv1  99%│ │Srv2  45%│ ...      │
 │                       │  │CPU ████ │ │CPU ██   │          │
 └───────────────────────┘  └─────────┘ └─────────┘          │
```

---

## Features

| Feature | Description |
|---------|-------------|
| **Web SSH Terminal** | Full interactive terminal via xterm.js + WebSocket. Dual-mode: PTY shell (Linux) and Command mode (Windows) |
| **Server Dashboard** | Overview cards (total/online/offline) + live system monitor (CPU, RAM, Disk) via SocketIO |
| **Server Management** | Add, edit, delete, test connection, organize into groups with color tags |
| **Batch Command** | Execute commands across multiple servers simultaneously with grouped output |
| **SFTP File Manager** | Browse, upload, download, delete, view files on remote servers |
| **Command Snippets** | Save and reuse frequently used commands (available in Terminal and Batch) |
| **Server Groups** | Tag servers into groups (Production, Staging, MikroTik, Linux, Windows) |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3.11+ / Flask / Flask-SocketIO / SQLAlchemy |
| **SSH** | Paramiko (SSH + SFTP) |
| **Async** | Gevent + WebSocket (SocketIO) |
| **Frontend** | HTML5 / CSS3 / Bootstrap 5 / jQuery / xterm.js |
| **Design** | Industrial Precision — dark theme with amber accents, JetBrains Mono for code, Inter for UI |
| **Database** | SQLite (file-based, zero config) |
| **Deploy** | Docker + Nginx reverse proxy |

---

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.11+ (for local dev)

### Option 1: Docker (Recommended)

```bash
# Clone
git clone https://github.com/Khairulumam92/Webremote-Pemjar.git
cd Webremote-Pemjar

# Build & Run
docker compose up -d

# Access
open http://localhost:8090
```

### Option 2: Local Development

```bash
pip install -r requirements.txt
python wsgi.py
# → http://localhost:5000
```

---

## Usage

### 1. Add a Server
Navigate to **Servers** → fill in host, port, username, password → **Add Server**.

### 2. Open Terminal
Click the **terminal icon** on any server row. The app auto-detects Linux/Windows and selects the best mode.

### 3. Run Batch Commands
Navigate to **Batch** → select servers → type or pick a snippet → **Execute**.

### 4. Browse Files
Click the **folder icon** → browse, upload, download, or view files via SFTP.

---

## Port Usage

| Port | Service | Note |
|------|---------|------|
| `8090` | Nginx → WebRemote | External access |
| `5000` | Flask/Gunicorn | Internal (Docker network only) |

Does not conflict with common ports (8080, 8082, 443, 3306).

---

## Project Structure

```
Webremote-Pemjar/
├── app/
│   ├── __init__.py          # Flask factory + DB + SocketIO init
│   ├── models.py            # Server, ServerGroup, CommandSnippet
│   ├── ssh_client.py        # Paramiko wrapper (SSH + SFTP + system info)
│   ├── routes.py            # HTTP routes (CRUD + SFTP + Batch)
│   ├── terminal_events.py   # SocketIO terminal namespace (dual-mode)
│   └── monitor.py           # SocketIO monitor namespace (live stats)
├── static/
│   ├── css/style.css        # Industrial Precision design system
│   └── js/
│       ├── main.js          # UI logic (CRUD, toasts, groups)
│       └── monitor.js       # Live system monitor (SocketIO)
├── templates/
│   ├── base.html            # Layout shell (sidebar + main content)
│   ├── index.html           # Dashboard + live monitor cards
│   ├── servers.html         # Server CRUD + group management
│   ├── terminal.html        # Web SSH (xterm.js + mode toggle + snippets)
│   ├── batch.html           # Multi-server command runner
│   └── files.html           # SFTP file browser
├── Dockerfile
├── nginx.conf
├── docker-compose.yml
├── requirements.txt
├── wsgi.py
└── run.sh
```

---

## API Endpoints

| Method | Route | Description |
|--------|-------|-------------|
| `GET` | `/` | Dashboard |
| `GET/POST` | `/servers` | Server CRUD |
| `GET/PUT/DELETE` | `/api/servers/<id>` | Single server ops |
| `POST` | `/api/servers/<id>/test` | Test SSH connection |
| `GET/POST/DELETE` | `/api/groups` | Group CRUD |
| `GET/POST/DELETE` | `/api/snippets` | Snippet CRUD |
| `GET` | `/terminal/<id>` | Web SSH terminal page |
| `GET` | `/batch` | Batch command page |
| `POST` | `/api/batch/run` | Execute batch command |
| `GET` | `/files/<id>` | File manager page |
| `POST` | `/api/sftp/<id>/list` | List directory |
| `POST` | `/api/sftp/<id>/upload` | Upload file |
| `POST` | `/api/sftp/<id>/download` | Download file |
| `POST` | `/api/sftp/<id>/delete` | Delete file/dir |
| `POST` | `/api/sftp/<id>/mkdir` | Create directory |
| `POST` | `/api/sftp/<id>/content` | View file content |
| **WS** | `/terminal` | SocketIO — SSH terminal I/O |
| **WS** | `/monitor` | SocketIO — Live system stats |

---

## Security Notes

This is a **TA (academic) project** — the following are intentionally simplified:

- **No web auth** — single-user local deployment
- **Plaintext passwords** stored in SQLite (use SSH keys in production)
- **Auto-accept host keys** — `paramiko.AutoAddPolicy()` (use `RejectPolicy` in production)
- **CORS wildcard** — restrict to specific origin in production
- Change `SECRET_KEY` via environment variable before deploying

---

## Identitas

- **Nama:** Moh. Khairul Umam
- **NIM:** 202310370311448
- **Kelas:** Pemrograman Jaringan A
- **Semester:** 6

---

## License

MIT — feel free to use and modify for educational purposes.
