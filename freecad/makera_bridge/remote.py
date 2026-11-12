"""Authenticated host transfer; never retries writes or follows credential redirects."""
import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("Verten omdirigerte forespørselen. Bruk den endelige HTTPS-adressen.")


def settings(prefs):
    address = prefs.GetString("HostURL", "").strip().rstrip("/")
    key = prefs.GetString("HostKey", "").strip()
    if not address:
        raise ValueError("Konfigurer vertsadressen i Makera Bridge-innstillingene.")
    parsed = urlsplit(address)
    if parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ("", "/"):
        raise ValueError("Bruk vertsadressen uten sti, passord eller query-parametere.")
    if parsed.scheme != "https" and not (parsed.scheme == "http" and parsed.hostname in ("localhost", "127.0.0.1", "::1")):
        raise ValueError("Bruk HTTPS for nettverkstilkobling (HTTP er bare tillatt for lokal tunnel).")
    if len(key) < 32:
        raise ValueError("Tilgangsnøkkelen må ha minst 32 tegn.")
    return address, key


def request(address, key, path, method="GET", payload=None, etag=None):
    headers = {"Authorization": "Bearer " + key, "Content-Type": "application/json"}
    if etag is not None:
        headers["If-Match"] = etag
    req = Request(address + path, data=payload, headers=headers, method=method)
    with build_opener(NoRedirect()).open(req, timeout=120) as response:
        data = response.read(64 * 1024 * 1024 + 1)
        if len(data) > 64 * 1024 * 1024:
            raise ValueError("Svaret fra verten er for stort.")
        return json.loads(data), response.headers.get("ETag", "*")


def send_package(path, prefs):
    address, key = settings(prefs)
    payload = Path(path).read_bytes()
    if len(payload) > 64 * 1024 * 1024:
        raise ValueError("Jobbpakken overskrider 64 MiB.")
    receipt, _ = request(address, key, "/api/inbox", "POST", payload)
    expected = hashlib.sha256(payload).hexdigest()
    if receipt.get("sha256") != expected or receipt.get("status") != "received_not_started":
        raise ValueError("Vertens mottakskvittering stemmer ikke med jobbpakken. Ikke send automatisk på nytt.")
    return address, receipt
