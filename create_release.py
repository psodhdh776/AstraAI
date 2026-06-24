"""
Создание GitHub релиза через API.
Использует токен из data/github_config.json

Пример:
  python create_release.py --tag v2.2.0 --title "v2.2.0 — Фрактальное мышление"
"""
import argparse, json, os, ssl, sys, urllib.request
from pathlib import Path

REPO = "psodhdh776/AstraAI"
API = f"https://api.github.com/repos/{REPO}/releases"
CONFIG_PATH = Path(__file__).parent / "data" / "github_config.json"


def _get_token():
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8")).get("github_token", "")
    return ""


def _api(method, url, data=None):
    token = _get_token()
    if not token:
        print("ERROR: токен не найден в data/github_config.json")
        sys.exit(1)
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    body = json.dumps(data, ensure_ascii=False).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("User-Agent", "AstraAI")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        print(f"ERROR: {e.code} {e.reason}")
        print(e.read().decode())
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)


def list_releases():
    data = _api("GET", API)
    if not data:
        print("Нет релизов")
        return
    for r in data:
        print(f"  {r['tag_name']:12s}  {r['name'][:50]:50s}  {r['published_at'][:10]}")


def create_release(tag, title, body, draft=False, prerelease=False):
    payload = {
        "tag_name": tag,
        "name": title or tag,
        "body": body or "",
        "draft": draft,
        "prerelease": prerelease,
    }
    result = _api("POST", API, payload)
    print(f"OK: релиз создан → {result.get('html_url')}")
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Управление GitHub релизами Astra AI")
    p.add_argument("--tag", help="Тег (например v2.2.0)")
    p.add_argument("--title", help="Заголовок релиза")
    p.add_argument("--body", help="Описание релиза (файл .md или текст)")
    p.add_argument("--body-file", help="Файл с описанием релиза")
    p.add_argument("--draft", action="store_true", help="Черновик")
    p.add_argument("--prerelease", action="store_true", help="Пре-релиз")
    p.add_argument("--list", action="store_true", help="Список релизов")

    args = p.parse_args()

    if args.list:
        list_releases()
        sys.exit(0)

    if not args.tag:
        print("Укажите --tag (или --list для списка)")
        sys.exit(1)

    body = args.body or ""
    if args.body_file:
        body = Path(args.body_file).read_text(encoding="utf-8")

    create_release(args.tag, args.title or args.tag, body, args.draft, args.prerelease)
