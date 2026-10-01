from typing import Any, Dict, List

from groq import Groq, RateLimitError
import json
import logging
from decimal import Decimal
from django.conf import settings
from .models import FinancialInquirySession

logger = logging.getLogger(__name__)


class AIProviderRateLimitError(Exception):
    def __init__(self, retry_after=None):
        self.retry_after = retry_after if retry_after and str(retry_after).isdigit() else None
        super().__init__('AI provider rate limit reached')


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


def get_jev_combined_prompt(user_financial_data: dict, total_monthly_income: float, DecimalEncoder=None) -> str:
    """
    Jev AI üçün istifadəçinin maliyyə məlumatlarını, büdcə optimallaşdırma qaydalarını və 12 aylıq plan tələblərini birləşdirən vahid prompt.
    """
    if DecimalEncoder:
        formatted_user_data = json.dumps(user_financial_data, cls=DecimalEncoder, ensure_ascii=False, indent=2)
    else:
        formatted_user_data = json.dumps(user_financial_data, ensure_ascii=False, indent=2)

    income_value = format(float(total_monthly_income), '.1f')

    return f"""You are Jev AI, an AI financial budget optimization engine.

Analyze this Azerbaijani user's financial profile (currency: AZN) and produce an optimal, realistic 12-month financial plan.

User Financial Data:
{formatted_user_data}

Total Monthly Income: {income_value} AZN

RULES — MONTHLY TABLE:
- "monthly_table" must have EXACTLY 12 objects (Yanvar to Dekabr, in order).
- Each credit's "months" = remaining months. Once it hits 0, stop including that credit's payment in "credit".
- recurring=true categories stay within ±5% every month. recurring=false categories MUST vary 15-40% month to month (seasonal: clothing spikes spring/autumn/New Year, entertainment/restaurant rises in summer).
- "balance" = income - (all expenses + credit + savings) for that month. Can be negative.

RULES — budget_comparison (one object per category: market, restaurant, transport, utilities, clothing, entertainment, online_shopping, other, credit):
- recommended_monthly_amount stays within ±30% of the user's actual amount unless overspending is clear. Total recommendations must not exceed total monthly income ({income_value} AZN).
- status, in this priority order: (1) credit/utilities are ALWAYS "Prioritet ödəniş". (2) amount=0 → "Qənaətlidir". (3) actual exceeds recommended by >20% → "Yüksək xərc". (4) exceeds by 5-20% → "Diqqət". (5) otherwise → "Uyğundur".

RULES — ai_recommendation (REQUIRED for every single row, never empty, tailored to that row's status):
- "Prioritet ödəniş": remind them to pay on time, e.g. "Kommunal ödənişini vaxtında ödə."
- "Yüksək xərc": name the AZN gap between current and recommended, e.g. "Restoran xərcini 80 AZN azalt."
- "Diqqət": lighter nudge naming the AZN gap, e.g. "Nəqliyyatı 15 AZN qədər azaltsan yaxşı olar."
- "Qənaətlidir": short positive note, e.g. "Bu sahədə əla qənaət edirsən."
- "Uyğundur": short confirmation, e.g. "Xərcin tövsiyə olunan səviyyədədir."

RULES — financial_status (exactly one): "financial_status": Exactly one of: "Risklidir" if expenses+credit ≥ income. "Diqqət" if expenses use >85% of income. "Balanslı" if there's healthy savings margin.

RULES — savings_goals_breakdown: do NOT just divide target/12. Each goal's "priority" is one of "Yuxarı prioritet" (largest share), "Orta prioritet" (moderate share), "Aşağı prioritet" (smallest share). Sum of recommended_monthly_saving across goals must fit within recommended_monthly_savings.

RULES — use the user's own stated preferences to shape everything above:
- financial_assessment: "good_manager"→more ambitious savings target. "sometimes_breaks_plan"→realistic, slightly conservative, some buffer. "nothing_left"→conservative, essentials + small buffer first.
- monthly_savings_ability: "can_save"→align with optimal amount. "sometimes"→somewhat below max. "cannot_save"→start small/achievable, say so in monthly_budget_plan.
- annual_budget_priority tilts the WHOLE plan and must be named explicitly in monthly_budget_plan: "Daha çox qənaət etmək"→push savings higher, trim discretionary categories. "Xərclərə nəzarət etmək"→tighten every category, flag "Yüksək xərc" more readily. "Borcları azaltmaq"→prioritize faster credit payoff over savings. "Gəliri daha düzgün bölüşdürmək"→balanced allocation across categories. "Gözlənilməz xərclərə hazır olmaq"→favor an emergency-fund goal. "Gələcək üçün pul toplamaq"→favor long-term goals (home/education/business) over short-term ones.
- If has_extra_income: lean toward putting extra_income into savings/debt payoff, not treating it like guaranteed salary.

RULES — TEXT: every "ai_recommendation" is ONE short sentence, max ~10-12 words, plain everyday Azerbaijani, no jargon, no lists. Like a text from a friend, not a report. financial_status_description: also 1 short plain sentence. monthly_budget_plan: max 3-4 sentences.

==================================================
JEV AI BUDGET OPTIMIZATION ENGINE INSTRUCTIONS
==================================================

Your task is to analyze all answers provided by the user during the 10-question onboarding process and calculate the "Recommended Budget Allocation" table.

OBJECTIVE:

Create a realistic, personalized, and mathematically balanced monthly budget based on the user's:
- Income
- Additional income
- Current expenses
- Housing situation
- Debt/credit obligations
- Financial goals
- Goal priorities
- Financial habits
- Risk profile
- Other information collected during onboarding

DO NOT use a fixed budgeting formula such as 50/30/20.
The allocation must be calculated individually for each user based on their actual financial situation.

==================================================
1. INCOME BASE
==================================================

Use the user's reliable monthly income as the main calculation base.
Reliable Monthly Income = Main Monthly Income + Reliable Recurring Additional Income
Do not treat irregular or uncertain additional income as fully guaranteed income.
Annual Income = Reliable Monthly Income × 12
The total recommended monthly allocation must never exceed the user's available monthly income.

==================================================
2. BUDGET CATEGORIES
==================================================

Use the following categories in the table:
market, restaurant, transport, utilities, clothing, entertainment, online_shopping, other, credit.
Map the user's current expenses to the appropriate categories.

==================================================
3. CALCULATION FOR EACH CATEGORY
==================================================

For every category calculate:
1. Category
2. Percentage (%)
3. Current Monthly Amount
4. Recommended Monthly Amount
5. Annual Amount
6. Status
7. AI Recommendation

IMPORTANT:
"Current Monthly Amount" must come directly from the user's answers.
Do NOT modify or optimize the Current Monthly Amount.
Only the "Recommended Monthly Amount" should be calculated and optimized by AI.

Calculate Percentage as:
Percentage (%) = Recommended Monthly Amount / Reliable Monthly Income × 100

Calculate Annual Amount as:
Annual Amount = Recommended Monthly Amount × 12

Use the same income base for all calculations.

==================================================
4. ALLOCATION PRIORITY
==================================================

Allocate the available income according to the following priority logic.

FIRST — Essential and mandatory expenses:
- Housing
- Food & Groceries (market)
- Utilities
- Essential transportation
- Minimum credit/debt payments
- Essential healthcare expenses

SECOND — Financial security:
- Savings
- Emergency fund
- Additional repayment of high-interest debt when appropriate

THIRD — User's financial goals:
Allocate money toward the goals selected during onboarding.

FOURTH — Flexible lifestyle expenses:
- Clothing
- Restaurants & Cafes
- Entertainment
- Online Shopping
- Personal Expenses
- Other non-essential expenses

Essential expenses must not be reduced unrealistically in order to fund optional lifestyle categories.

==================================================
5. CREDIT AND DEBT
==================================================

If the user has credit or debt:
- Always include the required minimum monthly payment.
- Never recommend an amount below the mandatory payment.
- Consider the remaining balance.
- Consider the interest rate.
- Consider the remaining repayment period.
- Consider the debt burden relative to monthly income.

If the interest rate is high and the user has sufficient free cash flow, additional debt repayment may be recommended.
However, do not allocate excessive money toward debt if this would prevent the user from covering essential living expenses or maintaining a reasonable financial buffer.

If the user has no credit/debt:
Credit & Debt = 0 AZN.

==================================================
6. FINANCIAL GOALS
==================================================

Consider all financial goals selected by the user.
For each goal consider:
- Target amount
- Priority
- Time horizon, if available
- User's financial capacity

If multiple goals exist, do NOT automatically divide the available money equally.
Higher-priority goals may receive a larger allocation.
However, the allocation must remain financially realistic.

If the user's desired goal cannot realistically be achieved with the available income:
DO NOT create an impossible budget.
Allocate a sustainable amount and explain in the AI Recommendation that the target, timeline, or spending structure may need adjustment.

==================================================
7. SAVINGS
==================================================

If the user's financial situation allows it, allocate part of the monthly income to Savings.
Savings should be treated as a planned budget category, not simply as money left over accidentally at the end of the month.
However, do not create an unrealistic savings amount when essential expenses and mandatory debt payments already consume most of the user's income.
If the user has weak financial reserves, unstable income, or significant obligations, Savings should receive greater priority than unnecessary discretionary spending.

==================================================
8. EXPENSE OPTIMIZATION
==================================================

Do not automatically assume that the user's current spending is optimal.
Analyze each category individually.
Compare: Current Monthly Amount vs. Recommended Monthly Amount.
If a non-essential category consumes an excessive portion of income relative to the user's goals and obligations, reduce its recommended amount.
Examples: Restaurants & Cafes, Entertainment, Online Shopping, Clothing, Other discretionary spending.

IMPORTANT:
Money reduced from one category must not disappear.
Redistribute the released amount toward the most appropriate category, such as:
- Savings
- Financial Goals
- Emergency reserve
- Additional debt repayment
The full available monthly income should therefore be allocated.

==================================================
9. STATUS LOGIC
==================================================

Assign one status to every category in budget_comparison:
Status priority:
1. Credit and Utilities are ALWAYS "Prioritet ödəniş".
2. Current amount = 0 → "Qənaətlidir".
3. Actual exceeds recommended by >20% → "Yüksək xərc".
4. Actual exceeds recommended by 5-20% → "Diqqət".
5. Otherwise → "Uyğundur".

==================================================
10. AI RECOMMENDATION
==================================================

Provide one short and specific recommendation for each category.
Avoid generic recommendations.
BAD: "Try to reduce your expenses."
GOOD: "Reduce restaurant spending from 220 AZN to 150 AZN per month and redirect the additional 70 AZN toward your priority financial goal."
Whenever possible, mention the actual financial impact of the recommendation.

==================================================
11. MANDATORY MATHEMATICAL RULES
==================================================

RULE 1: SUM(Recommended Monthly Amounts) = Reliable Monthly Income.
RULE 2: SUM(Percentage) = 100%
RULE 3: Percentage = Recommended Monthly Amount / Reliable Monthly Income × 100
RULE 4: Annual Amount = Recommended Monthly Amount × 12
RULE 5: The sum of all Annual Amounts must equal: Reliable Monthly Income × 12
RULE 6: No Recommended Monthly Amount may be negative.
RULE 7: Do not count the same money in more than one category.
RULE 8: Do not invent additional income.
RULE 9: Do not allocate more money than the user actually has available.
RULE 10: If rounding creates a small difference, adjust the difference in "Savings" first. If Savings cannot reasonably absorb the difference, adjust "Other Expenses". After the adjustment, the total percentage must equal exactly 100%.

==================================================
12. BUDGET DEFICIT
==================================================

If: Essential Expenses + Mandatory Debt Payments > Reliable Monthly Income:
Then the user has a budget deficit.
Do NOT artificially force the budget into a normal allocation.
In this situation:
1. Preserve essential expenses.
2. Preserve mandatory debt payments.
3. Reduce discretionary categories as much as reasonably possible.
4. Financial Goals may temporarily receive 0 AZN.
5. Savings may temporarily receive 0 AZN.
6. Calculate the remaining monthly deficit.
7. Clearly indicate the deficit in the AI Recommendation.
Do not hide a deficit by inventing income or unrealistically reducing mandatory expenses.

==================================================
13. FINAL VALIDATION
==================================================

Before returning the table, internally validate the entire calculation:
✓ Sum of Recommended Monthly Amounts = Reliable Monthly Income
✓ Sum of Percentages = exactly 100%
✓ Sum of Annual Amounts = Reliable Monthly Income × 12
✓ Annual Amount for every category = Recommended Monthly Amount × 12
✓ Mandatory credit/debt payments are included
✓ Financial goal priorities are considered
✓ Savings are considered where financially possible
✓ No amount is negative
✓ No money is counted twice
✓ Current Monthly Amounts remain unchanged from user input

If ANY validation fails: DO NOT return the result yet. Recalculate the allocation, correct the error, and validate again.

==================================================
RULES — JSON SCHEMA (CRITICAL OUTPUT FORMAT)
==================================================

- You MUST return a single JSON object. No markdown text, no prefix, no suffix.
- "monthly_table" MUST be an array of EXACTLY 12 objects, one for each month (Yanvar, Fevral, Mart, Aprel, May, İyun, İyul, Avqust, Sentyabr, Oktyabr, Noyabr, Dekabr). No missing months.
- "budget_comparison" MUST be an array of EXACTLY 9 objects (market, restaurant, transport, utilities, clothing, entertainment, online_shopping, other, credit).
- Do not drop any keys.
- All numeric fields must be raw numbers (floats/integers), no "AZN" suffix, no strings for numbers.

Return ONLY a valid JSON object with EXACTLY these top-level keys:
{{
  "recommended_monthly_savings": float,
  "recommended_annual_savings": float,
  "financial_status": string,
  "financial_status_description": string,
  "monthly_budget_plan": string,
  "reliable_monthly_income": float,
  "current_total_monthly_expenses": float,
  "recommended_total_monthly_allocation": float,
  "annual_total_allocation": float,
  "total_allocation_percentage": 100.0,
  "savings_goals_breakdown": [
    {{
      "goal_name": string,
      "target_amount": float,
      "current_amount": float,
      "progress_percentage": float,
      "recommended_monthly_saving": float,
      "priority": string
    }}
  ],
  "monthly_table": [
    {{
      "month_name": string,
      "income": float,
      "market": float,
      "restaurant": float,
      "transport": float,
      "utilities": float,
      "clothing": float,
      "entertainment": float,
      "online_shopping": float,
      "other": float,
      "credit": float,
      "savings": float,
      "balance": float
    }}
  ],
  "annual_totals": {{
    "total_income": float,
    "total_market": float,
    "total_restaurant": float,
    "total_transport": float,
    "total_utilities": float,
    "total_clothing": float,
    "total_entertainment": float,
    "total_online_shopping": float,
    "total_other": float,
    "total_credit": float,
    "total_savings": float,
    "net_annual_balance": float
  }},
  "budget_comparison": [
    {{
      "category_name": string,
      "percentage": float,
      "current_monthly_amount": float,
      "recommended_monthly_amount": float,
      "annual_amount": float,
      "status": string,
      "ai_recommendation": string
    }}
  ]
}}

Return ONLY the valid JSON object, nothing else.
"""


