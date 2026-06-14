# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 DOORM AI PTE. LTD. and Genmount OS Contributors

from __future__ import annotations

import httpx
import typer

from genmount import __version__

_PYPI_JSON = "https://pypi.org/pypi/genmount/json"


def _latest_pypi_version() -> str | None:
    try:
        resp = httpx.get(_PYPI_JSON, timeout=10.0)
        if resp.status_code == 200:
            version = resp.json().get("info", {}).get("version")
            return version if isinstance(version, str) else None
    except (httpx.HTTPError, OSError, ValueError):
        return None
    return None


def run(
    check: bool = typer.Option(False, "--check", help="only check, do not print upgrade hint"),
) -> None:
    typer.echo(f"installed: {__version__}")
    latest = _latest_pypi_version()
    if latest is None:
        typer.secho("Could not reach PyPI to check the latest version.", fg=typer.colors.YELLOW)
        return
    typer.echo(f"latest on PyPI: {latest}")
    if latest == __version__:
        typer.secho("You are up to date.", fg=typer.colors.GREEN)
    elif not check:
        typer.echo("To upgrade:  pip install -U genmount")
