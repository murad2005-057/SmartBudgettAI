import json
import openai
from django.conf import settings
from .models import FinancialInquirySession

def generate_ai_budget_plan(session_id):
    """
    Background or synchronous task to process user session data 
    via an AI model and generate the financial plan.
    """
    try:
        session = FinancialInquirySession.objects.get(id=session_id)
        
        # 1. Aggregate user inputs from the onboarding session
        user_financial_data = {
            "salary": float(session.salary or 0),
            "extra_income": float(session.extra_income or 0) if session.has_extra_income else 0,
            "housing_type": session.housing_type,
            "housing_amount": float(session.housing_amount or 0),
            "monthly_expenses": float(session.total_monthly_expense or 0),
            "credits": list(session.credits.values('monthly', 'remaining', 'rate', 'months')),
            "savings_goals": list(session.savings_goals.values('goal_id', 'custom_name', 'priority', 'amount')),
            "annual_budget_priority": session.annual_budget_priority,
        }

        # 2. Construct the prompt for the AI model
        prompt = f"""
        You are an expert financial advisor and AI budget planner. 
        Analyze the following user financial profile and provide a tailored 12-month financial breakdown and strategy.
        
        User Financial Data:
        {json.dumps(user_financial_data, ensure_ascii=False, indent=2)}
        
        Provide insights on recommended monthly savings, annual savings, and financial status assessment.
        """

        # 3. Call AI API (Example using OpenAI SDK)
        # Make sure to set OPENAI_API_KEY in your Django settings.py or environment variables
        # openai.api_key = getattr(settings, 'OPENAI_API_KEY', None)
        
        # If using OpenAI:
        # response = openai.chat.completions.create(
        #     model="gpt-4o-mini",
        #     messages=[
        #         {"role": "system", "content": "You are a professional financial planner."},
        #         {"role": "user", "content": prompt}
        #     ],
        #     response_format={"type": "json_object"} # Optional if structured JSON is needed
        # )
        # ai_result = response.choices[0].message.content

        # 4. Mark session as completed
        # (You can also save the raw AI output in a text field on the session model if needed)
        session.status = 'completed'
        session.save()

    except Exception as e:
        print(f"AI Plan Generation Error: {str(e)}")
        session = FinancialInquirySession.objects.filter(id=session_id).first()
        if session:
            session.status = 'failed'
            session.save()