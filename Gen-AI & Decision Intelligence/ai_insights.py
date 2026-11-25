"""Evidence-based insights: Python computes numbers, the LLM only explains them."""
import json
import os
import re

MODEL = os.environ.get("NEXLYTICS_MODEL", "gpt-4o-mini")

SYSTEM_PROMPT = (
    "You are an expert business intelligence advisor for NEXLYTICS. "
    "Base your explanations ONLY on the provided JSON metrics. "
    "Do not invent statistics, percentages, dates or events that are not in the data. "
    "Return ONLY valid JSON: {\"summary\": str, \"recommendations\": [str, str]}."
)


def call_llm_json(system_prompt, user_prompt, timeout=15):
    """Call the chat API and return parsed JSON. Raises on any failure (caller falls back)."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")
    from openai import OpenAI
    client = OpenAI(api_key=api_key, timeout=timeout)
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "system", "content": system_prompt},
                  {"role": "user", "content": user_prompt}],
        temperature=0.1,
        response_format={"type": "json_object"},
    )
    return json.loads(resp.choices[0].message.content)


_NUM = re.compile(r"-?\d[\d,]*\.?\d*")


def _extract_numbers(obj):
    return {round(float(m.replace(",", "")), 2) for m in _NUM.findall(str(obj)) if m.strip("-,.")}


def numbers_are_grounded(llm_output, source_data, free_small_ints=5):
    """True if every number in the LLM output appears in the source data (list numbering 1..5 is ignored)."""
    allowed = _extract_numbers(source_data)
    allowed |= {round(abs(x), 2) for x in allowed}
    for n in _extract_numbers(llm_output):
        if n in allowed or (float(n).is_integer() and 0 <= n <= free_small_ints):
            continue
        return False
    return True


def fallback_insight(kpi_data, anomaly_data):
    """Rule-based text used when the LLM fails, times out, or invents numbers."""
    kpis = ", ".join(f"{k}: {v}" for k, v in kpi_data.items())
    anomalies = anomaly_data if anomaly_data else "no anomalies flagged"
    return {
        "source": "template",
        "summary": f"Key metrics - {kpis}. Anomalies: {anomalies}.",
        "recommendations": [
            "Review the flagged anomalies before making pricing or stock decisions.",
            "Check the Decision Readiness grade before acting on any forecast.",
        ],
    }


def generate_business_insight(kpi_data, anomaly_data):
    """Returns dict with summary + recommendations; always returns something usable."""
    payload = {"kpis": kpi_data, "anomalies": anomaly_data}
    try:
        data = call_llm_json(SYSTEM_PROMPT, json.dumps(payload, default=str))
        if not isinstance(data.get("recommendations"), list) or "summary" not in data:
            raise ValueError("response missing required keys")
        if not numbers_are_grounded(data, payload):
            raise ValueError("response contains numbers not in the input data")
        data["source"] = "llm"
        return data
    except Exception as exc:  # API down, timeout, bad JSON, hallucinated numbers
        result = fallback_insight(kpi_data, anomaly_data)
        result["fallback_reason"] = str(exc)
        return result
