from google import genai
from google.genai.errors import ServerError
import json
import time
from decimal import Decimal
from django.conf import settings
from .models import FinancialInquirySession

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)

def generate_ai_budget_plan(session_id):
    print(f"--- AI Plan Generation Started for Session ID: {session_id} ---")
    try:
        session = FinancialInquirySession.objects.get(id=session_id)
        
        user_financial_data = {
            "salary": float(session.salary or 0),
            "has_extra_income": getattr(session, 'has_extra_income', 'Xeyr'),
            "extra_income": float(getattr(session, 'extra_income', 0) or 0),
            "housing_type": getattr(session, 'housing_type', ''),
            "housing_amount": float(getattr(session, 'housing_amount', 0) or 0),
            "has_credit": getattr(session, 'has_credit', 'Xeyr'),
            "credits": list(session.credits.values('monthly', 'remaining', 'rate', 'months')) if hasattr(session, 'credits') else [],
            "monthly_expenses": {
                "market": float(getattr(session, 'market', 0) or 0),
                "utilities": float(getattr(session, 'utilities', 0) or 0),
                "transport": float(getattr(session, 'transport', 0) or 0),
                "restaurant": float(getattr(session, 'restaurant', 0) or 0),
                "clothing": float(getattr(session, 'clothing', 0) or 0),
                "entertainment": float(getattr(session, 'entertainment', 0) or 0),
                "online_shopping": float(getattr(session, 'online_shopping', 0) or 0),
                "other": float(getattr(session, 'other', 0) or 0),
            },
            "recurring_expenses": getattr(session, 'recurring_expenses', []),
            "financial_assessment": getattr(session, 'financial_assessment', ''),
            "monthly_savings_ability": getattr(session, 'monthly_savings_ability', ''),
            "savings_goals": list(session.savings_goals.values('goal_id', 'custom_name', 'priority', 'amount')) if hasattr(session, 'savings_goals') else [],
            "annual_budget_priority": getattr(session, 'annual_budget_priority', '')
        }

        prompt = f"""
        You are an expert financial advisor and AI budget planner. 
        Analyze this comprehensive user financial profile and calculate a detailed, realistic financial plan.

        User Financial Data:
        {json.dumps(user_financial_data, cls=DecimalEncoder, ensure_ascii=False, indent=2)}

        You must perform the calculations yourself and return the response strictly as a valid JSON object with the following keys:
        - "recommended_monthly_savings": (float)
        - "recommended_annual_savings": (float)
        - "financial_status": (string)
        - "financial_status_description": (string)
        - "monthly_budget_plan": (string text summary)
        - "savings_goals_breakdown": [
            {{
              "goal_name": "string",
              "target_amount": 0.0,
              "current_amount": 0.0,
              "progress_percentage": 0.0,
              "recommended_monthly_saving": 0.0,
              "priority": "string"
            }}
          ]
        - "monthly_table": [
            {{
              "month_name": "Yanvar",
              "income": 0.0,
              "expenses": 0.0,
              "credit": 0.0,
              "savings": 0.0,
              "balance": 0.0
            }}
            // Exactly 12 months (Yanvar to Dekabr)
          ]
        - "annual_totals": {{
            "total_income": 0.0,
            "total_expenses": 0.0,
            "total_credit": 0.0,
            "total_savings": 0.0,
            "net_annual_balance": 0.0
          }}
        - "budget_comparison": [
            {{
              "category_name": "string",
              "percentage": 0.0,
              "current_monthly_amount": 0.0,
              "recommended_monthly_amount": 0.0,
              "annual_amount": 0.0,
              "status": "Optimal / Azaldılmalıdır / Artırılmalıdır",
              "ai_recommendation": "string"
            }}
          ]
        
        Return ONLY valid JSON. No extra markdown formatting outside the json block.
        """

        api_key = getattr(settings, 'GEMINI_API_KEY', None)
        if not api_key:
            raise ValueError("GEMINI_API_KEY settings.py faylında tapılmadı.")

        print("Sending comprehensive data to Gemini API using google-genai...")
        client = genai.Client(api_key=api_key)
        
        max_retries = 5
        response = None
        for attempt in range(max_retries):
            try:
                print(f"Sending request to Gemini (Attempt {attempt + 1}/{max_retries})...")
                response = client.models.generate_content(
                    model='gemini-3.6-flash',
                    contents=prompt,
                )
                break
            except ServerError as e:
                if "503" in str(e) and attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 3
                    print(f"Server is busy (503 High Demand). Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    raise e

        print("Response received successfully from Gemini!")
        
        ai_raw_text = response.text
        cleaned_text = ai_raw_text.replace("```json", "").replace("```", "").strip()
        
        try:
            ai_data = json.loads(cleaned_text)
        
            session.recommended_monthly_savings = ai_data.get("recommended_monthly_savings", 0)
            session.recommended_annual_savings = ai_data.get("recommended_annual_savings", 0)
            session.financial_status = ai_data.get("financial_status", "Naməlum")
            session.financial_status_description = ai_data.get("financial_status_description", "")
            session.ai_response_text = ai_data.get("monthly_budget_plan", "")
            session.savings_goals_breakdown = ai_data.get("savings_goals_breakdown", [])
            session.monthly_table = ai_data.get("monthly_table", [])
            session.annual_totals = ai_data.get("annual_totals", {})
            session.budget_comparison = ai_data.get("budget_comparison", []) # US-16 Added
        
            session.status = 'completed'
            session.save()
            
        except json.JSONDecodeError:
            print("Warning: JSON parse xətası baş verdi, xam mətn yadda saxlanılır.")
            session.ai_response_text = ai_raw_text
            session.status = 'completed'
            session.save()

        print(f"--- AI Plan Generation Completed for Session ID: {session_id} ---")

    except Exception as e:
        print(f"*** AI Plan Generation Error: {str(e)} ***")
        session = FinancialInquirySession.objects.filter(id=session_id).first()
        if session:
            session.status = 'failed'
            session.save()
            
            
api_key = getattr(settings, 'GEMINI_API_KEY', None)
print(f"DEBUGGING ACTIVE KEY: {api_key[:8]}... (Length: {len(api_key) if api_key else 0})")

client = genai.Client(api_key=api_key)