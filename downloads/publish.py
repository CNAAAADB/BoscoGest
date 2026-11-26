"""Publish a verified Android APK and refresh the downloads page in S3."""
import argparse
import hashlib
import html
import json
from pathlib import Path
import re
import subprocess
from string import Template

BUCKET = "boscogest-frontend"
PREFIX = "descargas/"
KEY = re.compile(r"descargas/(BoscoGest-([A-Za-z0-9][A-Za-z0-9._+-]{0,79})-v([0-9]+)-([0-9a-f]{64})\.apk)")


def aws(*args):
    return subprocess.check_output(["aws", "s3api", *args], text=True)


def publish(apk, build_tools):
    subprocess.run([build_tools / "apksigner", "verify", apk], check=True)
    manifest = subprocess.check_output([build_tools / "aapt", "dump", "badging", apk], text=True)
    package = re.search(r"^package: name='com\.boscogest\.app' versionCode='(\d+)' versionName='([^']+)'", manifest, re.M)
    if not package:
        raise ValueError("El APK no contiene el paquete de BoscoGest")
    code, version = package.groups()
    digest = hashlib.sha256(apk.read_bytes()).hexdigest()
    name = f"BoscoGest-{version}-v{code}-{digest}.apk"
    if not KEY.fullmatch(PREFIX + name):
        raise ValueError("Nombre de versión no válido")
    aws("put-object", "--bucket", BUCKET, "--key", PREFIX + name, "--body", str(apk),
        "--content-type", "application/vnd.android.package-archive", "--content-disposition",
        f'attachment; filename="BoscoGest-{version}-v{code}.apk"', "--cache-control", "public,max-age=31536000,immutable")
    objects = json.loads(aws("list-objects-v2", "--bucket", BUCKET, "--prefix", PREFIX))["Contents"]
    page = Path("index.html")
    page.write_text(render(objects), encoding="utf-8")
    aws("put-object", "--bucket", BUCKET, "--key", PREFIX + "index.html", "--body", str(page),
        "--content-type", "text/html; charset=utf-8", "--cache-control", "no-cache")
    print(f"BoscoGest {version} ({code}) SHA-256 {digest}")


def render(objects):
    releases = []
    for obj in objects:
        match = KEY.fullmatch(obj["Key"])
        if match:
            name, version, code, digest = match.groups()
            releases.append((int(code), obj["LastModified"], name, version, digest))
    cards = []
    for code, _, name, version, digest in sorted(releases, reverse=True):
        cards.append(f'<article><h2>BoscoGest {html.escape(version)}</h2><p>Android · Compilación {code}</p>'
                     f'<a class="download" href="{html.escape(name)}" download>Descargar APK</a>'
                     f'<p class="hash">SHA-256 <code>{digest}</code></p></article>')
    template = Path(__file__).with_name("index.template.html").read_text(encoding="utf-8")
    return Template(template).substitute(releases="\n".join(cards) or "<p>Todavía no hay versiones disponibles.</p>")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("apk", type=Path)
    parser.add_argument("build_tools", type=Path)
    args = parser.parse_args()
    publish(args.apk, args.build_tools)
