from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator


class FinancialInquirySession(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='financial_session')
    created_at = models.DateTimeField(auto_now_add=True)
    is_completed = models.BooleanField(default=False)

    # Income & Housing fields
    salary = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    has_extra_income = models.BooleanField(null=True, blank=True)
    extra_income = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    HOUSING_CHOICES = [
        ('Özümündür', 'Özümündür'),
        ('Kirayədir', 'Kirayədir'),
        ('İpotekadır', 'İpotekadır'),
    ]
    housing_type = models.CharField(max_length=20, choices=HOUSING_CHOICES, null=True, blank=True)
    housing_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    
    has_credit = models.BooleanField(null=True, blank=True)

    # Expense fields
    expense_market = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    expense_utilities = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    expense_transport = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    expense_restaurant = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    expense_clothing = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    expense_entertainment = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    expense_online_shopping = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    expense_other = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])

    # Recurring flags
    recurring_market = models.BooleanField(default=False)
    recurring_utilities = models.BooleanField(default=False)
    recurring_transport = models.BooleanField(default=False)
    recurring_restaurant = models.BooleanField(default=False)
    recurring_clothing = models.BooleanField(default=False)
    recurring_entertainment = models.BooleanField(default=False)
    recurring_online_shopping = models.BooleanField(default=False)
    recurring_other = models.BooleanField(default=False)

    ASSESSMENT_CHOICES = [
        ('good_manager', 'Pulumu yaxşı idarə edə bilirəm'),
        ('sometimes_breaks_plan', 'Bəzən planı poza bilirəm'),
        ('nothing_left', 'Ay sonuna pul qalmır'),
    ]
    financial_assessment = models.CharField(max_length=30, choices=ASSESSMENT_CHOICES, blank=True)

    @property
    def total_monthly_expense(self):
        return (
            self.expense_market + self.expense_utilities + self.expense_transport +
            self.expense_restaurant + self.expense_clothing + self.expense_entertainment +
            self.expense_online_shopping + self.expense_other
        )

    def __str__(self):
        return f"Session({self.user.email})"


class Credit(models.Model):
    session = models.ForeignKey(FinancialInquirySession, on_delete=models.CASCADE, related_name='credits')
    monthly = models.DecimalField(max_digits=12, decimal_places=2)
    remaining = models.DecimalField(max_digits=12, decimal_places=2)
    rate = models.DecimalField(max_digits=5, decimal_places=2)
    months = models.PositiveIntegerField()

    def __str__(self):
        return f"Credit({self.session.user.email}) - {self.monthly}/ay"


class SavingsGoal(models.Model):
    GOAL_CHOICES = [
        ('travel', 'travel'), ('home', 'home'), ('car', 'car'),
        ('education', 'education'), ('wedding', 'wedding'),
        ('business', 'business'), ('emergency', 'emergency'), ('other', 'other'),
    ]
    PRIORITY_CHOICES = [
        ('Aşağı prioritet', 'Aşağı prioritet'),
        ('Orta prioritet', 'Orta prioritet'),
        ('Yuxarı prioritet', 'Yuxarı prioritet'),
    ]

    session = models.ForeignKey(FinancialInquirySession, on_delete=models.CASCADE, related_name='savings_goals')
    goal_id = models.CharField(max_length=50, choices=GOAL_CHOICES)
    custom_name = models.CharField(max_length=100, blank=True)  # only used when goal_id == 'other'
    priority = models.CharField(max_length=50, choices=PRIORITY_CHOICES, default='Orta prioritet')
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        unique_together = ('session', 'goal_id')

    def __str__(self):
        return f"{self.session.user.email} - {self.goal_id}"