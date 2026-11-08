# AI-Powered SEO Intelligence — Technical Portfolio Staging

> **PRIVATE REVIEW / NOT YET CLEARED FOR PUBLICATION.** This is a recovery and engineering-review package of scripts supplied by the project contributor. It may contain work created during an Al Rajhi Takaful engagement. Confirm ownership, employer approval, and third-party website terms before publishing any code or examples. This folder is **not** a public-ready release.

## Project overview

Python-based AI-assisted workflow for extracting Arabic insurance webpage content, analyzing competitor SEO signals using a hosted large language model, and assessing readiness for downstream content generation. A separate experimental vision branch captures webpage screenshots and uses a vision-enabled LLM to analyze page design or classify visible phrases.

This is **LLM API orchestration**, not evidence of training or fine-tuning an ML model.

## What the recovered source actually implements

**Core pipeline** (`python main.py`):

1. `agent_1_reader.py`: page fetching (requests, BeautifulSoup, Selenium fallback), Arabic text cleaning, metadata, headings, CTAs, keywords, and extracted text.
2. `agent_2_analyst.py`: Groq-hosted `openai/gpt-oss-120b` analysis of content quality and competitor opportunities.
3. `agent_3_critic.py`: the same LLM critiques analysis and emits a readiness decision and data handoff.
4. `main.py` coordinates these stages and saves their JSON outputs to the current working directory.
5. `utils.py` provides reusable browser and Arabic text helpers.

**Vision experiments** (not connected to `main.py`):

- `experiments/vision/agent_1_screenshot.py`: Playwright full-page screenshot collection.
- `experiments/vision/test_1_2.py`: vision LLM page-design analysis.
- `experiments/vision/view_results.py`: save screenshots and display vision analysis.
- `experiments/vision/agent_2_classifier.py`: screenshot text/phrase classification by language, type, and importance.

The vision branch uses `meta-llama/llama-4-scout-17b-16e-instruct` via Groq in the supplied source. The `agent_2_classifier` label refers to a separate vision experiment, **not** the textual core `agent_2_analyst`.

## Environment setup (manual, not validated end-to-end)

A local Python environment, access to a Chrome/Chromium browser, and a Groq API key are needed to attempt real execution. Public websites and API behavior may have changed since the source's archived April 2026 runs.

```powershell
# Windows PowerShell from repository root
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m playwright install chromium
$env:GROQ_API_KEY = "YOUR_PRIVATE_API_KEY"
python main.py
```

IMPORTANT: the original scripts read environment variables via `os.environ`, rather than loading `.env` files automatically. Never commit real keys.

To run an individual core stage:

```powershell
python main.py --agent 1
python main.py --agent 2  # requires agent_1_output.json
python main.py --agent 3  # requires agent_2_output.json
```

To try vision experiments individually from repository root (requires browser, API access, and network):

```powershell
python experiments/vision/test_1_2.py
python experiments/vision/agent_2_classifier.py
```

Before attempting any live scraping, verify authorization and the applicable website terms.

## Verified vs unverified

- The recovered Python files parse successfully, and the core module names exist in this package.
- A static inspection does NOT establish successful live execution, production deployment, or accuracy of model outputs.
- The archived core critic result was `partially_ready` with `can_generate = false`, not proof of an end-to-end completed content-generation system.
- JSON/CSV output artifacts were **excluded from this GitHub staging copy**. The original backup ZIP holds the intact outputs for private review.
- The scripts for generating the recovered Google Trends CSV and SEO descriptions CSV were not among the uploaded files; no direct Google Search Console integration was found.
- A claimed 24% improvement over 28 days, if used in a CV, requires independent source evidence and careful attribution; it is not demonstrated by these code files.

See [`docs/TECHNICAL_AUDIT.md`](docs/TECHNICAL_AUDIT.md) for a file inventory, timeline and gaps.

## Publication status

**Do not publish this staging repository publicly until intellectual-property, confidentiality, dependency, crawling and website-use reviews are completed.** If permission is not available, build a *new, separately labeled* portfolio demonstration using permissible public/synthetic data and newly authored code.

No license has been supplied because ownership and publication rights have not been established.
