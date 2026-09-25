from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from .ai_services import generate_ai_budget_plan
import openpyxl
from django.http import HttpResponse
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from .models import (
    FinancialInquirySession, Credit, SavingsGoal,
)

from .serializers import (
    RegisterSerializer, SalaryUpdateSerializer, ExtraIncomeUpdateSerializer,
    HousingUpdateSerializer, HasCreditSerializer, CreditSerializer,
    SavingsGoalsUpdateSerializer, MonthlyExpensesSerializer, RecurringExpensesSerializer,
    FinancialAssessmentSerializer, MonthlySavingsAbilitySerializer,
    CompleteOnboardingSerializer, ASSESSMENT_TEXT_TO_CODE, FinancialInquirySessionSerializer
)
from django.contrib.auth import authenticate




class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        email = request.data.get('email', '').strip()
        password = request.data.get('password', '')

        existing_user = User.objects.filter(email__iexact=email).first()

        if existing_user:
            user = authenticate(username=existing_user.username, password=password)

            if user is None:
                return Response(
                    {"error": "Bu e-poçt artıq qeydiyyatdan keçib, şifrə yanlışdır."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            session, _ = FinancialInquirySession.objects.get_or_create(user=user)
            refresh = RefreshToken.for_user(user)

            return Response({
                "success": True,
                "message": "Giriş uğurla tamamlandı.",
                "user": {
                    "fullName": f"{user.first_name} {user.last_name}".strip(),
                    "email": user.email,
                },
                "tokens": {
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                },
                "sessionStatus": session.status,
                "isReturningUser": True
            }, status=status.HTTP_200_OK)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        session = FinancialInquirySession.objects.create(user=user)

        refresh = RefreshToken.for_user(user)

        return Response({
            "success": True,
            "message": "Qeydiyyat uğurla tamamlandı.",
            "user": {
                "fullName": f"{user.first_name} {user.last_name}".strip(),
                "email": user.email,
            },
            "tokens": {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            },
            "sessionStatus": session.status,
            "isReturningUser": False
        }, status=status.HTTP_201_CREATED)


class UpdateSalaryView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        serializer = SalaryUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        session, _ = FinancialInquirySession.objects.get_or_create(user=request.user)
        session.salary = serializer.validated_data['salary']
        session.save()

        return Response({
            "success": True,
            "message": "Aylıq əmək haqqı saxlanıldı.",
            "salary": str(session.salary)
        }, status=status.HTTP_200_OK)


class UpdateExtraIncomeView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        serializer = ExtraIncomeUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        session, _ = FinancialInquirySession.objects.get_or_create(user=request.user)
        session.has_extra_income = serializer.validated_data['hasExtraIncome'] == 'Bəli'
        session.extra_income = serializer.validated_data['extraIncome']
        session.save()

        return Response({
            "success": True,
            "message": "Əlavə gəlir məlumatı saxlanıldı.",
            "hasExtraIncome": session.has_extra_income,
            "extraIncome": str(session.extra_income) if session.extra_income else None
        }, status=status.HTTP_200_OK)


class UpdateHousingView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        serializer = HousingUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        session, _ = FinancialInquirySession.objects.get_or_create(user=request.user)
        session.housing_type = serializer.validated_data['housingType']
        session.housing_amount = serializer.validated_data['housingAmount']
        session.save()

        return Response({
            "success": True,
            "message": "Yaşayış məlumatı saxlanıldı.",
            "housingType": session.housing_type,
            "housingAmount": str(session.housing_amount) if session.housing_amount else None
        }, status=status.HTTP_200_OK)


class UpdateHasCreditView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        serializer = HasCreditSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        session, _ = FinancialInquirySession.objects.get_or_create(user=request.user)
        has_credit = serializer.validated_data['hasCredit'] == 'Bəli'
        session.has_credit = has_credit

        if not has_credit:
            session.credits.all().delete()

        session.save()

        return Response({"success": True, "hasCredit": session.has_credit}, status=status.HTTP_200_OK)


class CreditListCreateView(generics.ListCreateAPIView):
    serializer_class = CreditSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        session, _ = FinancialInquirySession.objects.get_or_create(user=self.request.user)
        return session.credits.all()

    def perform_create(self, serializer):
        session, _ = FinancialInquirySession.objects.get_or_create(user=self.request.user)
        serializer.save(session=session)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response({
            "success": True,
            "message": "Kredit əlavə edildi.",
            "credit": serializer.data
        }, status=status.HTTP_201_CREATED)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({"success": True, "credits": serializer.data})


class CreditDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CreditSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Credit.objects.filter(session__user=self.request.user)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', True)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"success": True, "message": "Kredit yeniləndi.", "credit": serializer.data})

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response({"success": True, "message": "Kredit silindi."}, status=status.HTTP_200_OK)


class UpdateSavingsGoalsView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        serializer = SavingsGoalsUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        session, _ = FinancialInquirySession.objects.get_or_create(user=request.user)
        session.savings_goals.all().delete()

        for goal in serializer.validated_data['goals']:
            SavingsGoal.objects.create(
                session=session,
                goal_id=goal['id'],
                custom_name=goal.get('customName', ''),
                priority=goal['priority'],
                amount=goal['amount'],
            )

        return Response({
            "success": True,
            "message": "Yığım məqsədləri saxlanıldı.",
            "count": session.savings_goals.count()
        }, status=status.HTTP_200_OK)


class UpdateMonthlyExpensesView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        raw = request.data
        cleaned = {
            key: (0 if raw.get(key) in (None, '') else raw.get(key))
            for key in ['market', 'utilities', 'transport', 'restaurant', 'clothing', 'entertainment', 'onlineShopping', 'other']
        }

        serializer = MonthlyExpensesSerializer(data=cleaned)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        session, _ = FinancialInquirySession.objects.get_or_create(user=request.user)
        session.expense_market = data['market']
        session.expense_utilities = data['utilities']
        session.expense_transport = data['transport']
        session.expense_restaurant = data['restaurant']
        session.expense_clothing = data['clothing']
        session.expense_entertainment = data['entertainment']
        session.expense_online_shopping = data['onlineShopping']
        session.expense_other = data['other']
        session.save()

        return Response({
            "success": True,
            "message": "Aylıq xərclər saxlanıldı.",
            "totalMonthlyExpense": str(session.total_monthly_expense)
        }, status=status.HTTP_200_OK)


FIELD_MAP = {
    'market': 'recurring_market',
    'utilities': 'recurring_utilities',
    'transport': 'recurring_transport',
    'restaurant': 'recurring_restaurant',
    'clothing': 'recurring_clothing',
    'entertainment': 'recurring_entertainment',
    'onlineShopping': 'recurring_online_shopping',
    'other': 'recurring_other',
}


class UpdateRecurringExpensesView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        serializer = RecurringExpensesSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        selected = set(serializer.validated_data['recurringExpenses'])

        session, _ = FinancialInquirySession.objects.get_or_create(user=request.user)

        for key, field_name in FIELD_MAP.items():
            setattr(session, field_name, key in selected)

        session.save()

        return Response({
            "success": True,
            "message": "Mütəmadi xərclər saxlanıldı.",
            "recurringExpenses": list(selected)
        }, status=status.HTTP_200_OK)


class UpdateFinancialAssessmentView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        serializer = FinancialAssessmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        session, _ = FinancialInquirySession.objects.get_or_create(user=request.user)
        session.financial_assessment = ASSESSMENT_TEXT_TO_CODE[serializer.validated_data['financialAssessment']]
        session.save()

        return Response({
            "success": True,
            "message": "Maliyyə davranışı saxlanıldı.",
            "financialAssessment": session.financial_assessment
        }, status=status.HTTP_200_OK)


class UpdateMonthlySavingsAbilityView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        serializer = MonthlySavingsAbilitySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        session, _ = FinancialInquirySession.objects.get_or_create(user=request.user)
        session.monthly_savings_ability = serializer.validated_data['monthlySavingsAbility']
        session.save()

        return Response({
            "success": True,
            "message": "Aylıq yığım qabiliyyəti saxlanıldı.",
            "monthlySavingsAbility": session.monthly_savings_ability
        }, status=status.HTTP_200_OK)   


class CompleteOnboardingView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        print("=== /complete/ INCOMING request.data ===", request.data)

        serializer = CompleteOnboardingSerializer(data=request.data)
        if not serializer.is_valid():
            print("=== SERIALIZER ERRORS ===", serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        session, _ = FinancialInquirySession.objects.get_or_create(user=request.user)
        print(f"=== SESSION STATE === status={session.status} salary={session.salary}")

        # Auto-reset stuck 'processing' or 'failed' sessions so users can retry
        # without having to clear their database manually.
        if session.status in ('processing', 'failed'):
            print(f"=== Resetting session from '{session.status}' to allow retry ===")
            session.status = 'pending'
            session.save()

        if not session.salary or session.salary <= 0:
            print("=== BLOCKED: salary is missing or 0 ===")
            return Response(
                {"error": "Əmək haqqı daxil edilməyib. Zəhmət olmasa Step 1-i yenidən tamamlayın."},
                status=status.HTTP_400_BAD_REQUEST
            )

        session.annual_budget_priority = serializer.validated_data['annualBudgetPriority']
        if serializer.validated_data.get('monthlySavingsAbility'):
            session.monthly_savings_ability = serializer.validated_data['monthlySavingsAbility']

        session.status = 'processing'
        session.save()

        try:
            generate_ai_budget_plan(session.id)
        except Exception as e:
            print(f"=== AI generation failed: {e} ===")
            session.status = 'failed'
            session.save()
            return Response(
                {"error": "AI emalı zamanı xəta baş verdi."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        session.refresh_from_db()

        return Response({
            "success": True,
            "message": "Sorğu emal edildi və plan hazırdır.",
            "status": session.status,
            "session_id": session.id
        }, status=status.HTTP_200_OK)


class FinancialInquiryStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        session, _ = FinancialInquirySession.objects.get_or_create(user=request.user)
        is_completed = session.status == 'completed'

        status_messages = {
            'pending': 'Sorğunuz növbəyə gözləyir...',
            'processing': 'AI maliyyə məlumatlarınızı təhlil edir və büdcə planını qurur...',
            'completed': 'Planınız hazırdır!',
            'failed': 'Plan hazırlanarkən xəta baş verdi.'
        }

        return Response({
            "success": True,
            "isCompleted": is_completed,
            "status": session.status,
            "message": status_messages.get(session.status, 'Yüklənir...'),
        }, status=status.HTTP_200_OK)


class RetryPlanGenerationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        session = FinancialInquirySession.objects.filter(user=request.user).first()

        if session and session.status == 'failed':
            session.status = 'processing'
            session.save()

            # FIXED: this used to be a no-op TODO while claiming success.
            try:
                generate_ai_budget_plan(session.id)
                session.refresh_from_db()
            except Exception:
                session.status = 'failed'
                session.save()
                return Response({
                    "success": False,
                    "message": "Yenidən cəhd uğursuz oldu."
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            return Response({
                "success": True,
                "message": "Yenidən emala başlandı.",
                "status": session.status
            }, status=status.HTTP_200_OK)

        return Response({
            "success": False,
            "message": "Yenidən cəhd etmək mümkün deyil."
        }, status=status.HTTP_400_BAD_REQUEST)



class RecalculateBudgetAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request):
        session, _ = FinancialInquirySession.objects.get_or_create(
            user=request.user
        )
        data = request.data

        # 1. Update basic financial fields
        field_map = {
            "salary": "salary",
            "market": "expense_market",
            "utilities": "expense_utilities",
            "transport": "expense_transport",
            "restaurant": "expense_restaurant",
            "clothing": "expense_clothing",
            "entertainment": "expense_entertainment",
            "online_shopping": "expense_online_shopping",
            "other": "expense_other",
        }
        for incoming_key, model_field in field_map.items():
            if incoming_key in data:
                setattr(session, model_field, data[incoming_key])

        # 2. Explicitly handle and save incoming credits if sent in request
        if "credits" in data and isinstance(data["credits"], list):
            session.credits.all().delete()  # Clear old credits
            for credit_data in data["credits"]:
                Credit.objects.create(
                    session=session,
                    monthly=credit_data.get("monthly", 0),
                    remaining=credit_data.get("remaining", 0),
                    rate=credit_data.get("rate", 0),
                    months=credit_data.get("months", 0),
                )

        session.status = "pending"
        session.save()

        # 3. Trigger full AI plan regeneration
        try:
            generate_ai_budget_plan(session.id)
        except Exception as e:
            print(f"*** Recalculate Error: {str(e)} ***")
            session.status = "failed"
            session.save()
            return Response(
                {
                    "status": "error",
                    "message": "Yenidən hesablama zamanı xəta baş verdi.",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        session.refresh_from_db()

        # 4. Return the FULL updated session data so the frontend tables re-render completely
        serializer = FinancialInquirySessionSerializer(session)
        return Response(
            {
                "status": "success",
                "message": "Plan uğurla yenidən hesablandı.",
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class ExportExcelAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        session, _ = FinancialInquirySession.objects.get_or_create(user=request.user)

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Büdcə Planı"

        ws.append(["Şəxsi Maliyyə Büdcə Hesabatı"])
        ws.append([f"Maliyyə Statusu: {session.financial_status}"])
        ws.append([f"Tövsiyə olunan aylıq qənaət: {session.recommended_monthly_savings} AZN"])
        ws.append([f"Tarix: {datetime.now().strftime('%Y-%m-%d')}"])
        ws.append([])

        ws.append(["Ay", "Gəlir (AZN)", "Xərc (AZN)", "Kredit (AZN)", "Qənaət (AZN)", "Balans (AZN)"])

        monthly_table = session.monthly_table or []
        for row in monthly_table:
            ws.append([
                row.get("month_name"),
                row.get("income"),
                row.get("expenses"),
                row.get("credit"),
                row.get("savings"),
                row.get("balance")
            ])

        ws.append([])
        annual = session.annual_totals or {}
        ws.append([
            "İllik Cəmi", annual.get("total_income", 0), annual.get("total_expenses", 0),
            annual.get("total_credit", 0), annual.get("total_savings", 0), annual.get("net_annual_balance", 0)
        ])

        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        date_str = datetime.now().strftime('%Y%m%d')
        response['Content-Disposition'] = f'attachment; filename=budce_plani_{date_str}.xlsx'
        wb.save(response)
        return response


class ExportPDFAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        session, _ = FinancialInquirySession.objects.get_or_create(user=request.user)

        response = HttpResponse(content_type='application/pdf')
        date_str = datetime.now().strftime('%Y%m%d')
        response['Content-Disposition'] = f'attachment; filename=budce_plani_{date_str}.pdf'

        p = canvas.Canvas(response, pagesize=letter)
        width, height = letter

        p.setFont("Helvetica-Bold", 14)
        p.drawString(50, height - 40, "Maliyyə Büdcə Planı Hesabatı")

        p.setFont("Helvetica", 10)
        p.drawString(50, height - 60, f"Maliyyə Statusu: {session.financial_status}")
        p.drawString(50, height - 75, f"Tövsiyə olunan aylıq qənaət: {session.recommended_monthly_savings} AZN")
        p.drawString(50, height - 90, f"Yaradılma tarixi: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

        y = height - 120
        p.setFont("Helvetica-Bold", 9)
        p.drawString(50, y, "Ay          Gəlir        Xərc        Kredit       Qənaət       Balans")
        y -= 15

        p.setFont("Helvetica", 9)
        monthly_table = session.monthly_table or []
        for row in monthly_table:
            if y < 50:
                p.showPage()
                y = height - 50
            line = f"{row.get('month_name', ''):<10} {str(row.get('income', 0)):<10} {str(row.get('expenses', 0)):<10} {str(row.get('credit', 0)):<10} {str(row.get('savings', 0)):<10} {str(row.get('balance', 0))}"
            p.drawString(50, y, line)
            y -= 15

        p.showPage()
        p.save()
        return response
    
    
    
class FinancialSummaryAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        session, _ = FinancialInquirySession.objects.get_or_create(user=request.user)

        if session.status != 'completed':
            return Response({
                "status": "pending",
                "message": "AI analysis is still in progress."
            }, status=202)

        return Response({
            "status": "success",
            "data": {
                "recommended_monthly_savings": float(session.recommended_monthly_savings or 0),
                "recommended_annual_savings": float(session.recommended_annual_savings or 0),
                "financial_status": session.financial_status,
                "financial_status_description": session.financial_status_description,
                "currency": "AZN"
            }
        }, status=200)


class SavingsGoalsProgressAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        session, _ = FinancialInquirySession.objects.get_or_create(user=request.user)

        if session.status != 'completed':
            return Response({
                "status": "pending",
                "message": "AI analysis is still processing."
            }, status=202)

        breakdown = session.savings_goals_breakdown or []

        formatted_goals = []
        for goal in breakdown:
            formatted_goals.append({
                "goal_name": goal.get("goal_name"),
                "target_amount": float(goal.get('target_amount', 0)),
                "current_amount": float(goal.get('current_amount', 0)),
                "progress_percentage": round(float(goal.get("progress_percentage", 0)), 1),
                "recommended_monthly_saving": float(goal.get('recommended_monthly_saving', 0)),
                "priority": goal.get("priority", "Orta prioritet")
            })

        return Response({
            "status": "success",
            "data": formatted_goals
        }, status=200)


class MonthlyBudgetTableAPIView(APIView):
    permission_classes = [IsAuthenticated]

    CATEGORY_KEYS = [
        'market', 'restaurant', 'transport', 'utilities',
        'clothing', 'entertainment', 'online_shopping', 'other'
    ]

    def get(self, request):
        session, _ = FinancialInquirySession.objects.get_or_create(user=request.user)

        if session.status != 'completed':
            return Response({
                "status": "pending",
                "message": "AI analysis is still processing."
            }, status=202)

        monthly_table = session.monthly_table or []
        annual_totals = session.annual_totals or {}

        formatted_table = []
        for row in monthly_table:
            entry = {
                "month_name": row.get("month_name"),
                "income": float(row.get('income', 0)),
                "credit": float(row.get('credit', 0)),
                "savings": float(row.get('savings', 0)),
                "balance": float(row.get('balance', 0)),
                "is_negative": float(row.get('balance', 0)) < 0
            }
            for key in self.CATEGORY_KEYS:
                entry[key] = float(row.get(key, 0))
            formatted_table.append(entry)

        formatted_totals = {
            "total_income": float(annual_totals.get('total_income', 0)),
            "total_credit": float(annual_totals.get('total_credit', 0)),
            "total_savings": float(annual_totals.get('total_savings', 0)),
            "net_annual_balance": float(annual_totals.get('net_annual_balance', 0)),
            "is_negative": float(annual_totals.get('net_annual_balance', 0)) < 0
        }
        for key in self.CATEGORY_KEYS:
            formatted_totals[f"total_{key}"] = float(annual_totals.get(f"total_{key}", 0))

        return Response({
            "status": "success",
            "monthly_table": formatted_table,
            "annual_totals": formatted_totals
        }, status=200)


class BudgetComparisonAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        session, _ = FinancialInquirySession.objects.get_or_create(user=request.user)

        if session.status != 'completed':
            return Response({
                "status": "pending",
                "message": "AI analysis is still processing."
            }, status=202)

        budget_comparison = session.budget_comparison or []

        formatted_comparison = []
        for item in budget_comparison:
            formatted_comparison.append({
                "category_name": item.get("category_name"),
                "percentage": round(float(item.get('percentage', 0)), 1),
                "current_monthly_amount": float(item.get('current_monthly_amount', 0)),
                "recommended_monthly_amount": float(item.get('recommended_monthly_amount', 0)),
                "annual_amount": float(item.get('annual_amount', 0)),
                "status": item.get("status", "Uyğundur"),
                "ai_recommendation": item.get("ai_recommendation", "")
            })

        return Response({
            "status": "success",
            "budget_comparison": formatted_comparison
        }, status=200)