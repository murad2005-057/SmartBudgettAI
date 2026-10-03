from decimal import Decimal
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from django.urls import reverse
from rest_framework.test import APIClient

from .ai_services import AIProviderRateLimitError, get_jev_combined_prompt
from .models import FinancialInquirySession


class FinancialSessionIsolationTests(TestCase):
	def setUp(self):
		self.client = APIClient()
		self.first_user = User.objects.create_user(username='first', password='test-password')
		self.second_user = User.objects.create_user(username='second', password='test-password')

	def test_register_returns_json_when_an_unexpected_error_occurs(self):
		with patch('users.views.User.objects.filter', side_effect=RuntimeError('database unavailable')):
			with self.assertLogs('users.views', level='ERROR'):
				response = self.client.post(
					reverse('register'),
					{
						'fullName': 'Test User',
						'email': 'test@example.com',
						'password': 'valid-password!',
					},
					format='json',
				)

		self.assertEqual(response.status_code, 500)
		self.assertEqual(response['Content-Type'], 'application/json')
		self.assertEqual(response.json(), {'error': 'database unavailable'})

	def test_register_keeps_validation_errors_as_client_errors(self):
		response = self.client.post(
			reverse('register'),
			{'fullName': '', 'email': 'invalid', 'password': 'short'},
			format='json',
		)

		self.assertEqual(response.status_code, 400)

	def test_each_user_reads_their_own_saved_plan(self):
		FinancialInquirySession.objects.create(
			user=self.first_user,
			status='completed',
			salary=Decimal('1200'),
			recommended_monthly_savings=Decimal('200'),
		)
		FinancialInquirySession.objects.create(
			user=self.second_user,
			status='completed',
			salary=Decimal('2400'),
			recommended_monthly_savings=Decimal('500'),
		)

		self.client.force_authenticate(user=self.first_user)
		first_response = self.client.get(reverse('financial-summary'))
		self.client.force_authenticate(user=self.second_user)
		second_response = self.client.get(reverse('financial-summary'))

		self.assertEqual(first_response.data['data']['recommended_monthly_savings'], 200.0)
		self.assertEqual(second_response.data['data']['recommended_monthly_savings'], 500.0)
		self.assertEqual(FinancialInquirySession.objects.count(), 2)

	def test_complete_returns_logged_error_when_generation_fails(self):
		session = FinancialInquirySession.objects.create(
			user=self.first_user,
			salary=Decimal('1200'),
		)
		self.client.force_authenticate(user=self.first_user)

		with patch('users.views.generate_ai_budget_plan', side_effect=RuntimeError('provider unavailable')):
			with self.assertLogs('users.views', level='ERROR'):
				response = self.client.post(reverse('complete-onboarding'), {}, format='json')

		session.refresh_from_db()
		self.assertEqual(response.status_code, 500)
		self.assertEqual(response.data['error'], 'AI emalı zamanı xəta baş verdi.')
		self.assertEqual(session.status, 'failed')

	def test_complete_returns_retryable_response_when_ai_provider_is_rate_limited(self):
		session = FinancialInquirySession.objects.create(
			user=self.first_user,
			salary=Decimal('1200'),
		)
		self.client.force_authenticate(user=self.first_user)

		with patch(
			'users.views.generate_ai_budget_plan',
			side_effect=AIProviderRateLimitError(retry_after='180'),
		):
			response = self.client.post(reverse('complete-onboarding'), {}, format='json')

		session.refresh_from_db()
		self.assertEqual(response.status_code, 503)
		self.assertEqual(response['Retry-After'], '180')
		self.assertEqual(response.data['retry_after'], '180')
		self.assertEqual(session.status, 'failed')

	def test_complete_returns_fallback_plan_when_api_keys_are_missing(self):
		session = FinancialInquirySession.objects.create(
			user=self.first_user,
			salary=Decimal('1200'),
		)
		self.client.force_authenticate(user=self.first_user)

		with patch.dict('os.environ', {'API_KEY': ''}), patch('users.ai_services.settings.GROQ_API_KEY', ''):
			with self.assertLogs('users.ai_services', level='ERROR'):
				response = self.client.post(reverse('complete-onboarding'), {}, format='json')

		session.refresh_from_db()
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data['status'], 'completed')
		self.assertEqual(len(response.data['fallback_plan']['monthly_table']), 12)
		self.assertEqual(len(response.data['fallback_plan']['budget_comparison']), 9)
		self.assertEqual(session.status, 'completed')

	def test_complete_uses_api_key_alias_for_groq(self):
		session = FinancialInquirySession.objects.create(
			user=self.first_user,
			salary=Decimal('1200'),
		)
		self.client.force_authenticate(user=self.first_user)

		with patch.dict('os.environ', {'API_KEY': 'test-key'}), patch(
			'users.ai_services.settings.GROQ_API_KEY', ''
		), patch('users.ai_services.Groq', side_effect=TimeoutError('request timed out')) as groq_client:
			with self.assertLogs('users.ai_services', level='ERROR'):
				response = self.client.post(reverse('complete-onboarding'), {}, format='json')

		self.assertEqual(response.status_code, 200)
		self.assertTrue(response.data['fallback_plan'])
		groq_client.assert_called_once_with(api_key='test-key', timeout=7.0, max_retries=0)

	def test_retry_rejects_recently_processing_session_with_conflict(self):
		FinancialInquirySession.objects.create(
			user=self.first_user,
			salary=Decimal('1200'),
			status='processing',
		)
		self.client.force_authenticate(user=self.first_user)

		with patch('users.views.generate_ai_budget_plan') as generate_plan:
			response = self.client.post(reverse('retry-plan'), {}, format='json')

		self.assertEqual(response.status_code, 409)
		self.assertEqual(response.data['code'], 'PLAN_ALREADY_PROCESSING')
		generate_plan.assert_not_called()

	def test_retry_recovers_stale_processing_session(self):
		session = FinancialInquirySession.objects.create(
			user=self.first_user,
			salary=Decimal('1200'),
			status='processing',
		)
		FinancialInquirySession.objects.filter(pk=session.pk).update(
			updated_at=timezone.now() - timedelta(minutes=1),
		)
		self.client.force_authenticate(user=self.first_user)

		def complete_plan(session_id):
			FinancialInquirySession.objects.filter(pk=session_id).update(status='completed')

		with patch('users.views.generate_ai_budget_plan', side_effect=complete_plan):
			response = self.client.post(reverse('retry-plan'), {}, format='json')

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data['status'], 'completed')

	def test_get_jev_combined_prompt_contains_required_schema_and_rules(self):
		financial_data = {
			"salary": 2200,
			"extra_income": 300,
			"monthly_expenses": {"market": 420, "utilities": 170},
		}

		prompt = get_jev_combined_prompt(financial_data, 2500)

		self.assertIn("Total Monthly Income: 2500.0 AZN", prompt)
		self.assertIn('"recommended_monthly_savings": float', prompt)
		self.assertIn('"budget_comparison": [', prompt)
		self.assertIn('SUM(Recommended Monthly Amounts) = Reliable Monthly Income.', prompt)
		self.assertIn('"financial_status": Exactly one of:', prompt)
		self.assertIn('market, restaurant, transport, utilities, clothing, entertainment, online_shopping, other, credit', prompt)

	def test_complete_uses_fallback_plan_when_jev_ai_request_fails(self):
		session = FinancialInquirySession.objects.create(
			user=self.first_user,
			salary=Decimal('1200'),
		)
		self.client.force_authenticate(user=self.first_user)

		with patch('users.ai_services.settings.GROQ_API_KEY', 'test-key'), patch(
			'users.ai_services.Groq', side_effect=TimeoutError('request timed out')
		):
			with self.assertLogs('users.ai_services', level='ERROR'):
				response = self.client.post(reverse('complete-onboarding'), {}, format='json')

		session.refresh_from_db()
		self.assertEqual(response.status_code, 200)
		self.assertEqual(session.status, 'completed')
		self.assertEqual(len(session.monthly_table), 12)
		self.assertEqual(len(session.budget_comparison), 9)

	def test_recalculate_applies_modified_recommendations_and_recomputes_comparison(self):
		session = FinancialInquirySession.objects.create(
			user=self.first_user,
			salary=Decimal('2000'),
			extra_income=Decimal('500'),
		)
		self.client.force_authenticate(user=self.first_user)

		def generate_plan(session_id):
			FinancialInquirySession.objects.filter(pk=session_id).update(
				status='completed',
				budget_comparison=[
					{
						'category_name': 'restaurant',
						'current_monthly_amount': 400,
						'recommended_monthly_amount': 340,
					},
					{
						'category_name': 'utilities',
						'current_monthly_amount': 300,
						'recommended_monthly_amount': 300,
					},
					{
						'category_name': 'other',
						'current_monthly_amount': 100,
						'recommended_monthly_amount': 80,
					},
				],
			)

		with patch('users.views.generate_ai_budget_plan', side_effect=generate_plan):
			response = self.client.put(
				reverse('budget-recalculate'),
				{
					'modifiedFields': {
						'comparison:restaurant': {'category_name': 'restaurant', 'new_value': 1000},
						'comparison:utilities': {'category_name': 'utilities', 'new_value': 350},
						'comparison:other': {'category_name': 'other', 'new_value': 0},
					},
				},
				format='json',
			)

		self.assertEqual(response.status_code, 200)
		comparison = {
			row['category_name']: row
			for row in response.data['data']['budget_comparison']
		}
		self.assertEqual(comparison['restaurant']['percentage'], 40.0)
		self.assertEqual(comparison['restaurant']['annual_amount'], 12000.0)
		self.assertEqual(comparison['restaurant']['status'], 'Yüksək xərc')
		self.assertEqual(
			comparison['restaurant']['ai_recommendation'],
			'Xərc tövsiyə olunan səviyyədən yüksəkdir.',
		)
		self.assertEqual(comparison['utilities']['status'], 'Prioritet ödəniş')
		self.assertEqual(comparison['utilities']['ai_recommendation'], 'Ödənişini vaxtında et.')
		self.assertEqual(comparison['other']['status'], 'Qənaətlidir')
		self.assertEqual(comparison['other']['ai_recommendation'], 'Bu sahədə qənaət edirsən.')
