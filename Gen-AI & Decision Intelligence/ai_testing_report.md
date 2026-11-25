# AI Testing Report - NEXLYTICS (Naveen: GenAI & Decision Intelligence)

## Scope
`ai_insights.py`, `decision_readiness.py`, `experiment_designer.py`, `what_if_simulation.py`

## Golden rule enforcement
Python computes every number. The LLM only explains. `numbers_are_grounded()` extracts every number from
the LLM response and rejects it if any number is not present in the input KPIs/anomalies (list numbers 1-5 ignored).
On rejection, API error, timeout, missing key or bad JSON, a rule-based template is returned instantly
(`source: "template"`, with `fallback_reason`).

## Reliability settings
- temperature 0.1, `response_format=json_object`, 15 s timeout
- Required keys checked: `summary`, `recommendations`
- API key from `OPENAI_API_KEY` env var only; no key means automatic fallback (demo never crashes)

## Tests (test_nexlytics_ai.py) - 6 passed
| Area | Check | Result |
|---|---|---|
| Simulation | 1000 rev, 800 cost, +10% price, -5% cost gives rev 1100, cost 760, profit 340, margin 30.91% | PASS |
| Simulation | zero revenue returns margin None; -100% change and string input rejected | PASS |
| Readiness | HIGH / MEDIUM / LOW grades and all four penalties (sample, missing, age, forecast error) | PASS |
| Experiments | SCALE / MODIFY / STOP / EXTEND rules, margin guardrail overrides lift | PASS |
| Grounding | grounded text accepted, invented 15% rejected | PASS |
| Fallback | no API key returns template output | PASS |

## Not yet tested (needs live key / team data)
- Real LLM calls with Bhargavi's KPI output and Tauz's anomaly format
- `readiness_from_dataframe` on Kadambini's cleaned dunnhumby tables
- Streamlit / Power BI rendering by Hasan

## Known limitations
- Simulation assumes linear scaling (no price elasticity)
- Number check is by value, so an LLM could reuse a real number in the wrong context; keep prompts narrow
