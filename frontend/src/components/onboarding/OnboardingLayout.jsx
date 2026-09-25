import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'
import { Header } from './Header'
import { QuestionCard } from './QuestionCard'
import { LoadingPlan } from './LoadingPlan'
import { BUDGET_MONTHS_STORAGE_KEY, useOnboardingForm } from '../../hooks/useOnboardingForm'
import { updateSalary } from '../../services/api'

const VALID_PRIORITIES = [
  'Daha çox qənaət etmək',
  'Xərclərə nəzarət etmək',
  'Borcları azaltmaq',
  'Gəliri daha düzgün bölüşdürmək',
  'Gözlənilməz xərclərə hazır olmaq',
  'Gələcək üçün pul toplamaq',
]

export function OnboardingLayout({ userName = 'User' }) {
  const onboarding = useOnboardingForm(userName)
  const navigate = useNavigate()
  const [loadingPhase, setLoadingPhase] = useState(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState(null)

  const handleComplete = async (formData) => {
    if (isSubmitting) return
    setIsSubmitting(true)
    setSubmitError(null)
    window.localStorage.removeItem(BUDGET_MONTHS_STORAGE_KEY)

    // Pre-flight: re-sync salary in case Step 1 API call failed silently.
    // This ensures the backend never blocks /complete/ with "salary missing".
    const salary = Number(formData.salary)
    if (salary > 0) {
      try {
        await updateSalary(salary)
      } catch (salaryErr) {
        console.warn('Salary pre-sync failed (non-fatal):', salaryErr)
      }
    }

    const annualBudgetPriority = VALID_PRIORITIES.includes(formData.annualBudgetPriority)
      ? formData.annualBudgetPriority
      : 'Gəliri daha düzgün bölüşdürmək'

    const payload = {
      annualBudgetPriority,
      monthlySavingsAbility: String(formData.monthlySavingsAbility || '')
    }

    setLoadingPhase(1)
    window.setTimeout(() => setLoadingPhase(2), 1500)

    try {
      const token = localStorage.getItem('access_token') || localStorage.getItem('token') || localStorage.getItem('accessToken')

      const response = await axios.post(
        'http://127.0.0.1:8000/api/financial-inquiry/complete/',
        payload,
        { headers: { 'Authorization': `Bearer ${token}` } }
      )

      const sessionId = response.data.session_id || response.data.sessionId

      if (sessionId) {
        onboarding.finishOnboarding()
        navigate(`/summary/${sessionId}`)
      } else {
        console.error('Session ID tapılmadı:', response.data)
        setLoadingPhase(null)
        setSubmitError('Server cavabı düzgün deyil. Yenidən cəhd edin.')
        setIsSubmitting(false)
      }
    } catch (err) {
      const errBody = err.response?.data
      const errMsg = errBody?.error || 'Xəta baş verdi. Yenidən cəhd edin.'
      console.error('POST /complete/ failed:', err.response?.status, errBody)
      setLoadingPhase(null)
      setSubmitError(errMsg)
      setIsSubmitting(false)
    }
  }

  return (
    <div className="onboarding-page-wrapper">
      <Header />
      <main className={`onboarding-main-container${loadingPhase !== null ? ' loading-main-container' : ''}`}>
        {loadingPhase === null ? (
          <>
            {submitError && (
              <div role="alert" style={{ color: '#ef4444', textAlign: 'center', padding: '0.75rem 1rem', marginBottom: '0.5rem', background: '#fee2e2', borderRadius: '8px', fontSize: '0.9rem' }}>
                ⚠️ {submitError}
              </div>
            )}
            <QuestionCard
              onboarding={onboarding}
              submittedFormData={null}
              onComplete={handleComplete}
              isSubmitting={isSubmitting}
            />
          </>
        ) : (
          <LoadingPlan phase={loadingPhase} />
        )}
      </main>
    </div>
  )
}
