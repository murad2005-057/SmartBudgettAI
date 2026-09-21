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
    CompleteOnboardingSerializer, ASSESSMENT_TEXT_TO_CODE
)


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        FinancialInquirySession.objects.create(user=user)

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
            }
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
        session.monthly_savings_ability = serializer.validated_data['monthly_savings_ability']
        session.save()

        return Response({
            "success": True,
            "message": "Aylıq yığım qabiliyyəti saxlanıldı.",
            "monthlySavingsAbility": session.monthly_savings_ability
        }, status=status.HTTP_200_OK)



class CompleteOnboardingView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CompleteOnboardingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        session, _ = FinancialInquirySession.objects.get_or_create(user=request.user)

        if not session.salary or session.salary <= 0:
            return Response(
                {"error": "Əmək haqqı daxil edilməyib."},
                status=status.HTTP_400_BAD_REQUEST
            )

        session.annual_budget_priority = serializer.validated_data['annualBudgetPriority']
        
        session.status = 'processing'
        session.save()

        try:
            generate_ai_budget_plan(session.id)
        except Exception:
            session.status = 'failed'
            session.save()
            return Response(
                {"error": "AI emalı zamanı xəta baş verdi."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response({
            "success": True,
            "message": "Sorğu emal edildi və plan hazırdır.",
            "status": session.status
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
            
            # TODO: Re-trigger your background AI task here
            # generate_ai_budget_plan.delay(session.id)
            
            return Response({
                "success": True,
                "message": "Yenidən emala başlandı."
            }, status=status.HTTP_200_OK)
            
        return Response({
            "success": False,
            "message": "Yenidən cəhd etmək mümkün deyil."
        }, status=status.HTTP_400_BAD_REQUEST)
        


class FinancialSummaryAPIView(APIView):
    def get(self, request, session_id):
        try:
            session = FinancialInquirySession.objects.get(id=session_id)
            
            if session.status != 'completed':
                return Response({
                    "status": "pending", 
                    "message": "AI analysis is still in progress."
                }, status=202)

            return Response({
                "status": "success",
                "data": {
                    "recommended_monthly_savings": f"{session.recommended_monthly_savings:.2f} AZN",
                    "recommended_annual_savings": f"{session.recommended_annual_savings:.2f} AZN",
                    "financial_status": session.financial_status,
                    "financial_status_description": getattr(session, 'financial_status_description', ''),
                    "currency": "AZN"
                }
            }, status=200)

        except FinancialInquirySession.DoesNotExist:
            return Response({"status": "error", "message": "Session not found."}, status=404)
        

class SavingsGoalsProgressAPIView(APIView):
    def get(self, request, session_id):
        try:
            session = FinancialInquirySession.objects.get(id=session_id)
            
            if session.status != 'completed':
                return Response({
                    "status": "pending",
                    "message": "AI analysis is still processing."
                }, status=202)

            breakdown = getattr(session, 'savings_goals_breakdown', [])

            formatted_goals = []
            for goal in breakdown:
                formatted_goals.append({
                    "goal_name": goal.get("goal_name"),
                    "target_amount": f"{goal.get('target_amount', 0):.2f} AZN",
                    "current_amount": f"{goal.get('current_amount', 0):.2f} AZN",
                    "progress_percentage": round(goal.get("progress_percentage", 0), 1),
                    "recommended_monthly_saving": f"{goal.get('recommended_monthly_saving', 0):.2f} AZN",
                    "priority": goal.get("priority", "Normal")
                })

            return Response({
                "status": "success",
                "data": formatted_goals
            }, status=200)

        except FinancialInquirySession.DoesNotExist:
            return Response({"status": "error", "message": "Session not found."}, status=404)
        
        
class MonthlyBudgetTableAPIView(APIView):
    def get(self, request, session_id):
        try:
            session = FinancialInquirySession.objects.get(id=session_id)
            
            if session.status != 'completed':
                return Response({
                    "status": "pending",
                    "message": "AI analysis is still processing."
                }, status=202)

            monthly_table = getattr(session, 'monthly_table', [])
            annual_totals = getattr(session, 'annual_totals', {})

            formatted_table = []
            for row in monthly_table:
                formatted_table.append({
                    "month_name": row.get("month_name"),
                    "income": f"{float(row.get('income', 0)):.2f} AZN",
                    "expenses": f"{float(row.get('expenses', 0)):.2f} AZN",
                    "credit": f"{float(row.get('credit', 0)):.2f} AZN",
                    "savings": f"{float(row.get('savings', 0)):.2f} AZN",
                    "balance": f"{float(row.get('balance', 0)):.2f} AZN",
                    "is_negative": float(row.get('balance', 0)) < 0  # Useful for frontend CSS highlighting
                })

            formatted_totals = {
                "total_income": f"{float(annual_totals.get('total_income', 0)):.2f} AZN",
                "total_expenses": f"{float(annual_totals.get('total_expenses', 0)):.2f} AZN",
                "total_credit": f"{float(annual_totals.get('total_credit', 0)):.2f} AZN",
                "total_savings": f"{float(annual_totals.get('total_savings', 0)):.2f} AZN",
                "net_annual_balance": f"{float(annual_totals.get('net_annual_balance', 0)):.2f} AZN",
                "is_negative": float(annual_totals.get('net_annual_balance', 0)) < 0
            }

            return Response({
                "status": "success",
                "monthly_table": formatted_table,
                "annual_totals": formatted_totals
            }, status=200)

        except FinancialInquirySession.DoesNotExist:
            return Response({"status": "error", "message": "Session not found."}, status=404)
        
        

class BudgetComparisonAPIView(APIView):
    def get(self, request, session_id):
        try:
            session = FinancialInquirySession.objects.get(id=session_id)
            
            if session.status != 'completed':
                return Response({
                    "status": "pending",
                    "message": "AI analysis is still processing."
                }, status=202)

            budget_comparison = getattr(session, 'budget_comparison', [])

            formatted_comparison = []
            for item in budget_comparison:
                formatted_comparison.append({
                    "category_name": item.get("category_name"),
                    "percentage": f"{float(item.get('percentage', 0)):.1f}%",
                    "current_monthly_amount": f"{float(item.get('current_monthly_amount', 0)):.2f} AZN",
                    "recommended_monthly_amount": f"{float(item.get('recommended_monthly_amount', 0)):.2f} AZN",
                    "annual_amount": f"{float(item.get('annual_amount', 0)):.2f} AZN",
                    "status": item.get("status", "Optimal"),
                    "ai_recommendation": item.get("ai_recommendation", "")
                })

            return Response({
                "status": "success",
                "budget_comparison": formatted_comparison
            }, status=200)

        except FinancialInquirySession.DoesNotExist:
            return Response({"status": "error", "message": "Session not found."}, status=404)
        
        



class RecalculateBudgetAPIView(APIView):
    def put(self, request, session_id):
        try:
            session = FinancialInquirySession.objects.get(id=session_id)
            
            data = request.data
            
            if 'salary' in data:
                session.salary = data['salary']
            if 'market' in data:
                session.market = data['market']
            if 'utilities' in data:
                session.utilities = data['utilities']
            if 'transport' in data:
                session.transport = data['transport']
            if 'restaurant' in data:
                session.restaurant = data['restaurant']
            if 'clothing' in data:
                session.clothing = data['clothing']
            if 'entertainment' in data:
                session.entertainment = data['entertainment']
            if 'online_shopping' in data:
                session.online_shopping = data['online_shopping']
            if 'other' in data:
                session.other = data['other']
            
            session.status = 'pending'
            session.save()
            
            generate_ai_budget_plan(session.id)
            
            session.refresh_from_db()
            
            return Response({
                "status": "success",
                "message": "Plan uğurla yenidən hesablandı.",
                "session_id": session.id,
                "financial_status": session.financial_status
            }, status=status.HTTP_200_OK)

        except FinancialInquirySession.DoesNotExist:
            return Response({"status": "error", "message": "Sessiya tapılmadı."}, status=status.HTTP_404_NOT_FOUND)
        
        


class ExportExcelAPIView(APIView):
    def get(self, request, session_id):
        try:
            session = FinancialInquirySession.objects.get(id=session_id)
            
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
            ws.append(["İllik Cəmi", annual.get("total_income", 0), annual.get("total_expenses", 0), annual.get("total_credit", 0), annual.get("total_savings", 0), annual.get("net_annual_balance", 0)])
            
            response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            date_str = datetime.now().strftime('%Y%m%d')
            response['Content-Disposition'] = f'attachment; filename=budce_plani_{session_id}_{date_str}.xlsx'
            wb.save(response)
            return response
            
        except FinancialInquirySession.DoesNotExist:
            return Response({"status": "error", "message": "Sessiya tapılmadı."}, status=status.HTTP_404_NOT_FOUND)
        

class ExportPDFAPIView(APIView):
    def get(self, request, session_id):
        try:
            session = FinancialInquirySession.objects.get(id=session_id)
            
            response = HttpResponse(content_type='application/pdf')
            date_str = datetime.now().strftime('%Y%m%d')
            response['Content-Disposition'] = f'attachment; filename=budce_plani_{session_id}_{date_str}.pdf'
            
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
            
        except FinancialInquirySession.DoesNotExist:
            return Response({"status": "error", "message": "Sessiya tapılmadı."}, status=status.HTTP_404_NOT_FOUND)