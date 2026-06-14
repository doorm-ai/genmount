# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 DOORM AI PTE. LTD. and Genmount OS Contributors

from __future__ import annotations

import typer

from genmount.commands import chat, doctor, init, sync, upgrade

app = typer.Typer(
    name="genmount",
    help="Genmount OS client — local + cloud inference.",
    no_args_is_help=True,
    add_completion=True,
)

app.command("init", help="Generate the device key + write config; optionally activate online.")(
    init.run
)
app.command("doctor", help="Check Python, Ollama, config, and device key health.")(doctor.run)
app.command("chat", help="Send a prompt to the local model (default) or the cloud (--cloud).")(
    chat.run
)
app.command("sync", help="Download + install your account's models into Ollama (coming soon).")(
    sync.run
)
app.command("upgrade", help="Report installed vs latest PyPI version.")(upgrade.run)
