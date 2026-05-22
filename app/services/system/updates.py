import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from app.core.config import Settings

SAFE_GIT_REF = re.compile(r"^[A-Za-z0-9._/-]+$")


class AdminUpdateError(RuntimeError):
    """Base class for admin-triggered update errors."""


class AdminUpdateDisabled(AdminUpdateError):
    """Raised when self-update is not enabled by deployment settings."""


class AdminUpdateBusy(AdminUpdateError):
    """Raised when another update owns the update lock."""


@dataclass(frozen=True)
class AdminUpdateState:
    enabled: bool
    running: bool
    ref: str
    log_tail: list[str]


class AdminUpdateManager:
    def status(self, settings: Settings) -> AdminUpdateState:
        return AdminUpdateState(
            enabled=settings.admin_updates_enabled,
            running=Path(settings.admin_update_lock_path).exists(),
            ref=settings.admin_update_ref,
            log_tail=self._tail(Path(settings.admin_update_log_path)),
        )

    def start(self, settings: Settings) -> AdminUpdateState:
        if not settings.admin_updates_enabled:
            raise AdminUpdateDisabled("Admin self-update is disabled.")
        if not SAFE_GIT_REF.fullmatch(settings.admin_update_ref):
            raise AdminUpdateError("Configured update ref is invalid.")

        command_path = Path(settings.admin_update_command)
        if not command_path.is_file():
            raise AdminUpdateError("Configured update command does not exist.")
        log_path = Path(settings.admin_update_log_path)
        lock_path = Path(settings.admin_update_lock_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        lock_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            lock_fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError as exc:
            raise AdminUpdateBusy("Another update is already running.") from exc

        try:
            with os.fdopen(lock_fd, "w", encoding="utf-8") as lock_file:
                lock_file.write("admin-api\n")
            with log_path.open("a", encoding="utf-8") as log_file:
                subprocess.Popen(
                    ["bash", str(command_path), settings.admin_update_ref],
                    cwd=str(command_path.parent.parent),
                    env={
                        **os.environ,
                        "VPNBOTX_ADMIN_UPDATE_LOCK_HELD": "1",
                        "ADMIN_UPDATE_LOCK_PATH": str(lock_path),
                        "ADMIN_UPDATE_LOG_PATH": str(log_path),
                    },
                    stdout=log_file,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                )
        except (OSError, ValueError) as exc:
            lock_path.unlink(missing_ok=True)
            raise AdminUpdateError("Failed to start the update command.") from exc

        return self.status(settings)

    @staticmethod
    def _tail(path: Path, limit: int = 40) -> list[str]:
        if not path.exists():
            return []
        return path.read_text(encoding="utf-8", errors="replace").splitlines()[-limit:]


admin_update_manager = AdminUpdateManager()