def llm_client_call(prompt: str) -> str:
    """Fallback JSON response for environments without a live LLM client."""
    return json.dumps({
        "monthly_table": [],
        "annual_totals": {},
        "financial_status_description": "",
        "monthly_budget_plan": "",
        "category_recommendations": {}
    }, ensure_ascii=False)


def calculate_base_budget(user_data: Dict[str, Any], total_income: float) -> Dict[str, Any]:
    """Calculate mathematically valid budget values and statuses before LLM text generation."""
    expenses = user_data.get("expenses") or user_data.get("monthly_expenses") or {}
    categories = [
        "market", "restaurant", "transport", "utilities",
        "clothing", "entertainment", "online_shopping", "other", "credit"
    ]

    budget_comparison = []
    total_recommended = 0.0

    for cat in categories:
        actual = float(expenses.get(cat, 0.0))

        if cat in ["credit", "utilities"]:
            recommended = actual
        elif actual > (total_income * 0.15):
            recommended = round(actual * 0.85, 2)
        else:
            recommended = actual

        total_recommended += recommended

    recommended_savings = max(0.0, round(total_income - total_recommended, 2))

    for cat in categories:
        actual = float(expenses.get(cat, 0.0))

        if cat in ["credit", "utilities"]:
            recommended = actual
        elif actual > (total_income * 0.15):
            recommended = round(actual * 0.85, 2)
        else:
            recommended = actual

        pct = round((recommended / total_income) * 100, 2) if total_income > 0 else 0.0
        annual = round(recommended * 12, 2)

        if cat in ["credit", "utilities"]:
            status = "Prioritet ödəniş"
        elif actual == 0:
            status = "Qənaətlidir"
        elif actual > recommended * 1.20:
            status = "Yüksək xərc"
        elif actual > recommended * 1.05:
            status = "Diqqət"
        else:
            status = "Uyğundur"

        budget_comparison.append({
            "category_name": cat,
            "percentage": pct,
            "current_monthly_amount": actual,
            "recommended_monthly_amount": recommended,
            "annual_amount": annual,
            "status": status,
            "ai_recommendation": ""
        })

    total_current_expenses = sum(float(expenses.get(c, 0.0)) for c in categories)
    if total_current_expenses >= total_income:
        financial_status = "Risklidir"
    elif total_current_expenses > (total_income * 0.85):
        financial_status = "Diqqət"
    else:
        financial_status = "Balanslı"

    return {
        "budget_comparison": budget_comparison,
        "recommended_monthly_savings": recommended_savings,
        "recommended_annual_savings": round(recommended_savings * 12, 2),
        "financial_status": financial_status,
        "reliable_monthly_income": total_income,
        "current_total_monthly_expenses": total_current_expenses,
        "recommended_total_monthly_allocation": total_income,
        "annual_total_allocation": round(total_income * 12, 2),
        "total_allocation_percentage": 100.0,
    }


