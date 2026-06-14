# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 DOORM AI PTE. LTD. and Genmount OS Contributors

from __future__ import annotations

import platform
import sys

import typer

from genmount import __version__, auth, ollama
from genmount.config import Config, config_path


def _line(label: str, detail: str, ok: bool | None) -> bool:
    mark = {True: "PASS", False: "FAIL", None: "WARN"}[ok]
    color = {True: typer.colors.GREEN, False: typer.colors.RED, None: typer.colors.YELLOW}[ok]
    typer.secho(f"  [{mark}] ", fg=color, nl=False)
    typer.echo(f"{label}: {detail}")
    return ok is not False


def run(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="show extra detail"),
) -> None:
    cfg = Config.load()
    typer.secho(f"genmount {__version__}", bold=True)

    ok = True
    ok &= _line("Python", platform.python_version(), sys.version_info >= (3, 10))
    cfg_exists = config_path().exists()
    ok &= _line(
        "Config file",
        str(config_path()) if cfg_exists else f"{config_path()} — run `genmount init`",
        cfg_exists or None,
    )
    ok &= _line(
        "Device key",
        "present" if auth.device_key_exists() else "missing — run `genmount init`",
        auth.device_key_exists() or None,
    )

    up = ollama.is_up(cfg.ollama_host)
    ver = ollama.version(cfg.ollama_host) if up else None
    ok &= _line(
        "Ollama",
        f"{cfg.ollama_host}" + (f" (v{ver})" if ver else " — not running"),
        up or None,
    )
    if up:
        ok &= _line(
            "Local model",
            cfg.model_tag
            if ollama.has_model(cfg.ollama_host, cfg.model_tag)
            else f"{cfg.model_tag} not pulled (ollama pull {cfg.model_tag})",
            ollama.has_model(cfg.ollama_host, cfg.model_tag) or None,
        )

    if verbose:
        typer.echo(f"\n  cloud endpoint: {cfg.cloud_endpoint}")
        typer.echo(f"  device id: {cfg.device_id or '(not activated)'}")

    typer.echo("")
    if ok:
        typer.secho("All required checks passed.", fg=typer.colors.GREEN)
    else:
        typer.secho("Some checks failed — see above.", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)
