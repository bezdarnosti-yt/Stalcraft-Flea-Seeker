import logging
import sys
from datetime import datetime
from pathlib import Path


def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).parent


def setup() -> Path:
    log_dir = _base_dir() / "logs"
    log_dir.mkdir(exist_ok=True)

    # Keep only the 20 most recent log files
    old_logs = sorted(log_dir.glob("*.log"), key=lambda p: p.stat().st_mtime)
    for f in old_logs[:-20]:
        f.unlink(missing_ok=True)

    ts      = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_path = log_dir / f"calcraft-bot_{ts}.log"

    fmt = logging.Formatter("%(asctime)s [%(levelname)-8s] %(name)s: %(message)s")

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(fmt)

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.addHandler(file_handler)

    # In dev (non-frozen) also print to console with UTF-8
    if not getattr(sys, "frozen", False):
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sh = logging.StreamHandler(sys.stdout)
        sh.setFormatter(fmt)
        root.addHandler(sh)

    # Redirect stderr to log — captures PyQt6 slot exceptions in windowed exe
    sys.stderr = _LogWriter(logging.getLogger("stderr"), logging.ERROR)

    # Catch unhandled Python exceptions
    def _excepthook(exc_type, exc_value, exc_tb):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return
        logging.critical("Необработанное исключение", exc_info=(exc_type, exc_value, exc_tb))

    sys.excepthook = _excepthook

    log = logging.getLogger("app")
    log.info("=" * 60)
    log.info("Запуск Stalcraft Flea Seeker")
    log.info("Python %s | платформа: %s", sys.version.split()[0], sys.platform)
    log.info("Лог-файл: %s", log_path)

    return log_path


class _LogWriter:
    """Перенаправляет writes() в указанный logger."""

    def __init__(self, logger: logging.Logger, level: int):
        self._logger = logger
        self._level  = level
        self._buf    = ""

    def write(self, msg: str):
        self._buf += msg
        while "\n" in self._buf:
            line, self._buf = self._buf.split("\n", 1)
            if line.strip():
                self._logger.log(self._level, line.rstrip())

    def flush(self):
        if self._buf.strip():
            self._logger.log(self._level, self._buf.rstrip())
            self._buf = ""

    def fileno(self):
        raise OSError("LogWriter не имеет файлового дескриптора")
