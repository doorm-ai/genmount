# Security Policy

## Reporting a vulnerability

Please report security issues **privately** — do **not** open a public issue.

- Email: **service@doorm.ai** (subject: `genmount security`)
- Include: affected version, reproduction steps, and impact.

We aim to acknowledge within a few business days.

## Supported versions

`genmount` is **pre-alpha** (`0.x`). Only the latest release receives fixes.

## Security posture

This client is a deliberately **thin client**:

- **No embedded secrets.** Authentication uses a per-device ED25519 keypair
  generated on your machine at activation; the private key never leaves the
  device, and only the public key is shared with the service. The package
  contains no shared keys, tokens, or credentials.
- **Local key storage.** The private key is written with `0600` permissions
  (POSIX) under the user data directory; on Windows it lives in the per-user
  profile directory.
- **No model weights, no server kernel** are shipped or run locally.
- **Replay-resistant requests.** Cloud calls are signed (`method + path +
  timestamp + nonce + body hash`); the server enforces a timestamp window and a
  nonce cache.
- **Non-diagnostic.** Outputs are educational / reference only and must not be
  relied upon as a diagnosis, prescription, or treatment.

## Releasing

Releases are published to PyPI only via a **manual, reviewed** workflow that
runs a secret scan and a forbidden-term scan before building. The package is
published with PyPI **Trusted Publishing** (no long-lived upload token).