def get_monthly_table_prompt(budget_comparison: List[Dict[str, Any]], total_income: float, user_data: Dict[str, Any]) -> str:
    """Return the 12-month simulation prompt for the monthly table generation step."""
    return f"""You are Jev AI's Financial Simulation Engine.

Task: Generate a realistic 12-month budget simulation (Yanvar to Dekabr) based on this base monthly allocation and user data.

Base Allocation:
{json.dumps(budget_comparison, ensure_ascii=False, indent=2)}

Total Income: {total_income} AZN
User Credits / Debts: {json.dumps(user_data.get('credits', []), ensure_ascii=False)}

RULES:
1. Return EXACTLY 12 monthly objects in "monthly_table" (Yanvar, Fevral, Mart, Aprel, May, İyun, İyul, Avqust, Sentyabr, Oktyabr, Noyabr, Dekabr).
2. Recurring categories (market, utilities, transport) MUST remain stable within ±5% monthly.
3. Non-recurring categories (clothing, entertainment, restaurant) MUST vary 15-40% month-to-month (e.g., clothing spikes in Spring/Autumn, entertainment/restaurant rises in Summer).
4. If a credit's remaining months hit 0, set its credit payment to 0 for all subsequent months.
5. "balance" = income - (market + restaurant + transport + utilities + clothing + entertainment + online_shopping + other + credit + savings).

OUTPUT FORMAT:
Return ONLY a JSON object with EXACTLY these top-level keys:
{{
  "monthly_table": [
    {{
      "month_name": string,
      "income": float,
      "market": float,
      "restaurant": float,
      "transport": float,
      "utilities": float,
      "clothing": float,
      "entertainment": float,
      "online_shopping": float,
      "other": float,
      "credit": float,
      "savings": float,
      "balance": float
    }}
  ],
  "annual_totals": {{
    "total_income": float,
    "total_market": float,
    "total_restaurant": float,
    "total_transport": float,
    "total_utilities": float,
    "total_clothing": float,
    "total_entertainment": float,
    "total_online_shopping": float,
    "total_other": float,
    "total_credit": float,
    "total_savings": float,
    "net_annual_balance": float
  }}
}}
"""


