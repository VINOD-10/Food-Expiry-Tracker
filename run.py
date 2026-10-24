"""Start the Food Expiry Tracker server.

    python run.py                 # http://127.0.0.1:8000
    python run.py --make-cert     # create certs\\cert.pem and certs\\key.pem (self-signed)
    python run.py --https         # https://127.0.0.1:8443 using certs\\

Environment variables: FOOD_HOST, FOOD_PORT, FOOD_SSL_CERTFILE, FOOD_SSL_KEYFILE,
FOOD_FORWARDED_ALLOW_IPS (trusted reverse proxies, default 127.0.0.1).
"""
import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CERT_DIR = ROOT / "certs"
GIT_OPENSSL = (Path(r"C:\Program Files\Git\mingw64\bin\openssl.exe"), Path(r"C:\Program Files\Git\usr\bin\openssl.exe"))


def find_openssl():
    found = shutil.which("openssl")
    if found:
        return found
    return next((str(path) for path in GIT_OPENSSL if path.exists()), None)


def make_cert(extra_names=()):
    """Self-signed certificate for localhost (plus any extra host names or IPs, e.g. your LAN IP)."""
    openssl = find_openssl()
    if openssl is None:
        sys.exit("OpenSSL was not found. Install Git for Windows (it includes OpenSSL) or add openssl to PATH.")
    CERT_DIR.mkdir(exist_ok=True)
    names = ["DNS:localhost", "IP:127.0.0.1"]
    for name in extra_names:
        names.append(f"IP:{name}" if name.replace(".", "").isdigit() else f"DNS:{name}")
    subprocess.run(
        [openssl, "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-sha256", "-days", "825",
         "-keyout", str(CERT_DIR / "key.pem"), "-out", str(CERT_DIR / "cert.pem"),
         "-subj", "/CN=Food Expiry Tracker", "-addext", f"subjectAltName={','.join(names)}"],
        check=True, env={**os.environ, "MSYS_NO_PATHCONV": "1"}, capture_output=True,
    )
    print(f"Created {CERT_DIR / 'cert.pem'} and {CERT_DIR / 'key.pem'} for: {', '.join(names)}")
    print("Browsers will warn that it is self-signed; choose to continue, or import cert.pem as a trusted certificate.")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run the Food Expiry Tracker server")
    parser.add_argument("--https", action="store_true", help="serve over HTTPS using certs\\cert.pem and certs\\key.pem")
    parser.add_argument("--make-cert", nargs="*", metavar="HOST", help="create a self-signed certificate, optionally for extra host names/IPs")
    args = parser.parse_args(argv)
    if args.make_cert is not None:
        make_cert(args.make_cert)
        return

    certfile = os.environ.get("FOOD_SSL_CERTFILE") or (str(CERT_DIR / "cert.pem") if args.https else None)
    keyfile = os.environ.get("FOOD_SSL_KEYFILE") or (str(CERT_DIR / "key.pem") if args.https else None)
    secure = bool(certfile and keyfile)
    if secure and not (Path(certfile).exists() and Path(keyfile).exists()):
        sys.exit("Certificate files not found. Create them with:  python run.py --make-cert")
    host = os.environ.get("FOOD_HOST", "127.0.0.1")
    port = int(os.environ.get("FOOD_PORT", "8443" if secure else "8000"))
    scheme = "https" if secure else "http"
    # Same-origin requests always work; this also lets the browser origin pass the CORS check.
    os.environ.setdefault("FOOD_CORS_ORIGINS", f"{scheme}://127.0.0.1:{port},{scheme}://localhost:{port}")
    print(f"Food Expiry Tracker running at {scheme}://{host}:{port}")

    import uvicorn
    uvicorn.run(
        "backend.main:app", host=host, port=port,
        ssl_certfile=certfile if secure else None, ssl_keyfile=keyfile if secure else None,
        proxy_headers=True, forwarded_allow_ips=os.environ.get("FOOD_FORWARDED_ALLOW_IPS", "127.0.0.1"),
    )


if __name__ == "__main__":
    main()
