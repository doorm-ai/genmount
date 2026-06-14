# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 DOORM AI PTE. LTD. and Genmount OS Contributors

from __future__ import annotations

import typer

from genmount.cli import app
from genmount.errors import GenmountError


def main() -> None:
    try:
        app()
    except GenmountError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise SystemExit(exc.exit_code) from exc


if __name__ == "__main__":
    main()