def get_copywriter_prompt(budget_comparison: List[Dict[str, Any]], user_data: Dict[str, Any], financial_status: str) -> str:
    """Return the short Azerbaijani recommendation prompt for each category and the summary text."""
    annual_priority = user_data.get("annual_budget_priority", "Gəliri daha düzgün bölüşdürmək")

    return f"""You are Jev AI, a friendly Azerbaijani AI Financial Advisor.

Task: Generate short, natural Azerbaijani recommendations for each budget category and overall strategy summary.

Input Data:
Budget Comparison Categories & Calculated Statuses:
{json.dumps(budget_comparison, ensure_ascii=False, indent=2)}

Overall Financial Status: {financial_status}
User Annual Priority: {annual_priority}
User Financial Assessment: {user_data.get('financial_assessment', '')}

TONE & RULES FOR CATEGORY RECOMMENDATIONS ("ai_recommendation"):
- Exactly 1 short sentence per category (max 10-12 words).
- Plain, friendly, everyday Azerbaijani (no corporate jargon, no lists).
- "Prioritet ödəniş": remind them to pay on time. E.g., "Kommunal ödənişini vaxtında ödə."
- "Yüksək xərc": state exact gap in AZN. E.g., "Restoran xərcini 80 AZN azalt."
- "Diqqət": light nudge with gap. E.g., "Nəqliyyatı 15 AZN qədər azaltsan yaxşı olar."
- "Qənaətlidir": positive feedback. E.g., "Bu sahədə əla qənaət edirsən."
- "Uyğundur": short confirmation. E.g., "Xərcin tövsiyə olunan səviyyədədir."

STRATEGY TEXT RULES:
- "financial_status_description": Exactly 1 short sentence summarizing current status.
- "monthly_budget_plan": Max 3-4 sentences summarizing the plan and explicitly mentioning the annual_budget_priority ("{annual_priority}").

OUTPUT FORMAT:
Return ONLY a JSON object:
{{
  "financial_status_description": string,
  "monthly_budget_plan": string,
  "category_recommendations": {{
    "market": string,
    "restaurant": string,
    "transport": string,
    "utilities": string,
    "clothing": string,
    "entertainment": string,
    "online_shopping": string,
    "other": string,
    "credit": string
  }}
}}
"""


