from groq import Groq
import json
from decimal import Decimal
from django.conf import settings
from .models import FinancialInquirySession


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


def generate_ai_budget_plan(session_id):
    print(f"--- Groq AI Plan Generation Started for Session ID: {session_id} ---")
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

        prompt = f"""
            Analyze this Azerbaijani user's financial profile (currency: AZN) and produce an optimal, realistic 12-month financial plan.

            User Financial Data:
            {json.dumps(user_financial_data, cls=DecimalEncoder, ensure_ascii=False, indent=2)}

            RULES — MONTHLY TABLE:
            - "monthly_table" must have EXACTLY 12 objects (Yanvar to Dekabr, in order).
            - Each credit's "months" = remaining months. Once it hits 0, stop including that credit's payment in "credit".
            - recurring=true categories stay within ±5% every month. recurring=false categories MUST vary 15-40% month to month (seasonal: clothing spikes spring/autumn/New Year, entertainment/restaurant rises in summer).
            - "balance" = income - (all expenses + credit + savings) for that month. Can be negative.

            RULES — budget_comparison (one object per category: market, restaurant, transport, utilities, clothing, entertainment, online_shopping, other, credit):
            - recommended_monthly_amount stays within ±30% of the user's actual amount unless overspending is clear. Total recommendations must not exceed total monthly income ({total_monthly_income} AZN).
            - status, in this priority order: (1) credit/utilities are ALWAYS "Prioritet ödəniş". (2) amount=0 → "Qənaətlidir". (3) actual exceeds recommended by >20% → "Yüksək xərc". (4) exceeds by 5-20% → "Diqqət". (5) otherwise → "Uyğundur".

            RULES — ai_recommendation (REQUIRED for every single row, never empty, tailored to that row's status):
            - "Prioritet ödəniş": remind them to pay on time, e.g. "Kommunal ödənişini vaxtında ödə."
            - "Yüksək xərc": name the AZN gap between current and recommended, e.g. "Restoran xərcini 80 AZN azalt."
            - "Diqqət": lighter nudge naming the AZN gap, e.g. "Nəqliyyatı 15 AZN qədər azaltsan yaxşı olar."
            - "Qənaətlidir": short positive note, e.g. "Bu sahədə əla qənaət edirsən."
            - "Uyğundur": short confirmation, e.g. "Xərcin tövsiyə olunan səviyyədədir."

            RULES — financial_status (exactly one): "Risklidir" if expenses+credit ≥ income. "Diqqət" if expenses use >85% of income. "Balanslı" if there's healthy savings margin.

            RULES — savings_goals_breakdown: do NOT just divide target/12. Each goal's "priority" is one of "Yuxarı prioritet" (largest share), "Orta prioritet" (moderate share), "Aşağı prioritet" (smallest share). Sum of recommended_monthly_saving across goals must fit within recommended_monthly_savings.

            RULES — use the user's own stated preferences to shape everything above:
            - financial_assessment: "good_manager"→more ambitious savings target. "sometimes_breaks_plan"→realistic, slightly conservative, some buffer. "nothing_left"→conservative, essentials + small buffer first.
            - monthly_savings_ability: "can_save"→align with optimal amount. "sometimes"→somewhat below max. "cannot_save"→start small/achievable, say so in monthly_budget_plan.
            - annual_budget_priority tilts the WHOLE plan and must be named explicitly in monthly_budget_plan: "Daha çox qənaət etmək"→push savings higher, trim discretionary categories. "Xərclərə nəzarət etmək"→tighten every category, flag "Yüksək xərc" more readily. "Borcları azaltmaq"→prioritize faster credit payoff over savings. "Gəliri daha düzgün bölüşdürmək"→balanced allocation across categories. "Gözlənilməz xərclərə hazır olmaq"→favor an emergency-fund goal. "Gələcək üçün pul toplamaq"→favor long-term goals (home/education/business) over short-term ones.
            - If has_extra_income: lean toward putting extra_income into savings/debt payoff, not treating it like guaranteed salary.

            RULES — TEXT: every "ai_recommendation" is ONE short sentence, max ~10-12 words, plain everyday Azerbaijani, no jargon, no lists. Like a text from a friend, not a report. financial_status_description: also 1 short plain sentence. monthly_budget_plan: max 3-4 sentences.

            RULES — JSON SCHEMA (CRITICAL):
            - You MUST return a single JSON object.
            - "monthly_table" MUST be an array of EXACTLY 12 objects, one for each month (Yanvar, Fevral, Mart, Aprel, May, İyun, İyul, Avqust, Sentyabr, Oktyabr, Noyabr, Dekabr). No missing months.
            - "budget_comparison" MUST be an array of EXACTLY 9 objects (market, restaurant, transport, utilities, clothing, entertainment, online_shopping, other, credit).
            - Do not drop any keys.

            Return ONLY a valid JSON object with EXACTLY these top-level keys: recommended_monthly_savings (float), recommended_annual_savings (float), financial_status (string), financial_status_description (string), monthly_budget_plan (string), savings_goals_breakdown (array of {{goal_name, target_amount, current_amount, progress_percentage, recommended_monthly_saving, priority}}), monthly_table (array of 12 {{month_name, income, market, restaurant, transport, utilities, clothing, entertainment, online_shopping, other, credit, savings, balance}}), annual_totals ({{total_income, total_market, total_restaurant, total_transport, total_utilities, total_clothing, total_entertainment, total_online_shopping, total_other, total_credit, total_savings, net_annual_balance}}), budget_comparison (array of EXACTLY 9 {{category_name, percentage, current_monthly_amount, recommended_monthly_amount, annual_amount, status, ai_recommendation}}).

            All numeric fields must be raw numbers, no "AZN" suffix, no strings for numbers. Return ONLY the JSON object, nothing else.
        """

        api_key = getattr(settings, 'GROQ_API_KEY', None)
        if not api_key:
            raise ValueError("GROQ_API_KEY settings.py faylında tapılmadı.")

        client = Groq(api_key=api_key)

        try:
            completion = client.chat.completions.create(
                model="openai/gpt-oss-20b",
                messages=[
                    {"role": "system", "content": "You are an expert financial advisor for Azerbaijani users. Respond with the final JSON answer directly and immediately — do not show your reasoning process, do not think step by step out loud, just output the JSON object as your entire response."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=20000,
                temperature=0.3,
                response_format={"type": "json_object"}
            )
        except Exception as groq_err:
            print(f"*** Groq API call failed. Full error: {groq_err} ***")
            if hasattr(groq_err, 'response'):
                try:
                    error_body = groq_err.response.json()
                    print(f"*** Error body: {error_body} ***")
                except Exception:
                    print("*** Could not parse error response body ***")
            raise

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
        print(f"--- Groq AI Plan Generation Completed for Session ID: {session_id} ---")

    except Exception as e:
        print(f"*** Groq AI Plan Generation Error: {str(e)} ***")
        session = FinancialInquirySession.objects.filter(id=session_id).first()
        if session:
            session.status = 'failed'
            session.save()