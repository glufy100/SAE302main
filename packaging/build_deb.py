#!/usr/bin/env python3
"""Construit les deux .deb avec Python standard, y compris depuis macOS.

Format Debian 2.0 : debian-binary, control.tar.gz, data.tar.gz dans une archive ar.
Aucune donnee de simulation ni dependance binaire n'est embarquee.
"""

import argparse
import gzip
import hashlib
import io
from pathlib import Path
import re
import tarfile

ROOT = Path(__file__).resolve().parents[1]


def tar_gz(files):
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w", format=tarfile.USTAR_FORMAT) as archive:
        directories = set()
        for name in files:
            directories.update(str(p) for p in Path(name).parents if str(p) != ".")
        for name in sorted(directories):
            info = tarfile.TarInfo("./" + name)
            info.type = tarfile.DIRTYPE
            info.mode = 0o755
            info.uname = info.gname = "root"
            archive.addfile(info)
        for name, (content, mode) in sorted(files.items()):
            info = tarfile.TarInfo("./" + name)
            info.size = len(content)
            info.mode = mode
            info.uname = info.gname = "root"
            archive.addfile(info, io.BytesIO(content))
    return gzip.compress(output.getvalue(), mtime=0)


def write_ar(path, members):
    with path.open("wb") as output:
        output.write(b"!<arch>\n")
        for name, content in members:
            header = f"{name:<16}{0:<12}{0:<6}{0:<6}{'100644':<8}{len(content):<10}`\n"
            output.write(header.encode("ascii"))
            output.write(content)
            if len(content) % 2:
                output.write(b"\n")


def launcher(role, command, database=False):
    lines = ["#!/bin/sh", "set -eu", "set -a",
             f". /etc/sae302/{role}.conf", "set +a",
             "export PYTHONDONTWRITEBYTECODE=1", "export PYTHONUNBUFFERED=1"]
    if database:
        lines.append('export SAE302_DB_PATH="${SAE302_DB_PATH:-${XDG_DATA_HOME:-$HOME/.local/share}/sae302/carrefour.sqlite3}"')
    lines.extend(["cd /usr/share/sae302", f'exec {command} "$@"', ""])
    return "\n".join(lines).encode()


def build(role, version, output):
    package = f"sae302-{role}"
    files = {}

    def add(name, content, mode=0o644):
        files[name] = (content, mode)

    # Liste blanche : ne jamais embarquer caches, environnements ou bases SQLite.
    for path in sorted((ROOT / role).rglob("*.py")):
        if "__pycache__" not in path.parts:
            add(f"usr/share/sae302/{path.relative_to(ROOT).as_posix()}", path.read_bytes())
    conf = f"etc/sae302/{role}.conf"
    add(conf, (ROOT / "packaging/debian" / f"{role}.conf").read_bytes())
    if role == "server":
        add("usr/bin/sae302-server", launcher(role, "/usr/bin/python3 -m server.carrefour", True), 0o755)
        add("usr/share/applications/sae302-server.desktop", b"""[Desktop Entry]
Type=Application
Name=Carrefour intelligent - Serveur
Comment=Simulation SAE302 et serveur TCP
Exec=sae302-server
Icon=applications-education
Terminal=true
Categories=Education;
""")
        dependencies = "python3 (>= 3.13), python3-pyside6.qtwidgets"
        description = "Serveur TCP et interface graphique du carrefour intelligent"
    else:
        add("usr/share/sae302/client/lancer_simulation.sh", (ROOT / "client/lancer_simulation.sh").read_bytes(), 0o755)
        add("usr/bin/sae302-client", launcher(role, "/bin/bash /usr/share/sae302/client/lancer_simulation.sh"), 0o755)
        for name in ("voiture", "urgence"):
            add(f"usr/bin/sae302-{name}", launcher(role, f"/usr/bin/python3 -m client.{name}"), 0o755)
        dependencies = "python3 (>= 3.13), bash, mawk | gawk"
        description = "Clients vehicules du carrefour intelligent"
    for source, target in [("LICENSE", "copyright"), (f"{role}/README.md", "README.md"),
                           ("doc/Installation.md", "Installation.md")]:
        add(f"usr/share/doc/{package}/{target}", (ROOT / source).read_bytes())
    size = (sum(len(content) for content, _ in files.values()) + 1023) // 1024
    control = f"""Package: {package}
Version: {version}
Section: education
Priority: optional
Architecture: all
Maintainer: Equipe SAE302 <sae302@localhost>
Depends: {dependencies}
Installed-Size: {size}
Homepage: https://github.com/glufy100/SAE302main
Description: {description}
 Simulation pedagogique de carrefours en croix et en T sur reseau local.
""".encode()
    checksums = "".join(f"{hashlib.md5(content).hexdigest()}  {name}\n"
                        for name, (content, _) in sorted(files.items()) if not name.startswith("etc/"))
    metadata = {"control": (control, 0o644), "conffiles": (("/" + conf + "\n").encode(), 0o644),
                "md5sums": (checksums.encode(), 0o644)}
    path = output / f"{package}_{version}_all.deb"
    write_ar(path, [("debian-binary", b"2.0\n"), ("control.tar.gz", tar_gz(metadata)),
                    ("data.tar.gz", tar_gz(files))])
    print(path)
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", default="1.0.0")
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9][A-Za-z0-9.+~]*", args.version):
        parser.error("Version attendue : nombre initial, lettres, points, + ou ~.")
    args.output.mkdir(parents=True, exist_ok=True)
    paths = [build(role, args.version, args.output) for role in ("server", "client")]
    sums = "".join(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}\n" for path in paths)
    (args.output / "SHA256SUMS").write_text(sums, encoding="utf-8")


if __name__ == "__main__":
    main()