def run_jev_budget_pipeline(user_data: Dict[str, Any], total_income: float, llm_client=None) -> dict:
    """Run the full Python-first Jev pipeline with LLM calls for monthly simulation and text generation."""
    base_result = calculate_base_budget(user_data, total_income)

    def _call_llm(prompt: str) -> str:
        if llm_client is not None:
            if hasattr(llm_client, "generate") and callable(llm_client.generate):
                result = llm_client.generate(prompt)
                if isinstance(result, str):
                    return result
                if isinstance(result, (dict, list)):
                    return json.dumps(result, ensure_ascii=False)
            if hasattr(llm_client, "chat") and hasattr(llm_client.chat, "completions"):
                try:
                    completion = llm_client.chat.completions.create(
                        model="openai/gpt-oss-20b",
                        messages=[
                            {"role": "user", "content": prompt},
                        ],
                        max_tokens=2048,
                        temperature=0.2,
                    )
                    if hasattr(completion, "choices") and completion.choices:
                        return completion.choices[0].message.content
                except Exception:
                    pass
        return llm_client_call(prompt)

    monthly_prompt = get_monthly_table_prompt(base_result["budget_comparison"], total_income, user_data)
    try:
        llm_response_a = json.loads(_call_llm(monthly_prompt))
    except (TypeError, ValueError):
        llm_response_a = {"monthly_table": [], "annual_totals": {}}

    copywriter_prompt = get_copywriter_prompt(base_result["budget_comparison"], user_data, base_result["financial_status"])
    try:
        llm_response_b = json.loads(_call_llm(copywriter_prompt))
    except (TypeError, ValueError):
        llm_response_b = {"financial_status_description": "", "monthly_budget_plan": "", "category_recommendations": {}}

    recs = llm_response_b.get("category_recommendations", {})
    for item in base_result["budget_comparison"]:
        cat = item["category_name"]
        item["ai_recommendation"] = recs.get(cat, "Xərclərinizə nəzarət etməyiniz tövsiyə olunur.")

    return {
        "recommended_monthly_savings": base_result["recommended_monthly_savings"],
        "recommended_annual_savings": base_result["recommended_annual_savings"],
        "financial_status": base_result["financial_status"],
        "financial_status_description": llm_response_b.get("financial_status_description", ""),
        "monthly_budget_plan": llm_response_b.get("monthly_budget_plan", ""),
        "reliable_monthly_income": base_result["reliable_monthly_income"],
        "current_total_monthly_expenses": base_result["current_total_monthly_expenses"],
        "recommended_total_monthly_allocation": base_result["recommended_total_monthly_allocation"],
        "annual_total_allocation": base_result["annual_total_allocation"],
        "total_allocation_percentage": base_result["total_allocation_percentage"],
        "savings_goals_breakdown": user_data.get("goals", []),
        "monthly_table": llm_response_a.get("monthly_table", []),
        "annual_totals": llm_response_a.get("annual_totals", {}),
        "budget_comparison": base_result["budget_comparison"],
    }


