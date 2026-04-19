"""
Сборка релизного exe с встроенными API-ключами.

Использование:
  1. Создай secrets.py (скопируй из secrets.example.py, впиши реальные ключи)
  2. Запусти: python build.py
  3. Готовый exe будет в dist/calcraft-bot.exe

secrets.py никогда не коммитится в git.
"""
import base64
import random
import subprocess
import sys
from pathlib import Path

_PLACEHOLDER = """\
# Dev placeholder — запусти build.py чтобы встроить реальные ключи.
CLIENT_ID     = ""
CLIENT_SECRET = ""
"""


def _encode(text: str, key: bytes) -> bytes:
    raw   = text.encode("utf-8")
    xored = bytes(b ^ key[i % len(key)] for i, b in enumerate(raw))
    return base64.b64encode(xored)


def main():
    if not Path("secrets.py").exists():
        print("Ошибка: secrets.py не найден.")
        print("Скопируй secrets.example.py → secrets.py и впиши реальные ключи.")
        sys.exit(1)

    ns: dict = {}
    exec(Path("secrets.py").read_text("utf-8"), ns)  # noqa: S102
    cid = ns.get("CLIENT_ID", "").strip()
    sec = ns.get("CLIENT_SECRET", "").strip()

    if not cid or not sec:
        print("Ошибка: CLIENT_ID и CLIENT_SECRET в secrets.py не должны быть пустыми.")
        sys.exit(1)

    key   = bytes(random.randint(1, 255) for _ in range(32))
    i_enc = _encode(cid, key)
    s_enc = _encode(sec, key)

    creds_code = (
        "import base64 as _b\n"
        f"_I = {i_enc!r}\n"
        f"_S = {s_enc!r}\n"
        f"_K = {key!r}\n"
        "def _x(d):\n"
        "    return bytes(b^_K[i%len(_K)]for i,b in enumerate(_b.b64decode(d))).decode()\n"
        "CLIENT_ID=_x(_I)\n"
        "CLIENT_SECRET=_x(_S)\n"
    )

    print("Генерирую credentials.py...")
    Path("credentials.py").write_text(creds_code, encoding="utf-8")

    print("Запускаю PyInstaller...")
    result = subprocess.run([
        sys.executable, "-m", "PyInstaller",
        "--onefile", "--windowed",
        "--name", "calcraft-bot",
        "main.py",
    ])

    print("Сбрасываю credentials.py к пустышке...")
    Path("credentials.py").write_text(_PLACEHOLDER, encoding="utf-8")

    if result.returncode == 0:
        print("\nГотово! Exe в dist/calcraft-bot.exe")
    else:
        print("\nPyInstaller завершился с ошибкой.")

    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
