# Recovery audit — Al Rajhi Takaful SEO AI project

_Based exclusively on the 17 uploaded files plus the user's statement that the branches belong to one evolving project. The staging source files are unmodified copies._

## In-scope code

| Branch | Source files | Status |
|---|---|---|
| Core SEO workflow | `main.py`, `agent_1_reader.py`, `agent_2_analyst.py`, `agent_3_critic.py`, `utils.py` | Entry point and pipeline stages present; live execution not validated |
| Vision experiments | `experiments/vision/agent_1_screenshot.py`, `test_1_2.py`, `view_results.py`, `agent_2_classifier.py` | Separate experimentation; not integrated into `main.py` |

## Archived evidence (in separate private originals backup; **not** in this repository)

- `agent_1_output.json` — Apr 22, 2026, 14:43:21
- `agent_2_output.json` — Apr 22, 2026, 14:34:46, links to an earlier Agent 1 timestamp than the supplied Agent 1 file
- `agent_3_output.json` — Apr 22, 2026, 14:35:30, `overall_status=partially_ready`, `next_agent_handoff.can_generate=false`
- `agent_2_visual_output.json` — Apr 23, 2026, 15:38:19, eight result entries (content not independently verified)
- `agent_2_classifier_output.json` — Apr 23, 2026, 16:07:49, eight result entries with four recorded errors
- `google_trends_keywords.csv` — 29 records, producing script not provided
- `seo_descriptions.csv` — four generated descriptions, producing script not provided
- `requirements(4).txt` — four dependencies, incomplete versus actual imports

## Known gaps and risks

1. **System integration:** Vision scripts do not feed into the main three-stage pipeline. Do not describe the integrated architecture as completed.
2. **Content generation:** output handoff references a future downstream generation step, but no generating script was uploaded. Recorded critic decision did not permit generation on that run.
3. **Extraction quality:** a nominally successful fetch can have thin `body_content`. The archived vehicle page contains only 17 body characters. Add explicit quality gates before LLM analysis.
4. **JSON parsing:** the source `fix_json()` helper attempts to close brackets but does not validate semantic completeness of repaired records.
5. **Model input:** `agent_3_critic.py` truncates a JSON string to 3,000 characters; this may drop evidence.
6. **Measurement:** no Google Search Console report, analytics baseline or independently verified impact metric was uploaded.
7. **Environment:** dependencies are newly enumerated but version compatibility and browser setup have not been tested. The original code uses network, hosted LLMs, and third-party web pages.
8. **Disclosure:** there is no confirmed permission to publish employer-authored code, source outputs, or internal business context.

## Staging actions taken

- Preserved all 17 original files unchanged in a separate **private** backup, with SHA-256 checksums.
- Copied the nine Python source files without edits into a GitHub-style tree (core at root; vision scripts in `experiments/vision/`).
- Added README, `.gitignore`, `.env.example`, a consolidated `requirements.txt`, this technical audit, and a local static-check script.
- Kept real historical JSON and CSV files outside the GitHub staging package.
- Did not run network, LLM, scraping or deployment tests. Did not create/push a GitHub repository.

## Recommendation

First confirm the scope of publishable intellectual property. Next independently test the existing core code against approved/public test pages and validate JSON stage boundaries. Only afterward prepare a public, reproducible case study with authorized data and substantiated results.
