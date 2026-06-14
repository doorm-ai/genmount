# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 DOORM AI PTE. LTD. and Genmount OS Contributors

from __future__ import annotations

import typer

from genmount import api, config, ollama
from genmount.api import CloudClient
from genmount.config import Config, TokenStore


def run(
    model: str = typer.Option(
        None, "--model", help="adapter version to install (default: all available)"
    ),
    use: bool = typer.Option(
        False, "--use", help="set the installed model as the default chat model"
    ),
) -> None:
    cfg = Config.load()
    tokens = TokenStore.load()
    client = CloudClient(cfg, jwt=tokens.jwt)

    data = client.list_models()
    raw = data.get("entries", [])
    entries = [e for e in raw if isinstance(e, dict) and e.get("gguf_url")]
    if model:
        entries = [e for e in entries if e.get("adapter_version") == model]
    if not entries:
        typer.echo("No downloadable models are available for this account.")
        return

    installed: list[str] = []
    for entry in entries:
        ver = str(entry["adapter_version"])
        sha = str(entry["sha256"])
        url = str(entry["gguf_url"])
        dest = config.data_dir() / "models" / ver / f"{ver}.gguf"
        if dest.exists() and api.file_sha256(dest) == sha.lower():
            typer.echo(f"{ver}: already downloaded (sha256 verified), skipping download.")
        else:
            size_gb = float(entry.get("size_bytes", 0)) / 1e9
            typer.echo(f"Downloading {ver} ({size_gb:.2f} GB)...")
            api.download_model(url, dest, sha)
            typer.secho(f"{ver}: downloaded, sha256 verified.", fg=typer.colors.GREEN)
        name = f"genmount-{ver}"
        ollama.install_gguf(cfg.ollama_host, name, dest)
        installed.append(name)
        typer.secho(f"Installed into Ollama as '{name}'.", fg=typer.colors.GREEN)

    if use and installed:
        cfg.model_tag = installed[-1]
        cfg.save()
        typer.echo(f"Default chat model set to '{installed[-1]}'.")
    typer.secho(
        "(Educational / reference only — not a diagnosis or prescription.)",
        fg=typer.colors.BRIGHT_BLACK,
    )
