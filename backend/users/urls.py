from django.urls import path
from .views import (
    RegisterView, UpdateSalaryView, UpdateExtraIncomeView, UpdateHousingView,
    UpdateHasCreditView, CreditListCreateView, CreditDetailView,
    UpdateSavingsGoalsView, UpdateMonthlyExpensesView, UpdateRecurringExpensesView,
    UpdateFinancialAssessmentView,
    
)

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('financial-inquiry/salary/', UpdateSalaryView.as_view(), name='update-salary'),
    path('financial-inquiry/extra-income/', UpdateExtraIncomeView.as_view(), name='update-extra-income'),
    path('financial-inquiry/housing/', UpdateHousingView.as_view(), name='update-housing'),
    path('financial-inquiry/has-credit/', UpdateHasCreditView.as_view(), name='update-has-credit'),
    path('financial-inquiry/credits/', CreditListCreateView.as_view(), name='credit-list-create'),
    path('financial-inquiry/credits/<int:pk>/', CreditDetailView.as_view(), name='credit-detail'),
    path('financial-inquiry/savings-goals/', UpdateSavingsGoalsView.as_view(), name='update-savings-goals'),
    path('financial-inquiry/monthly-expenses/', UpdateMonthlyExpensesView.as_view(), name='update-monthly-expenses'),
    path('financial-inquiry/recurring-expenses/', UpdateRecurringExpensesView.as_view(), name='update-recurring-expenses'),
    path('financial-inquiry/financial-assessment/', UpdateFinancialAssessmentView.as_view(), name='update-financial-assessment'),



]