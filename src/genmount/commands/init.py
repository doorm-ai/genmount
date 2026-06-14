# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 DOORM AI PTE. LTD. and Genmount OS Contributors

from __future__ import annotations

import typer

from genmount import auth
from genmount.api import CloudClient
from genmount.config import Config, TokenStore, config_path
from genmount.errors import CloudUnavailableError


def run(
    code: str = typer.Option(None, "--code", help="activation code from your account"),
    force: bool = typer.Option(False, "--force", help="regenerate the device key"),
    register: bool = typer.Option(
        False, "--register", help="register online and receive an activation code"
    ),
    name: str = typer.Option(None, "--name", help="your name (registration)"),
    organization: str = typer.Option(None, "--org", help="your organization (registration)"),
    email: str = typer.Option(None, "--email", help="contact email (registration)"),
    use_case: str = typer.Option(None, "--use-case", help="intended use (registration)"),
) -> None:
    if auth.device_key_exists() and not force:
        typer.echo("Device key already present (use --force to regenerate).")
    else:
        auth.generate_device_key(overwrite=force)
        typer.secho(
            "Generated device key — the private key stays on this machine.",
            fg=typer.colors.GREEN,
        )

    cfg = Config.load()
    cfg.save()
    typer.echo(f"Config written: {config_path()}")

    if register and not code:
        name = name or typer.prompt("Name")
        organization = organization or typer.prompt("Organization")
        email = email or typer.prompt("Email")
        use_case = use_case or typer.prompt("Intended use")
        typer.echo(
            "Models are licensed under the published LICENSE terms and are "
            "educational / reference only — not a diagnosis or prescription."
        )
        if not typer.confirm("Accept the LICENSE terms?"):
            raise typer.Exit(code=1)
        if not typer.confirm("Acknowledge the educational-use notice?"):
            raise typer.Exit(code=1)
        try:
            result = CloudClient(cfg).register(
                name=name, organization=organization, email=email, use_case=use_case
            )
            issued = result.get("activation_code")
            if isinstance(issued, str) and issued:
                code = issued
                typer.secho("Registered — activation code issued.", fg=typer.colors.GREEN)
            else:
                typer.secho("Registration response had no code.", fg=typer.colors.RED)
        except CloudUnavailableError as exc:
            typer.secho(f"(offline) {exc}", fg=typer.colors.YELLOW)

    if code:
        try:
            result = CloudClient(cfg).activate(code)
            device_id = result.get("device_id")
            tier = result.get("tier")
            jwt = result.get("jwt")
            refresh_token = result.get("refresh_token")
            cfg.device_id = device_id if isinstance(device_id, str) else None
            cfg.tier = tier if isinstance(tier, str) else None
            cfg.save()
            TokenStore(
                jwt=jwt if isinstance(jwt, str) else None,
                refresh_token=refresh_token if isinstance(refresh_token, str) else None,
            ).save()
            typer.secho("Device activated with the cloud.", fg=typer.colors.GREEN)
        except CloudUnavailableError as exc:
            typer.secho(f"(offline) {exc}", fg=typer.colors.YELLOW)

    typer.echo("\ninit complete.")
    typer.secho("Next:", fg=typer.colors.CYAN, bold=True)
    typer.echo("  1. Get a model (gated, free) from Hugging Face, e.g.:")
    typer.echo("       https://huggingface.co/doorm-ai/Llama-3.2-3B-genmount-tcm-GGUF")
    typer.echo("       (also -ayurveda-GGUF / -tibetan-GGUF)")
    typer.echo("     then load it into Ollama:")
    typer.echo("       ollama create genmount-tcm -f Modelfile")
    typer.echo("       # Modelfile: FROM ./<file>.gguf  +  PARAMETER repeat_penalty 1.15")
    typer.echo("       (one-command `genmount sync` is coming)")
    typer.echo('  2. Run it:        genmount chat "..."')
    typer.echo("  3. Verify setup:  genmount doctor")
