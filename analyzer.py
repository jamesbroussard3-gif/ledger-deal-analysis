"""
Core analyzer logic — deal analysis edition.

Architecture (per professor feedback on LLM math hallucination):
- Python does ALL the math (deterministic, no hallucination risk).
- The LLM does ONLY the extraction (reading numbers from text) and
  the narrative interpretation (analysis, trends, risks).

The LLM is framed as a senior deal analyst, applicable to IB, PE, VC,
and corporate development contexts.
"""

import json
import os

from google import genai
from google.genai import types

client = genai.Client()
MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
JSON_CONFIG = types.GenerateContentConfig(response_mime_type="application/json")


# -----------------------------------------------------------------------------
# STEP 1: EXTRACTION — Parse raw input into structured data.
# -----------------------------------------------------------------------------

EXTRACTION_PROMPT = """You are a financial data extraction assistant. Read the financial statements provided and extract the line items into the exact JSON schema below.

CRITICAL RULES:
- Extract numbers exactly as written. Do NOT calculate or derive any values.
- If a value is in millions/thousands, convert to the actual number (e.g., "$1,234M" -> 1234000000).
- Use null for any value not present in the source.
- Negative values (like net losses) should be negative numbers.
- If multiple time periods are present, extract each one as a separate period in the array.
- Period labels should be like "FY2024", "Q3 2024", "2023", etc., based on what's in the source.
- Return ONLY valid JSON with no markdown fences, no commentary.

SCHEMA:
{
  "company_name": "string or null",
  "currency": "string (e.g., USD, EUR) or null",
  "periods": [
    {
      "period_label": "string",
      "income_statement": {
        "revenue": number or null,
        "cost_of_revenue": number or null,
        "gross_profit": number or null,
        "operating_expenses": number or null,
        "operating_income": number or null,
        "interest_expense": number or null,
        "net_income": number or null
      },
      "balance_sheet": {
        "current_assets": number or null,
        "inventory": number or null,
        "total_assets": number or null,
        "current_liabilities": number or null,
        "total_liabilities": number or null,
        "total_equity": number or null
      },
      "cash_flow": {
        "operating_cash_flow": number or null,
        "investing_cash_flow": number or null,
        "financing_cash_flow": number or null,
        "capital_expenditures": number or null
      }
    }
  ]
}

FINANCIAL DATA TO EXTRACT:
"""


def extract_financial_data(raw_text: str) -> dict:
    """Parse raw financial text into structured JSON. LLM reads only — no math."""
    response = client.models.generate_content(
        model=MODEL,
        contents=EXTRACTION_PROMPT + raw_text,
        config=JSON_CONFIG,
    )
    text = (response.text or "").strip()
    return json.loads(text)


# -----------------------------------------------------------------------------
# STEP 2: CALCULATIONS — Pure Python math. No LLM involvement.
# -----------------------------------------------------------------------------


def safe_divide(numerator, denominator):
    """Divide two numbers, returning None if either is None or denominator is zero."""
    if numerator is None or denominator is None or denominator == 0:
        return None
    return numerator / denominator


def calculate_ratios(period: dict) -> dict:
    """Calculate financial ratios for a single period. All math in deterministic Python."""
    income = period.get("income_statement", {}) or {}
    balance = period.get("balance_sheet", {}) or {}

    revenue = income.get("revenue")
    cost_of_revenue = income.get("cost_of_revenue")
    gross_profit = income.get("gross_profit")
    operating_income = income.get("operating_income")
    interest_expense = income.get("interest_expense")
    net_income = income.get("net_income")

    current_assets = balance.get("current_assets")
    inventory = balance.get("inventory")
    total_assets = balance.get("total_assets")
    current_liabilities = balance.get("current_liabilities")
    total_liabilities = balance.get("total_liabilities")
    total_equity = balance.get("total_equity")

    if gross_profit is None and revenue is not None and cost_of_revenue is not None:
        gross_profit = revenue - cost_of_revenue

    quick_assets = None
    if current_assets is not None and inventory is not None:
        quick_assets = current_assets - inventory
    elif current_assets is not None and inventory is None:
        quick_assets = current_assets

    return {
        "liquidity": {
            "current_ratio": safe_divide(current_assets, current_liabilities),
            "quick_ratio": safe_divide(quick_assets, current_liabilities),
        },
        "profitability": {
            "gross_margin": safe_divide(gross_profit, revenue),
            "operating_margin": safe_divide(operating_income, revenue),
            "net_margin": safe_divide(net_income, revenue),
            "return_on_assets": safe_divide(net_income, total_assets),
            "return_on_equity": safe_divide(net_income, total_equity),
        },
        "leverage": {
            "debt_to_equity": safe_divide(total_liabilities, total_equity),
            "debt_to_assets": safe_divide(total_liabilities, total_assets),
            "interest_coverage": safe_divide(operating_income, interest_expense),
        },
        "efficiency": {
            "asset_turnover": safe_divide(revenue, total_assets),
        },
    }


