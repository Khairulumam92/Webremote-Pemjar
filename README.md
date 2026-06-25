# WebRemote — Web-Based Remote Server Management Console

![License](https://img.shields.io/badge/license-MIT-blue)
![Python](https://img.shields.io/badge/python-3.11+-blue)
![Flask](https://img.shields.io/badge/flask-3.1-black)
![Docker](https://img.shields.io/badge/docker-ready-brightgreen)

A modern web-based dashboard for managing remote servers via SSH. Built as a final project for **Pemrograman Jaringan** (Network Programming).

---

## Features

| Feature | Description |
|---------|-------------|
| **Authentication** | Login page with session-based auth, credentials via environment variables |
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
| **SSH** | Paramiko (SSH + SFTP) with keepalive for stable connections |
| **Async** | Gevent + simple-websocket (SocketIO) |
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
git clone https://github.com/Khairulumam92/Webremote-Pemjar.git
cd Webremote-Pemjar

# Configure credentials
cp .env.example .env
nano .env   # change WEBREMOTE_USER and WEBREMOTE_PASS

# Build & Run
docker compose up -d --build

# Access
open http://localhost:8090
```

**Default login:** `admin` / `webremote` (change via `.env`)

### Option 2: Local Development

```bash
pip install -r requirements.txt

# Set credentials
export WEBREMOTE_USER=admin
export WEBREMOTE_PASS=webremote

python wsgi.py
# → http://localhost:5000
```

---

## Configuration

All configuration is done via environment variables. Create a `.env` file (not committed to git):

| Variable | Default | Description |
|----------|---------|-------------|
| `WEBREMOTE_USER` | `admin` | Login username |
| `WEBREMOTE_PASS` | `webremote` | Login password |
| `SECRET_KEY` | *(auto)* | Flask session signing key |

---

## Usage

### 1. Login
Open the app → enter credentials from your `.env` file. Session lasts 24 hours.

### 2. Add a Server
Navigate to **Servers** → fill in host, port, username, password → **Add Server**.

### 3. Open Terminal
Click the **terminal icon** on any server row. Auto-detects Linux/Windows and selects the best mode (PTY shell or command mode).

### 4. Run Batch Commands
Navigate to **Batch** → select servers → type or pick a snippet → **Execute**.

### 5. Browse Files
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
│   ├── auth.py              # Authentication (login_required decorator, env credentials)
│   ├── models.py            # Server, ServerGroup, CommandSnippet
│   ├── ssh_client.py        # Paramiko wrapper (SSH + SFTP + system info + keepalive)
│   ├── routes.py            # HTTP routes (CRUD + SFTP + Batch + Login)
│   ├── terminal_events.py   # SocketIO terminal namespace (dual-mode)
│   └── monitor.py           # SocketIO monitor namespace (live stats, persistent SSH)
├── static/
│   ├── css/style.css        # Industrial Precision design system
│   └── js/
│       ├── main.js          # UI logic (CRUD, toasts, groups)
│       └── monitor.js       # Live system monitor (SocketIO)
├── templates/
│   ├── base.html            # Layout shell (sidebar + main content + logout)
│   ├── login.html           # Login page (dark theme)
│   ├── index.html           # Dashboard + live monitor cards
│   ├── servers.html         # Server CRUD + group management
│   ├── terminal.html        # Web SSH (xterm.js + mode toggle + snippets)
│   ├── batch.html           # Multi-server command runner
│   └── files.html           # SFTP file browser
├── .env.example             # Template for environment variables (safe to commit)
├── Dockerfile
├── nginx.conf
├── docker-compose.yml
├── requirements.txt
├── wsgi.py
└── run.sh
```

---

## API Endpoints

| Method | Route | Auth | Description |
|--------|-------|------|-------------|
| `GET/POST` | `/login` | No | Login page / authenticate |
| `GET` | `/logout` | No | Clear session, redirect to login |
| `GET` | `/` | Yes | Dashboard |
| `GET/POST` | `/servers` | Yes | Server CRUD |
| `GET/PUT/DELETE` | `/api/servers/<id>` | Yes | Single server ops |
| `POST` | `/api/servers/<id>/test` | Yes | Test SSH connection |
| `GET` | `/api/servers/<id>/monitor` | Yes | One-shot system info |
| `GET/POST/DELETE` | `/api/groups` | Yes | Group CRUD |
| `GET/POST/DELETE` | `/api/snippets` | Yes | Snippet CRUD |
| `GET` | `/terminal/<id>` | Yes | Web SSH terminal page |
| `GET` | `/batch` | Yes | Batch command page |
| `POST` | `/api/batch/run` | Yes | Execute batch command |
| `GET` | `/files/<id>` | Yes | File manager page |
| `POST` | `/api/sftp/<id>/list` | Yes | List directory |
| `POST` | `/api/sftp/<id>/upload` | Yes | Upload file |
| `POST` | `/api/sftp/<id>/download` | Yes | Download file |
| `POST` | `/api/sftp/<id>/delete` | Yes | Delete file/dir |
| `POST` | `/api/sftp/<id>/mkdir` | Yes | Create directory |
| `POST` | `/api/sftp/<id>/content` | Yes | View file content |
| **WS** | `/terminal` | — | SocketIO — SSH terminal I/O |
| **WS** | `/monitor` | — | SocketIO — Live system stats |

Unauthenticated API requests return `401 JSON`. Page requests redirect to `/login`.

---

## Security Notes

This is a **TA (academic) project** — the following are intentionally simplified:

- **Session-based login** — username/password via env vars (no OAuth/MFA)
- **Plaintext SSH passwords** — stored in SQLite (use SSH keys in production)
- **Auto-accept host keys** — `paramiko.AutoAddPolicy()` (use `RejectPolicy` in production)
- **CORS wildcard** — restrict to specific origin in production
- **Credentials via `.env`** — file is gitignored, never pushed to repository

---

## Identitas

- **Nama:** Moh. Khairul Umam
- **NIM:** 202310370311448
- **Kelas:** Pemrograman Jaringan A
- **Semester:** 6

---

## License

MIT — feel free to use and modify for educational purposes.
