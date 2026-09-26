from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from .ai_services import AIProviderRateLimitError
from .models import FinancialInquirySession


class FinancialSessionIsolationTests(TestCase):
	def setUp(self):
		self.client = APIClient()
		self.first_user = User.objects.create_user(username='first', password='test-password')
		self.second_user = User.objects.create_user(username='second', password='test-password')

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

	def test_complete_uses_fallback_plan_when_groq_request_fails(self):
		session = FinancialInquirySession.objects.create(
			user=self.first_user,
			salary=Decimal('1200'),
		)
		self.client.force_authenticate(user=self.first_user)

		with patch('users.ai_services.Groq', side_effect=TimeoutError('request timed out')):
			with self.assertLogs('users.ai_services', level='ERROR'):
				response = self.client.post(reverse('complete-onboarding'), {}, format='json')

		session.refresh_from_db()
		self.assertEqual(response.status_code, 200)
		self.assertEqual(session.status, 'completed')
		self.assertEqual(len(session.monthly_table), 12)
		self.assertEqual(len(session.budget_comparison), 9)