def calculate_trends(periods_with_ratios: list) -> dict:
    """Calculate year-over-year changes between the most recent two periods."""
    if len(periods_with_ratios) < 2:
        return {}

    current = periods_with_ratios[0]
    prior = periods_with_ratios[1]

    def pct_change(new, old):
        if new is None or old is None or old == 0:
            return None
        return (new - old) / abs(old)

    cur_inc = current.get("income_statement", {}) or {}
    prev_inc = prior.get("income_statement", {}) or {}

    return {
        "current_period": current.get("period_label"),
        "prior_period": prior.get("period_label"),
        "revenue_growth": pct_change(cur_inc.get("revenue"), prev_inc.get("revenue")),
        "net_income_growth": pct_change(cur_inc.get("net_income"), prev_inc.get("net_income")),
        "operating_income_growth": pct_change(
            cur_inc.get("operating_income"), prev_inc.get("operating_income")
        ),
    }


# -----------------------------------------------------------------------------
# STEP 3: NARRATIVE — Deal-analyst commentary from calculated numbers.
# -----------------------------------------------------------------------------

NARRATIVE_PROMPT = """You are a senior deal analyst. You have been given pre-calculated financial ratios and trend data for {company}. Write a clear, professional analysis suitable for inclusion in a deal memo that could support an investment, acquisition, or strategic transaction decision.

IMPORTANT:
- The ratios provided have ALREADY been calculated correctly. Do NOT recalculate or question them.
- Reference the ratios by their values. Do not invent new numbers.
- Be specific. Avoid generic statements that could apply to any company.
- Professional, direct voice — deal team writing, not textbook writing.
- Plain text only. No markdown syntax inside bullet text.

Return ONLY valid JSON, no markdown fences, no preamble.

{{
  "summary": "A 3-4 sentence executive summary of the company's financial profile.",
  "strengths": ["Investment highlight 1", "Investment highlight 2", "Investment highlight 3"],
  "concerns": ["Area of concern 1", "Area of concern 2", "Area of concern 3"],
  "red_flags": ["Specific key risks warranting further diligence. Empty array if none material."],
  "trend_commentary": "2-3 sentences on what the period-over-period trends indicate about business trajectory. If no trend data, write 'Insufficient periods for trend analysis.'"
}}

DATA:
{data_json}
"""


def generate_narrative(extracted_data: dict, all_ratios: list, trends: dict) -> dict:
    """Send calculated numbers to the LLM for deal-analyst narrative."""
    payload = {
        "company": extracted_data.get("company_name") or "the target",
        "currency": extracted_data.get("currency"),
        "periods": [
            {
                "period_label": period.get("period_label"),
                "raw_data": period,
                "calculated_ratios": ratios,
            }
            for period, ratios in zip(extracted_data.get("periods", []), all_ratios)
        ],
        "trend_analysis": trends if trends else "Only one period provided.",
    }

    prompt = NARRATIVE_PROMPT.format(
        company=extracted_data.get("company_name") or "the target",
        data_json=json.dumps(payload, indent=2),
    )

    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=JSON_CONFIG,
    )
    text = (response.text or "").strip()
    return json.loads(text)


# -----------------------------------------------------------------------------
# FOLLOW-UP CHAT — Analyst Q&A.
# -----------------------------------------------------------------------------

CHAT_SYSTEM_PROMPT = """You are a senior deal analyst assistant. You have access to a company's financial data, pre-calculated ratios, and the analysis already produced. Answer the user's questions clearly and concisely.

CRITICAL FORMATTING RULES:
- Respond in plain text only. Do NOT use markdown formatting.
- Do NOT use asterisks for bold (no **text**).
- Do NOT use asterisks or hyphens for bullet points.
- Do NOT use markdown headers (no ###).
- If you need to list items, write them as short numbered sentences (1. First point. 2. Second point.) or as a flowing paragraph.
- Keep responses tight — 2-4 sentences unless the question demands more.

CONTENT RULES:
- Ratios were calculated correctly in Python. Do not recalculate.
- If asked for hypothetical math (e.g., "what if revenue grew 20%?"), describe the impact qualitatively rather than computing it.
- Stay grounded in the data. Do not invent figures.
- Professional deal-analyst voice.

CONTEXT DATA:
{context_json}
"""


def chat_followup(context: dict, conversation: list) -> str:
    """Handle a follow-up question with the full analysis as context."""
    system_text = CHAT_SYSTEM_PROMPT.format(context_json=json.dumps(context, indent=2))

    contents = []
    for msg in conversation:
        role = "model" if msg["role"] == "assistant" else "user"
        contents.append(
            types.Content(role=role, parts=[types.Part.from_text(text=msg["content"])])
        )

    response = client.models.generate_content(
        model=MODEL,
        contents=contents,
        config=types.GenerateContentConfig(system_instruction=system_text),
    )
    return response.text or ""


# -----------------------------------------------------------------------------
# ORCHESTRATION
# -----------------------------------------------------------------------------


def run_full_analysis(raw_text: str) -> dict:
    """Run the complete pipeline: extract -> calculate -> narrate."""
    extracted = extract_financial_data(raw_text)
    periods = extracted.get("periods", [])
    all_ratios = [calculate_ratios(p) for p in periods]
    trends = calculate_trends(periods)
    narrative = generate_narrative(extracted, all_ratios, trends)
    return {
        "extracted_data": extracted,
        "calculated_ratios": all_ratios,
        "trends": trends,
        "narrative": narrative,
    }
