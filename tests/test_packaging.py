"""Contrôles des paquets livrés, sans installer de fichiers système."""

import hashlib
import importlib.util
import io
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("build_deb", ROOT / "packaging/build_deb.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


def read_deb(path):
    data = path.read_bytes()
    if data[:8] != b"!<arch>\n":
        raise AssertionError("Archive ar attendue")
    members = {}
    offset = 8
    while offset < len(data):
        header = data[offset:offset + 60]
        if header[-2:] != b"`\n":
            raise AssertionError("Entete ar invalide")
        name = header[:16].decode().strip().rstrip("/")
        size = int(header[48:58])
        members[name] = data[offset + 60:offset + 60 + size]
        offset += 60 + size + size % 2
    return members


def unpack(data):
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
        return {entry.name.removeprefix("./"): (archive.extractfile(entry).read(), entry)
                for entry in archive.getmembers() if entry.isfile()}


class TestPaquetsDebian(unittest.TestCase):
    def test_archives_roles_permissions_et_configuration(self):
        with tempfile.TemporaryDirectory() as temporary:
            for role, other in (("server", "client"), ("client", "server")):
                with self.subTest(role=role):
                    path = builder.build(role, "1.0.0", Path(temporary))
                    members = read_deb(path)
                    self.assertEqual(list(members), ["debian-binary", "control.tar.gz", "data.tar.gz"])
                    self.assertEqual(members["debian-binary"], b"2.0\n")
                    metadata = unpack(members["control.tar.gz"])
                    files = unpack(members["data.tar.gz"])
                    control = metadata["control"][0].decode()
                    self.assertIn("Architecture: all\n", control)
                    self.assertIn("python3 (>= 3.13)", control)
                    self.assertEqual("python3-pyside6.qtwidgets" in control, role == "server")
                    self.assertEqual(metadata["conffiles"][0], f"/etc/sae302/{role}.conf\n".encode())
                    self.assertIn(f"usr/share/sae302/{role}/config.py", files)
                    self.assertFalse(any(f"/{other}/" in name for name in files))
                    self.assertFalse(any("__pycache__" in name or name.endswith(".sqlite3") for name in files))
                    for name, (content, info) in files.items():
                        self.assertEqual((info.uid, info.gid), (0, 0))
                        if name.startswith("usr/bin/"):
                            self.assertEqual(info.mode, 0o755)
                            subprocess.run(["/bin/sh", "-n"], input=content, check=True)
                    for line in metadata["md5sums"][0].decode().splitlines():
                        digest, name = line.split("  ", 1)
                        self.assertEqual(digest, hashlib.md5(files[name][0]).hexdigest())
                    # Une reconstruction identique doit produire les memes octets.
                    previous = path.read_bytes()
                    builder.build(role, "1.0.0", Path(temporary))
                    self.assertEqual(path.read_bytes(), previous)

    def test_configuration_externe_et_sqlite_hors_du_code(self):
        environment = dict(os.environ, SAE302_HOST="192.0.2.10", SAE302_PORT="54321",
                           SAE302_BIND_HOST="192.0.2.20", SAE302_DB_PATH="/tmp/sae302-test.sqlite3")
        result = subprocess.run([sys.executable, "-c", """
from client.config import HOST, PORT
from server.config import BIND_HOST, PORT as SERVER_PORT, DB_SQLITE_PATH
assert HOST == '192.0.2.10'
assert PORT == SERVER_PORT == 54321
assert BIND_HOST == '192.0.2.20'
assert str(DB_SQLITE_PATH) == '/tmp/sae302-test.sqlite3'
"""], env=environment, cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
