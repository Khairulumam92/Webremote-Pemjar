import paramiko
import socket
import stat as statlib
from datetime import datetime, timezone


class RemoteSSHClient:

    def __init__(self, server):
        self.host = server.host
        self.port = server.port
        self.username = server.username
        self.password = server.password or ''
        self.client = None
        self.channel = None
        self.sftp = None
        self._os_type = None

    def connect(self, timeout=10):
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.client.connect(
            hostname=self.host,
            port=self.port,
            username=self.username,
            password=self.password,
            timeout=timeout,
            allow_agent=False,
            look_for_keys=False,
        )
        return True

    def detect_os(self):
        if self._os_type:
            return self._os_type
        try:
            _, out, _ = self.client.exec_command('uname -s 2>/dev/null || ver 2>nul', timeout=5)
            output = out.read().decode('utf-8', errors='ignore').strip()
            if 'Windows' in output or 'win32' in output.lower():
                self._os_type = 'windows'
            elif output:
                self._os_type = 'linux'
            else:
                _, out2, _ = self.client.exec_command('echo %OS%', timeout=5)
                out2_str = out2.read().decode('utf-8', errors='ignore').strip()
                self._os_type = 'windows' if out2_str else 'linux'
        except Exception:
            self._os_type = 'linux'
        return self._os_type

    def exec(self, command, timeout=15):
        _, stdout, stderr = self.client.exec_command(command, timeout=timeout)
        exit_code = stdout.channel.recv_exit_status()
        out = stdout.read().decode('utf-8', errors='ignore')
        err = stderr.read().decode('utf-8', errors='ignore')
        return out, err, exit_code

    def open_shell(self, term='xterm-256color', cols=80, rows=24):
        try:
            self.channel = self.client.invoke_shell(
                term=term, width=cols, height=rows)
            self.channel.setblocking(0)
            return self.channel, 'shell'
        except Exception:
            return None, 'command'

    def shell_send(self, data):
        if self.channel and self.channel.active:
            try:
                self.channel.send(data)
            except Exception:
                pass

    def shell_recv(self, nbytes=4096):
        try:
            if self.channel and self.channel.recv_ready():
                return self.channel.recv(nbytes).decode('utf-8', errors='ignore')
        except Exception:
            pass
        return ''

    def shell_recv_fallback(self, nbytes=4096):
        try:
            if self.channel:
                data = self.channel.recv(nbytes)
                if data:
                    return data.decode('utf-8', errors='ignore')
        except Exception:
            pass
        return ''

    def resize_pty(self, cols, rows):
        try:
            if self.channel:
                self.channel.resize_pty(width=cols, height=rows)
        except Exception:
            pass

    def exec_one(self, command, timeout=15):
        out, err, code = self.exec(command, timeout=timeout)
        result = out
        if err:
            result += '\r\n[STDERR] ' + err
        return result, code

    def open_sftp(self):
        transport = self.client.get_transport()
        if not transport or not transport.is_active():
            self.connect()
        self.sftp = paramiko.SFTPClient.from_transport(self.client.get_transport())
        return self.sftp

    def sftp_list(self, path='/'):
        sftp = self.sftp or self.open_sftp()
        entries = []
        for entry in sftp.listdir_attr(path):
            is_dir = statlib.S_ISDIR(entry.st_mode)
            entries.append({
                'name': entry.filename,
                'size': entry.st_size if not is_dir else 0,
                'is_dir': is_dir,
                'modified': datetime.fromtimestamp(entry.st_mtime, tz=timezone.utc).isoformat() if entry.st_mtime else None,
                'permissions': statlib.filemode(entry.st_mode),
            })
        entries.sort(key=lambda e: (not e['is_dir'], e['name'].lower()))
        return entries

    def sftp_get_bytes(self, remote_path):
        sftp = self.sftp or self.open_sftp()
        with sftp.open(remote_path, 'rb') as f:
            return f.read()

    def sftp_put_bytes(self, remote_path, data):
        sftp = self.sftp or self.open_sftp()
        with sftp.open(remote_path, 'wb') as f:
            f.write(data)

    def sftp_delete(self, path):
        sftp = self.sftp or self.open_sftp()
        try:
            attr = sftp.stat(path)
            if statlib.S_ISDIR(attr.st_mode):
                sftp.rmdir(path)
            else:
                sftp.remove(path)
            return True
        except Exception:
            return False

    def sftp_mkdir(self, path):
        sftp = self.sftp or self.open_sftp()
        sftp.mkdir(path)
        return True

    def sftp_exists(self, remote_path):
        try:
            sftp = self.sftp or self.open_sftp()
            sftp.stat(remote_path)
            return True
        except Exception:
            return False

    def close(self):
        if self.sftp:
            try:
                self.sftp.close()
            except Exception:
                pass
        if self.channel:
            try:
                self.channel.close()
            except Exception:
                pass
        if self.client:
            try:
                self.client.close()
            except Exception:
                pass

    def test_connection(self):
        try:
            self.connect(timeout=8)
            return True, None
        except (paramiko.AuthenticationException,
                paramiko.SSHException,
                socket.error,
                TimeoutError) as e:
            return False, str(e)
        finally:
            self.close()

    def get_system_info(self):
        try:
            self.connect(timeout=8)
            os_type = self.detect_os()
            info = {'os': os_type, 'hostname': '', 'cpu': '', 'mem': '', 'disk': ''}

            if os_type == 'linux':
                _, out, _ = self.client.exec_command('hostname')
                info['hostname'] = out.read().decode('utf-8', errors='ignore').strip()

                _, out, _ = self.client.exec_command("top -bn1 | grep 'Cpu(s)' | awk '{print $2+$4\"%\"}'")
                info['cpu'] = out.read().decode('utf-8', errors='ignore').strip()

                _, out, _ = self.client.exec_command("free -m | awk '/Mem:/ {printf \"%.0f%%\", $3/$2*100}'")
                info['mem'] = out.read().decode('utf-8', errors='ignore').strip()

                _, out, _ = self.client.exec_command("df -h / | awk 'NR==2 {print $5}'")
                info['disk'] = out.read().decode('utf-8', errors='ignore').strip()
            else:
                _, out, _ = self.client.exec_command('echo %COMPUTERNAME%')
                info['hostname'] = out.read().decode('utf-8', errors='ignore').strip()

                _, out, _ = self.client.exec_command('wmic cpu get loadpercentage | findstr /r "[0-9]"')
                info['cpu'] = out.read().decode('utf-8', errors='ignore').strip() + '%'

                _, out, _ = self.client.exec_command(
                    'wmic OS get TotalVisibleMemorySize,FreePhysicalMemory /format:csv | findstr /r "[0-9]"')
                raw = out.read().decode('utf-8', errors='ignore').strip()
                if raw:
                    parts = raw.split(',')
                    if len(parts) >= 3:
                        try:
                            free = int(parts[-2])
                            total = int(parts[-1])
                            pct = round((total - free) / total * 100)
                            info['mem'] = f'{pct}%'
                        except Exception:
                            info['mem'] = 'N/A'

                _, out, _ = self.client.exec_command(
                    'wmic logicaldisk where "DeviceID=\'C:\'" get Size,FreeSpace /format:csv | findstr /r "[0-9]"')
                raw2 = out.read().decode('utf-8', errors='ignore').strip()
                if raw2:
                    parts2 = raw2.split(',')
                    if len(parts2) >= 3:
                        try:
                            free = int(parts2[-2])
                            total = int(parts2[-1])
                            pct = round((total - free) / total * 100)
                            info['disk'] = f'{pct}%'
                        except Exception:
                            info['disk'] = 'N/A'

            return info
        except Exception:
            return None
        finally:
            self.close()
