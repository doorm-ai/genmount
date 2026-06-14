# genmount

> **Genmount OS client — run Genmount models locally, with an authenticated cloud fallback.**

[![PyPI](https://img.shields.io/pypi/v/genmount)](https://pypi.org/project/genmount/)
[![Python](https://img.shields.io/pypi/pyversions/genmount)](https://pypi.org/project/genmount/)
[![License: AGPL-3.0](https://img.shields.io/badge/License-AGPL--3.0--or--later-blue.svg)](https://www.gnu.org/licenses/agpl-3.0.html)
[![Last Commit](https://img.shields.io/github/last-commit/doorm-ai/genmount)](https://github.com/doorm-ai/genmount/commits/main)
[![Stars](https://img.shields.io/github/stars/doorm-ai/genmount?style=social)](https://github.com/doorm-ai/genmount/stargazers)

`genmount` is the **user-side thin client** for [Genmount OS](https://genmount.com). It runs models **locally on your machine via [Ollama](https://ollama.com)** and routes hard cases to an **authenticated cloud** — shipping **no model weights** and running **no server kernel** on your device.

```bash
pip install genmount
```

---

## 🚀 Quickstart

```bash
pip install genmount
genmount doctor                 # check Python, Ollama, config

# Get a model (gated, free) from Hugging Face, then load it into Ollama:
#   https://huggingface.co/doorm-ai/Llama-3.2-3B-genmount-tcm-GGUF
ollama create genmount-tcm -f Modelfile   # FROM ./<file>.gguf; PARAMETER repeat_penalty 1.15

genmount chat "What does the classical literature say about ..."   # runs 100% locally
```

**No account needed for local use** — `chat` runs entirely on your machine via Ollama. Registration is **only for cloud features** (model sync / cloud fallback — rolling out):

```bash
genmount init --register        # optional: collects name / org / email / intended use
```

Your device keypair is generated **locally** and never leaves your machine.

---

## 🧰 Commands

| Command | Status | What it does |
|---|---|---|
| `genmount doctor` | ✅ | Health check: Python, Ollama, config, device key — works offline |
| `genmount init` | ✅ | Generate a local device keypair + write config; `--register` activates against the cloud |
| `genmount chat "…"` | ✅ local | One-shot prompt to your local Ollama model |
| `genmount upgrade [--check]` | ✅ | Compare the installed version against the latest on PyPI |
| `genmount chat --cloud` | ⏳ | Route hard cases to authenticated cloud inference |
| `genmount sync` | ⏳ | Download + install the models your account can access into Ollama (sha256-verified) |

---

## 🔐 Auth — zero shared secrets

- A per-device **ED25519 keypair** is generated **on your machine**; the private key never leaves it.
- An activation code exchanges your **public key** for a short-lived **JWT** plus per-request signatures.
- By design, the client **cannot** disable or bypass server-side audit, redaction, or rate limiting.

---

## 🔭 Where this client sits

| Tier | Scope | This repo? |
|---|---|---|
| **L3** Production | Production weights, clinical adapters, partner data | 🔒 Closed |
| **L2** Finetune-Workbench | Training pipeline + quality gates | Sibling repo (pending) |
| **L1** Platform | Gateway · state space · audit · redactor · runtime | Sibling repo (pending) |
| **Client** | Local runner + authenticated cloud glue | **← You are here** |

The client is **base-model agnostic** — it talks to Genmount OS over a stable, authenticated API and is not tied to any one model or release schedule.

---

## 📦 Models

Genmount's traditional-medicine **education** models are distributed (gated, free registration) on Hugging Face — *Built with Llama*:

- [`doorm-ai/Llama-3.2-3B-genmount-tcm-GGUF`](https://huggingface.co/doorm-ai/Llama-3.2-3B-genmount-tcm-GGUF)
- [`doorm-ai/Llama-3.2-3B-genmount-ayurveda-GGUF`](https://huggingface.co/doorm-ai/Llama-3.2-3B-genmount-ayurveda-GGUF)
- [`doorm-ai/Llama-3.2-3B-genmount-tibetan-GGUF`](https://huggingface.co/doorm-ai/Llama-3.2-3B-genmount-tibetan-GGUF)

Run with `repeat_penalty 1.15` (the `genmount` client sets this for you).

---

## ⚖️ Scope & safety

Outputs are **educational / reference** material over classical texts — **not** a diagnosis, prescription, dosing, or treatment recommendation, and **not** a medical device (non-SaMD). Always consult a qualified practitioner.

---

## 📡 Stay updated

- **⭐ Star** to follow releases · **👁 Watch → Custom → Releases** for drop notifications
- 💬 [Discussions](https://github.com/doorm-ai/genmount/discussions) · 📬 [Issues](https://github.com/doorm-ai/genmount/issues)

---

## 📚 Companion artifacts

- 🌐 **[genmount.com](https://genmount.com)** — product site
- 🧩 **[Genmount WorldModel-OS](https://github.com/doorm-ai/Genmount-WorldModel-OS)** — L1 platform skeleton (pending public release)
- 🛠 **[Genmount Finetune-Workbench](https://github.com/doorm-ai/Genmount-Finetune-Workbench)** — L2 training workbench (pending)

---

## 💼 Commercial / non-AGPL licensing

For commercial use outside AGPL-3.0-or-later terms, or partner integrations:

📧 **service@doorm.ai**

DOORM AI PTE. LTD. (UEN 202441729W) · Singapore
