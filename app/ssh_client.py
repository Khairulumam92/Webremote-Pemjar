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
        transport = self.client.get_transport()
        if transport:
            transport.set_keepalive(30)
        return True

    def detect_os(self):
        if self._os_type:
            return self._os_type
        try:
            _, out, _ = self.client.exec_command('uname -s', timeout=5)
            output = out.read().decode('utf-8', errors='ignore').strip()
            if output and 'windows' not in output.lower():
                self._os_type = 'linux'
                return self._os_type
        except Exception:
            pass

        try:
            _, out, _ = self.client.exec_command('cmd /c ver', timeout=5)
            output = out.read().decode('utf-8', errors='ignore').strip()
            if 'Windows' in output:
                self._os_type = 'windows'
                return self._os_type
        except Exception:
            pass

        try:
            _, out, _ = self.client.exec_command('echo %OS%', timeout=5)
            out_str = out.read().decode('utf-8', errors='ignore').strip()
            if out_str and 'windows' in out_str.lower():
                self._os_type = 'windows'
                return self._os_type
        except Exception:
            pass

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
            self.channel.settimeout(0.5)
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
        if not self.channel or not self.channel.active:
            return None
        try:
            data = self.channel.recv(nbytes)
            if data:
                return data.decode('utf-8', errors='ignore')
            if self.channel.closed or self.channel.eof_received:
                return None
        except socket.timeout:
            pass
        except Exception:
            return None
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
        if err and code != 0:
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

    def _collect_system_info(self, os_type):
        """Collect stats assuming an open connection. Does NOT connect or close."""
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
            _, out, _ = self.client.exec_command('hostname')
            info['hostname'] = out.read().decode('utf-8', errors='ignore').strip()

            _, out, _ = self.client.exec_command(
                'powershell -Command "(Get-CimInstance Win32_Processor).LoadPercentage"')
            raw = out.read().decode('utf-8', errors='ignore').strip()
            info['cpu'] = f'{raw}%' if raw else 'N/A'

            _, out, _ = self.client.exec_command(
                'powershell -Command "$os=Get-CimInstance Win32_OperatingSystem;'
                '[math]::Round(($os.TotalVisibleMemorySize-$os.FreePhysicalMemory)/$os.TotalVisibleMemorySize*100)"')
            raw = out.read().decode('utf-8', errors='ignore').strip()
            info['mem'] = f'{raw}%' if raw else 'N/A'

            _, out, _ = self.client.exec_command(
                'powershell -Command "Get-PSDrive C | ForEach-Object '
                '{ [math]::Round(($_.Used)/($_.Used+$_.Free)*100) }"')
            raw = out.read().decode('utf-8', errors='ignore').strip()
            info['disk'] = f'{raw}%' if raw else 'N/A'

        return info

    def get_system_info(self):
        """One-shot system info: connect, collect, close."""
        try:
            self.connect(timeout=8)
            os_type = self.detect_os()
            return self._collect_system_info(os_type)
        except Exception:
            return None
        finally:
            self.close()

    def poll_system_info(self, os_type=None):
        """Poll stats on an already-open connection. OS type must be provided from first connect."""
        return self._collect_system_info(os_type or self._os_type or 'linux')