def get_fallback_budget_plan(session):
    income = float(session.salary or 0) + float(session.extra_income or 0)
    expenses = {
        "food": float(session.expense_market or 0),
        "restaurant": float(session.expense_restaurant or 0),
        "transport": float(session.expense_transport or 0),
        "utilities": float(session.expense_utilities or 0),
        "clothing": float(session.expense_clothing or 0),
        "entertainment": float(session.expense_entertainment or 0),
        "online_shopping": float(session.expense_online_shopping or 0),
        "other": float(session.expense_other or 0),
    }
    credit = sum(float(item.monthly) for item in session.credits.all())
    monthly_expenses = sum(expenses.values())
    available = income - monthly_expenses - credit
    monthly_savings = round(max(0, min(income * 0.1, available)), 2)
    balance = round(available - monthly_savings, 2)

    months = [
        "Yanvar", "Fevral", "Mart", "Aprel", "May", "İyun",
        "İyul", "Avqust", "Sentyabr", "Oktyabr", "Noyabr", "Dekabr",
    ]
    monthly_plan = [
        {
            "month": month,
            "income": income,
            **expenses,
            "credit": credit,
            "savings": monthly_savings,
            "balance": balance,
        }
        for month in months
    ]

    categories = [
        ("food", "Market", expenses["food"]),
        ("restaurant", "Restoran", expenses["restaurant"]),
        ("transport", "Nəqliyyat", expenses["transport"]),
        ("utilities", "Kommunal", expenses["utilities"]),
        ("clothing", "Geyim", expenses["clothing"]),
        ("entertainment", "Əyləncə", expenses["entertainment"]),
        ("online_shopping", "Onlayn alış-veriş", expenses["online_shopping"]),
        ("other", "Digər", expenses["other"]),
        ("credit", "Kredit", credit),
    ]
    budget_breakdown = []
    for key, label, amount in categories:
        if key in ("utilities", "credit"):
            status = "Prioritet ödəniş"
            recommendation = "Ödənişini vaxtında et."
        elif amount == 0:
            status = "Qənaətlidir"
            recommendation = "Bu sahədə qənaət edirsən."
        else:
            status = "Uyğundur"
            recommendation = "Xərcin tövsiyə olunan səviyyədədir."
        budget_breakdown.append({
            "category": label,
            "percentage": round(amount / income * 100, 2) if income else 0,
            "current_monthly": amount,
            "recommended_monthly": amount,
            "yearly": round(amount * 12, 2),
            "status": status,
            "recommendation": recommendation,
        })

    if income <= monthly_expenses + credit:
        financial_status = "Risklidir"
        financial_status_description = "Xərclər gəlirə bərabərdir və ya gəliri keçir."
    elif income and (monthly_expenses + credit) / income > 0.85:
        financial_status = "Diqqət"
        financial_status_description = "Gəlirin böyük hissəsi aylıq ödənişlərə gedir."
    else:
        financial_status = "Balanslı"
        financial_status_description = "Aylıq xərclərdən sonra gəlirin bir hissəsi qalır."

    goals = list(session.savings_goals.all())
    weights = [
        3 if "yuxarı" in (goal.priority or "").lower()
        else 1 if "aşağı" in (goal.priority or "").lower()
        else 2
        for goal in goals
    ]
    total_weight = sum(weights)
    savings_goals_breakdown = []
    for goal, weight in zip(goals, weights):
        target = float(goal.amount or 0)
        contribution = monthly_savings * weight / total_weight if total_weight else 0
        savings_goals_breakdown.append({
            "goal_name": goal.custom_name or goal.goal_id,
            "target_amount": target,
            "current_amount": 0,
            "progress_percentage": 0,
            "recommended_monthly_saving": round(min(contribution, target) if target else contribution, 2),
            "priority": goal.priority or "Orta prioritet",
        })

    annual_totals = {
        "total_income": round(income * 12, 2),
        "total_market": round(expenses["food"] * 12, 2),
        "total_restaurant": round(expenses["restaurant"] * 12, 2),
        "total_transport": round(expenses["transport"] * 12, 2),
        "total_utilities": round(expenses["utilities"] * 12, 2),
        "total_clothing": round(expenses["clothing"] * 12, 2),
        "total_entertainment": round(expenses["entertainment"] * 12, 2),
        "total_online_shopping": round(expenses["online_shopping"] * 12, 2),
        "total_other": round(expenses["other"] * 12, 2),
        "total_credit": round(credit * 12, 2),
        "total_savings": round(monthly_savings * 12, 2),
        "net_annual_balance": round(balance * 12, 2),
    }
    return {
        "recommended_monthly_savings": monthly_savings,
        "recommended_annual_savings": round(monthly_savings * 12, 2),
        "financial_status": financial_status,
        "financial_status_description": financial_status_description,
        "monthly_budget_plan": "Bu ilkin plan gəlir və qeyd etdiyiniz xərclər əsasında hazırlanıb.",
        "savings_goals_breakdown": savings_goals_breakdown,
        "monthly_plan": monthly_plan,
        "annual_totals": annual_totals,
        "budget_breakdown": budget_breakdown,
    }


