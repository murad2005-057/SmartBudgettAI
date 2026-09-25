import re
from django.contrib.auth.models import User
from rest_framework import serializers
from .models import Credit, SavingsGoal, FinancialInquirySession


class RegisterSerializer(serializers.ModelSerializer):
    fullName = serializers.CharField(write_only=True, required=True)
    password = serializers.CharField(write_only=True, required=True)
    email = serializers.EmailField(required=True)

    class Meta:
        model = User
        fields = ('fullName', 'email', 'password')

    def validate_fullName(self, value):
        if not value.strip():
            raise serializers.ValidationError("Ad və soyad hissəsini doldurun.")
        return value

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Bu email artıq istifadə olunub.")
        return value

    def validate_password(self, value):
        if len(value) < 8 or not re.search(r'[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>/?]', value):
            raise serializers.ValidationError(
                "Şifrə ən azı 8 simvol olmalı və xüsusi simvol ehtiva etməlidir."
            )
        return value

    def create(self, validated_data):
        full_name = validated_data['fullName'].strip()
        parts = full_name.split(' ', 1)
        first_name = parts[0]
        last_name = parts[1] if len(parts) > 1 else ''

        user = User.objects.create_user(
            username=validated_data['email'],
            email=validated_data['email'],
            first_name=first_name,
            last_name=last_name,
            password=validated_data['password'],
        )
        return user


class SalaryUpdateSerializer(serializers.Serializer):
    salary = serializers.DecimalField(max_digits=12, decimal_places=2)

    def validate_salary(self, value):
        if value <= 0:
            raise serializers.ValidationError("Əmək haqqı müsbət ədəd olmalıdır.")
        return value


class ExtraIncomeUpdateSerializer(serializers.Serializer):
    hasExtraIncome = serializers.ChoiceField(choices=['Bəli', 'Xeyr'])
    extraIncome = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True)

    def validate(self, attrs):
        has_extra = attrs['hasExtraIncome'] == 'Bəli'

        if has_extra:
            amount = attrs.get('extraIncome')
            if amount is None or amount <= 0:
                raise serializers.ValidationError(
                    {"extraIncome": "Əlavə gəlir varsa, məbləğ daxil edilməlidir."}
                )
        else:
            attrs['extraIncome'] = None

        return attrs


class HousingUpdateSerializer(serializers.Serializer):
    housingType = serializers.ChoiceField(choices=['Özümündür', 'Kirayədir', 'İpotekadır'])
    housingAmount = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True)

    def validate(self, attrs):
        housing_type = attrs['housingType']

        if housing_type == 'Özümündür':
            attrs['housingAmount'] = None
        else:
            amount = attrs.get('housingAmount')
            if amount is None or amount <= 0:
                field_name = 'Aylıq kirayə' if housing_type == 'Kirayədir' else 'Aylıq ipoteka'
                raise serializers.ValidationError(
                    {"housingAmount": f"{field_name} məbləği məcburidir."}
                )

        return attrs


class HasCreditSerializer(serializers.Serializer):
    hasCredit = serializers.ChoiceField(choices=['Bəli', 'Xeyr'])


class CreditSerializer(serializers.ModelSerializer):
    class Meta:
        model = Credit
        fields = ('id', 'monthly', 'remaining', 'rate', 'months')

    def validate_monthly(self, value):
        if value <= 0:
            raise serializers.ValidationError("Aylıq ödəniş 0-dan böyük olmalıdır.")
        return value

    def validate_remaining(self, value):
        if value <= 0:
            raise serializers.ValidationError("Qalıq məbləğ 0-dan böyük olmalıdır.")
        return value

    def validate_months(self, value):
        if value <= 0:
            raise serializers.ValidationError("Qalan ay sayı müsbət tam ədəd olmalıdır.")
        return value


class SavingsGoalSerializer(serializers.Serializer):
    # FIXED: was a plain CharField, accepting any string. Tied to the model's
    # actual GOAL_CHOICES now, so an invalid/typo'd goal id is rejected here
    # instead of silently reaching the database.
    id = serializers.ChoiceField(choices=[c[0] for c in SavingsGoal.GOAL_CHOICES])
    customName = serializers.CharField(required=False, allow_blank=True, max_length=100)

    priority = serializers.ChoiceField(choices=[c[0] for c in SavingsGoal.PRIORITY_CHOICES])
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Hədəf məbləği müsbət ədəd olmalıdır.")
        return value

    def validate(self, attrs):
        if attrs['id'] == 'other' and not attrs.get('customName', '').strip():
            raise serializers.ValidationError(
                {"customName": "'Digər' seçildikdə məqsədin adı daxil edilməlidir."}
            )
        return attrs


