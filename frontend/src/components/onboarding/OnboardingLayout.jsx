import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'
import { Header } from './Header'
import { QuestionCard } from './QuestionCard'
import { LoadingPlan } from './LoadingPlan'
import { BUDGET_MONTHS_STORAGE_KEY, useOnboardingForm } from '../../hooks/useOnboardingForm'

export function OnboardingLayout({ userName = 'User' }) {
  const onboarding = useOnboardingForm(userName)
  const navigate = useNavigate()
  const [loadingPhase, setLoadingPhase] = useState(null)
  const [submittedFormData, setSubmittedFormData] = useState(null)

  useEffect(() => {
    if (loadingPhase === null) return undefined

    const phaseTimer = window.setTimeout(() => setLoadingPhase(2), 2500)
    
    const completionTimer = window.setTimeout(async () => {
      try {
        const token = localStorage.getItem('access_token') || localStorage.getItem('token')

        const response = await axios.post(
          'http://127.0.0.1:8000/api/financial-inquiry/complete/', 
          submittedFormData || onboarding.formData,
          {
            headers: {
              'Authorization': `Bearer ${token}`
            }
          }
        )

        const sessionId = response.data.session_id || response.data.sessionId

        if (sessionId) {
        onboarding.finishOnboarding()
          navigate(`/summary/${sessionId}`)
        } else {
          console.error("Session ID tapılmadı:", response.data)
          setLoadingPhase(null)
        }
      } catch (err) {
        console.error("Məlumatı göndərərkən xəta baş verdi:", err)
        setLoadingPhase(null)
      }
    }, 5000)

    return () => {
      window.clearTimeout(phaseTimer)
      window.clearTimeout(completionTimer)
    }
  }, [loadingPhase, submittedFormData, onboarding, navigate])

  const handleComplete = (formData) => {
    window.localStorage.removeItem(BUDGET_MONTHS_STORAGE_KEY)
    
    const payload = {
      annualBudgetPriority: formData.annualBudgetPriority || 'balanced',
      monthlySavingsAbility: formData.savingsGoal || formData.monthlySavingsAbility || 0
    }

    setSubmittedFormData(payload)
    setLoadingPhase(1)
  }

  return (
    <div className="onboarding-page-wrapper">
      <Header />
      <main className={`onboarding-main-container${loadingPhase !== null ? ' loading-main-container' : ''}`}>
        {loadingPhase === null ? (
          <QuestionCard
            onboarding={onboarding}
            submittedFormData={submittedFormData}
            onComplete={handleComplete}
          />
        ) : (
          <LoadingPlan phase={loadingPhase} />
        )}
      </main>
    </div>
  )
}