def generate_ai_budget_plan(session_id):
    logger.info("AI plan generation started for session %s", session_id)
    session = None
    try:
        session = FinancialInquirySession.objects.get(id=session_id)

        user_financial_data = {
            "salary": float(session.salary or 0),
            "has_extra_income": bool(session.has_extra_income),
            "extra_income": float(session.extra_income or 0),
            "housing_type": session.housing_type or '',
            "housing_amount": float(session.housing_amount or 0),
            "has_credit": bool(session.has_credit),
            "credits": list(session.credits.values('monthly', 'remaining', 'rate', 'months')),
            "monthly_expenses": {
                "market": float(session.expense_market),
                "utilities": float(session.expense_utilities),
                "transport": float(session.expense_transport),
                "restaurant": float(session.expense_restaurant),
                "clothing": float(session.expense_clothing),
                "entertainment": float(session.expense_entertainment),
                "online_shopping": float(session.expense_online_shopping),
                "other": float(session.expense_other),
            },
            "recurring_expenses": {
                "market": session.recurring_market,
                "utilities": session.recurring_utilities,
                "transport": session.recurring_transport,
                "restaurant": session.recurring_restaurant,
                "clothing": session.recurring_clothing,
                "entertainment": session.recurring_entertainment,
                "online_shopping": session.recurring_online_shopping,
                "other": session.recurring_other,
            },
            "financial_assessment": session.financial_assessment or '',
            "monthly_savings_ability": session.monthly_savings_ability or '',
            "annual_budget_priority": session.annual_budget_priority or '',
            "savings_goals": list(session.savings_goals.values('goal_id', 'custom_name', 'priority', 'amount')),
        }

        total_monthly_income = float(session.salary or 0) + float(session.extra_income or 0)
        total_monthly_credit = sum(float(c.monthly) for c in session.credits.all())

        prompt = get_jev_combined_prompt(user_financial_data, total_monthly_income, DecimalEncoder=DecimalEncoder)

        api_key = getattr(settings, 'JEV_AI_API_KEY', None) or getattr(settings, 'GROQ_API_KEY', None)
        try:
            if not api_key:
                raise ValueError("JEV_AI_API_KEY və ya GROQ_API_KEY settings.py faylında tapılmadı.")

            client = Groq(api_key=api_key)
            completion = client.chat.completions.create(
                model="openai/gpt-oss-20b",
                messages=[
                    {"role": "system", "content": "You are Jev AI, an expert AI financial budget optimization engine for Azerbaijani users. Respond with the final JSON answer directly and immediately — do not show your reasoning process, do not think step by step out loud, just output the JSON object as your entire response."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=4096,
                temperature=0.3,
                response_format={"type": "json_object"}
            )
        except RateLimitError as groq_err:
            retry_after = groq_err.response.headers.get('retry-after') if groq_err.response else None
            logger.warning(
                "Jev AI provider rate limit reached for session %s; retry-after=%s",
                session_id,
                retry_after,
                exc_info=True,
            )
            raise AIProviderRateLimitError(retry_after=retry_after) from groq_err
        except Exception as groq_err:
            logger.exception("Jev AI request failed for session %s; using fallback plan", session_id)
            ai_raw_text = json.dumps(get_fallback_budget_plan(session), cls=DecimalEncoder, ensure_ascii=False)
        else:
            ai_raw_text = completion.choices[0].message.content
            print(f"Finish reason: {completion.choices[0].finish_reason}")
            print(f"--- RAW AI OUTPUT (length: {len(ai_raw_text) if ai_raw_text else 0}) ---")
            print(repr(ai_raw_text))
            print("--- END RAW AI OUTPUT ---")

        cleaned_text = ai_raw_text.strip()
        if "```json" in cleaned_text:
            parts = cleaned_text.split("```json")
            if len(parts) > 1:
                cleaned_text = parts[1].split("```")[0]
        elif "```" in cleaned_text:
            parts = cleaned_text.split("```")
            if len(parts) > 1:
                cleaned_text = parts[1].split("```")[0]

        cleaned_text = cleaned_text.strip()
        start_idx = cleaned_text.find('{')
        end_idx = cleaned_text.rfind('}')

        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            cleaned_text = cleaned_text[start_idx:end_idx + 1]

        try:
            ai_data = json.loads(cleaned_text)
        except json.JSONDecodeError as json_err:
            print(f"*** JSON parse failed: {json_err} ***")
            error_pos = json_err.pos
            start = max(0, error_pos - 200)
            end = min(len(cleaned_text), error_pos + 200)
            print(f"--- CONTEXT AROUND ERROR (position {error_pos}) ---")
            print(cleaned_text[start:end])
            print("--- END CONTEXT ---")
            raise

        if "monthly_table" not in ai_data and isinstance(ai_data.get("monthly_plan"), list):
            ai_data["monthly_table"] = [
                {
                    "month_name": row.get("month", row.get("month_name", "")),
                    "income": row.get("income", total_monthly_income),
                    "market": row.get("food", row.get("market", 0)),
                    "restaurant": row.get("restaurant", 0),
                    "transport": row.get("transport", 0),
                    "utilities": row.get("utilities", 0),
                    "clothing": row.get("clothing", 0),
                    "entertainment": row.get("entertainment", 0),
                    "online_shopping": row.get("online_shopping", 0),
                    "other": row.get("other", 0),
                    "credit": row.get("credit", 0),
                    "savings": row.get("savings", 0),
                    "balance": row.get("balance", 0),
                }
                for row in ai_data["monthly_plan"]
            ]
        if "budget_comparison" not in ai_data and isinstance(ai_data.get("budget_breakdown"), list):
            ai_data["budget_comparison"] = [
                {
                    "category_name": row.get("category", ""),
                    "percentage": row.get("percentage", 0),
                    "current_monthly_amount": row.get("current_monthly", 0),
                    "recommended_monthly_amount": row.get("recommended_monthly", 0),
                    "annual_amount": row.get("yearly", 0),
                    "status": row.get("status", "Uyğundur"),
                    "ai_recommendation": row.get("recommendation", ""),
                }
                for row in ai_data["budget_breakdown"]
            ]

        monthly_table = ai_data.get("monthly_table", [])
        if not isinstance(monthly_table, list) or len(monthly_table) != 12:
            print(f"WARNING: monthly_table was truncated ({len(monthly_table) if isinstance(monthly_table, list) else 'invalid'} months). Rebuilding full 12-month table.")
            ai_data["monthly_table"] = [
                {
                    "month_name": m, "income": total_monthly_income, "market": float(session.expense_market),
                    "restaurant": float(session.expense_restaurant), "transport": float(session.expense_transport),
                    "utilities": float(session.expense_utilities), "clothing": float(session.expense_clothing),
                    "entertainment": float(session.expense_entertainment), "online_shopping": float(session.expense_online_shopping),
                    "other": float(session.expense_other), "credit": 0, "savings": 0, "balance": 0
                }
                for m in ["Yanvar", "Fevral", "Mart", "Aprel", "May", "İyun", "İyul", "Avqust", "Sentyabr", "Oktyabr", "Noyabr", "Dekabr"]
            ]

        budget_comparison = ai_data.get("budget_comparison", [])
        if not isinstance(budget_comparison, list) or len(budget_comparison) < 5:
            print("WARNING: budget_comparison was truncated. Rebuilding fallback comparison.")
            ai_data["budget_comparison"] = [
                {"category_name": "Market", "percentage": 0, "current_monthly_amount": float(session.expense_market), "recommended_monthly_amount": float(session.expense_market), "annual_amount": float(session.expense_market) * 12, "status": "Uyğundur", "ai_recommendation": "Xərcin tövsiyə olunan səviyyədədir."},
                {"category_name": "Restoran", "percentage": 0, "current_monthly_amount": float(session.expense_restaurant), "recommended_monthly_amount": float(session.expense_restaurant), "annual_amount": float(session.expense_restaurant) * 12, "status": "Uyğundur", "ai_recommendation": "Xərcin tövsiyə olunan səviyyədədir."},
                {"category_name": "Nəqliyyat", "percentage": 0, "current_monthly_amount": float(session.expense_transport), "recommended_monthly_amount": float(session.expense_transport), "annual_amount": float(session.expense_transport) * 12, "status": "Uyğundur", "ai_recommendation": "Xərcin tövsiyə olunan səviyyədədir."},
                {"category_name": "Kommunal", "percentage": 0, "current_monthly_amount": float(session.expense_utilities), "recommended_monthly_amount": float(session.expense_utilities), "annual_amount": float(session.expense_utilities) * 12, "status": "Prioritet ödəniş", "ai_recommendation": "Kommunal ödənişini vaxtında ödə."},
                {"category_name": "Geyim", "percentage": 0, "current_monthly_amount": float(session.expense_clothing), "recommended_monthly_amount": float(session.expense_clothing), "annual_amount": float(session.expense_clothing) * 12, "status": "Uyğundur", "ai_recommendation": "Xərcin tövsiyə olunan səviyyədədir."},
                {"category_name": "Əyləncə", "percentage": 0, "current_monthly_amount": float(session.expense_entertainment), "recommended_monthly_amount": float(session.expense_entertainment), "annual_amount": float(session.expense_entertainment) * 12, "status": "Uyğundur", "ai_recommendation": "Xərcin tövsiyə olunan səviyyədədir."},
                {"category_name": "Onlayn alış-veriş", "percentage": 0, "current_monthly_amount": float(session.expense_online_shopping), "recommended_monthly_amount": float(session.expense_online_shopping), "annual_amount": float(session.expense_online_shopping) * 12, "status": "Uyğundur", "ai_recommendation": "Xərcin tövsiyə olunan səviyyədədir."},
                {"category_name": "Digər", "percentage": 0, "current_monthly_amount": float(session.expense_other), "recommended_monthly_amount": float(session.expense_other), "annual_amount": float(session.expense_other) * 12, "status": "Uyğundur", "ai_recommendation": "Xərcin tövsiyə olunan səviyyədədir."},
                {"category_name": "Kredit", "percentage": 0, "current_monthly_amount": total_monthly_credit, "recommended_monthly_amount": total_monthly_credit, "annual_amount": total_monthly_credit * 12, "status": "Prioritet ödəniş", "ai_recommendation": "Kredit ödənişini hər ay vaxtında et."},
            ]

        db_goals_count = session.savings_goals.count()
        ai_goals = ai_data.get("savings_goals_breakdown", [])
        if not isinstance(ai_goals, list) or len(ai_goals) < db_goals_count:
            print("WARNING: savings_goals_breakdown truncated. Generating smart priority-weighted fallback.")
            goals = list(session.savings_goals.all())
            total_rec_savings = float(ai_data.get("recommended_monthly_savings", 0) or (total_monthly_income * 0.2))

            weights = []
            for g in goals:
                p = (g.priority or "Orta prioritet").lower()
                if "yuxarı" in p:
                    weights.append(3)
                elif "aşağı" in p:
                    weights.append(1)
                else:
                    weights.append(2)

            total_weight = sum(weights) if weights else 1
            fallback_goals = []
            for i, goal in enumerate(goals):
                target = float(goal.amount or 0)
                weight = weights[i]
                optimal_monthly = (total_rec_savings * (weight / total_weight)) if total_weight > 0 else (target / 12)
                if optimal_monthly > target and target > 0:
                    optimal_monthly = target

                fallback_goals.append({
                    "goal_name": goal.custom_name or goal.goal_id,
                    "target_amount": target,
                    "current_amount": 0.0,
                    "progress_percentage": 0.0,
                    "recommended_monthly_saving": round(optimal_monthly, 2),
                    "priority": goal.priority or "Orta prioritet"
                })
            ai_data["savings_goals_breakdown"] = fallback_goals

        session.recommended_monthly_savings = ai_data.get("recommended_monthly_savings", 0)
        session.recommended_annual_savings = ai_data.get("recommended_annual_savings", 0)
        session.financial_status = ai_data.get("financial_status", "Naməlum")
        session.financial_status_description = ai_data.get("financial_status_description", "")
        session.ai_response_text = ai_data.get("monthly_budget_plan", "")
        session.savings_goals_breakdown = ai_data.get("savings_goals_breakdown", [])
        session.monthly_table = ai_data.get("monthly_table", [])
        session.annual_totals = ai_data.get("annual_totals", {})
        session.budget_comparison = ai_data.get("budget_comparison", [])

        session.status = 'completed'
        session.save()
        print(f"--- Jev AI Plan Generation Completed for Session ID: {session_id} ---")

    except Exception:
        logger.exception("AI plan generation failed for session %s", session_id)
        if session is None:
            session = FinancialInquirySession.objects.filter(id=session_id).first()
        if session:
            session.status = 'failed'
            session.save()
        raise