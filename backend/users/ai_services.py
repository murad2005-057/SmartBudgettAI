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

        prompt = f"""
        Analyze this comprehensive user financial profile and calculate a detailed financial plan.

        User Financial Data:
        {json.dumps(user_financial_data, cls=DecimalEncoder, ensure_ascii=False, indent=2)}

        You must return a valid JSON object containing EXACTLY these keys:
        - "recommended_monthly_savings": (float)
        - "recommended_annual_savings": (float)
        - "financial_status": (string)
        - "financial_status_description": (string)
        - "monthly_budget_plan": (string text summary)
        - "savings_goals_breakdown": array of objects with keys: goal_name, target_amount, current_amount, progress_percentage, recommended_monthly_saving, priority
        - "monthly_table": array of exactly 12 objects (Yanvar to Dekabr) with keys: month_name, income, expenses, credit, savings, balance
        - "annual_totals": object with keys: total_income, total_expenses, total_credit, total_savings, net_annual_balance
        - "budget_comparison": array of objects with keys: category_name, percentage, current_monthly_amount, recommended_monthly_amount, annual_amount, status, ai_recommendation
        """

        api_key = getattr(settings, 'GROQ_API_KEY', None)
        if not api_key:
            raise ValueError("GROQ_API_KEY settings.py faylında tapılmadı.")

        client = Groq(api_key=api_key)

        completion = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[
                {"role": "system", "content": "You are an expert financial advisor. You must output valid JSON matching the requested structure."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )

        ai_raw_text = completion.choices[0].message.content
        ai_data = json.loads(ai_raw_text)

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