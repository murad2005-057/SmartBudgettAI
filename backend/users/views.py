from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from .models import FinancialInquirySession, FinancialInquirySession
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from .models import Credit, SavingsGoal

from .serializers import (
    RegisterSerializer, SalaryUpdateSerializer, ExtraIncomeUpdateSerializer,
    HousingUpdateSerializer, HasCreditSerializer, CreditSerializer,
    SavingsGoalsUpdateSerializer, MonthlyExpensesSerializer, RecurringExpensesSerializer,
    FinancialAssessmentSerializer, ASSESSMENT_TEXT_TO_CODE,
    
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
        session.savings_goals.all().delete()  # replace entirely — deselected goal = removed

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