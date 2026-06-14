# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 DOORM AI PTE. LTD. and Genmount OS Contributors

from __future__ import annotations

import typer

from genmount import ollama
from genmount.api import CloudClient
from genmount.config import Config
from genmount.errors import OllamaUnavailableError


def run(
    prompt: str = typer.Argument(..., help="your message"),
    cloud: bool = typer.Option(False, "--cloud", help="route to the cloud model"),
) -> None:
    cfg = Config.load()

    if cloud:
        typer.echo(CloudClient(cfg).chat(prompt))
        return

    ollama.require_up(cfg.ollama_host)
    if not ollama.has_model(cfg.ollama_host, cfg.model_tag):
        raise OllamaUnavailableError(
            f"Local model '{cfg.model_tag}' is not present in Ollama.\n"
            f"  Get one (gated, free) from Hugging Face, e.g.\n"
            f"    https://huggingface.co/doorm-ai/Llama-3.2-3B-genmount-tcm-GGUF\n"
            f"  then load it:  ollama create {cfg.model_tag} -f Modelfile   (FROM ./<file>.gguf)\n"
            f"  (one-command `genmount sync` is coming)"
        )

    from ollama import Client

    resp = Client(host=cfg.ollama_host).chat(
        model=cfg.model_tag,
        messages=[{"role": "user", "content": prompt}],
    )
    typer.echo(resp.message.content)
    typer.secho(
        "\n(Educational / reference only — not a diagnosis or prescription.)",
        fg=typer.colors.BRIGHT_BLACK,
    )