class SavingsGoalsUpdateSerializer(serializers.Serializer):
    goals = SavingsGoalSerializer(many=True)


class MonthlyExpensesSerializer(serializers.Serializer):
    market = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default=0)
    utilities = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default=0)
    transport = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default=0)
    restaurant = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default=0)
    clothing = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default=0)
    entertainment = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default=0)
    onlineShopping = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default=0)
    other = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default=0)

    def validate(self, attrs):
        for field, value in attrs.items():
            if value is not None and value < 0:
                raise serializers.ValidationError({field: "Mənfi məbləğ qəbul edilmir."})
        return attrs


EXPENSE_CATEGORY_KEYS = ['market', 'clothing', 'restaurant', 'entertainment', 'transport', 'onlineShopping', 'utilities', 'other']

class RecurringExpensesSerializer(serializers.Serializer):
    recurringExpenses = serializers.ListField(
        child=serializers.CharField(), required=False, default=list
    )

    def validate_recurringExpenses(self, value):
        invalid = set(value) - set(EXPENSE_CATEGORY_KEYS)
        if invalid:
            raise serializers.ValidationError(f"Naməlum xərc kateqoriyası: {', '.join(invalid)}")
        return value


ASSESSMENT_TEXT_TO_CODE = {
    'Pulumu yaxşı idarə edə bilirəm': 'good_manager',
    'Bəzən planı poza bilirəm': 'sometimes_breaks_plan',
    'Ay sonuna pul qalmır': 'nothing_left',
}

class FinancialAssessmentSerializer(serializers.Serializer):
    financialAssessment = serializers.ChoiceField(choices=list(ASSESSMENT_TEXT_TO_CODE.keys()))


class MonthlySavingsAbilitySerializer(serializers.Serializer):
    monthlySavingsAbility = serializers.ChoiceField(
        choices=[c[0] for c in __import__('users.models', fromlist=['FinancialInquirySession']).FinancialInquirySession.SAVINGS_ABILITY_CHOICES]
    )
    
ANNUAL_PRIORITY_CHOICES = [
    ('Daha çox qənaət etmək', 'Daha çox qənaət etmək'),
    ('Xərclərə nəzarət etmək', 'Xərclərə nəzarət etmək'),
    ('Borcları azaltmaq', 'Borcları azaltmaq'),
    ('Gəliri daha düzgün bölüşdürmək', 'Gəliri daha düzgün bölüşdürmək'),
    ('Gözlənilməz xərclərə hazır olmaq', 'Gözlənilməz xərclərə hazır olmaq'),
    ('Gələcək üçün pul toplamaq', 'Gələcək üçün pul toplamaq'),
    # NOTE: the 4 options below are NOT in the model's ANNUAL_PRIORITY_CHOICES.
    # They'll validate and save fine (Django doesn't enforce `choices` at the
    # DB level), but they're undeclared on the model — either add them to
    # FinancialInquirySession.ANNUAL_PRIORITY_CHOICES too, or remove them here
    # so both sides agree on the same 6 options. Left in for now since removing
    # them without knowing which your frontend actually uses could break it.
    ('Yığımları artırmaq', 'Yığımları artırmaq'),
    ('Borcları daha sürətli bağlamaq', 'Borcları daha sürətli bağlamaq'),
    ('Balanslı yaşamaq (yığım + əyləncə)', 'Balanslı yaşamaq (yığım + əyləncə)'),
    ('Gələcəyə yatırım etmək', 'Gələcəyə yatırım etmək'),
]

VALID_ANNUAL_PRIORITIES = [c[0] for c in ANNUAL_PRIORITY_CHOICES]

_DEFAULT_PRIORITY = 'Gəliri daha düzgün bölüşdürmək'

class CompleteOnboardingSerializer(serializers.Serializer):
    annualBudgetPriority = serializers.CharField(
        required=False,
        allow_blank=True,
        default=_DEFAULT_PRIORITY
    )
    monthlySavingsAbility = serializers.CharField(required=False, allow_blank=True, default='')

    def validate_annualBudgetPriority(self, value):
        # Empty string → use safe default
        if not value or not value.strip():
            return _DEFAULT_PRIORITY
        if value not in VALID_ANNUAL_PRIORITIES:
            print(f"=== UNKNOWN annualBudgetPriority: '{value}' — using default ===")
            return _DEFAULT_PRIORITY
        return value


class FinancialInquirySessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinancialInquirySession
        fields = '__all__'
        read_only_fields = ['user']