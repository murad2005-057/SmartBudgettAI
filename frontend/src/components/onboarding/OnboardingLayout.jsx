import React, { useState } from 'react'
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

  const handleComplete = async (formData) => {
    window.localStorage.removeItem(BUDGET_MONTHS_STORAGE_KEY)
    
    const payload = {
      annualBudgetPriority: formData.annualBudgetPriority || 'balanced',
      monthlySavingsAbility: formData.savingsGoal || formData.monthlySavingsAbility || 0
    }

    // 1. Switch to the loading animation screen immediately
    setLoadingPhase(1)

    // 2. Smooth UI phase transition timer (e.g., move to phase 2 after 2.5s)
    const phaseTimer = window.setTimeout(() => setLoadingPhase(2), 2500)

    try {
      const token = localStorage.getItem('access_token') || localStorage.getItem('token')

      // 3. Fire the API request ONCE right here
      const response = await axios.post(
        'http://127.0.0.1:8000/api/financial-inquiry/complete/', 
        payload,
        {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        }
      )

      const sessionId = response.data.session_id || response.data.sessionId

      if (sessionId) {
        window.clearTimeout(phaseTimer)
        onboarding.finishOnboarding()
        navigate(`/summary/${sessionId}`)
      } else {
        console.error("Session ID tapılmadı:", response.data)
        setLoadingPhase(null)
      }
    } catch (err) {
      console.error("Məlumatı göndərərkən xəta baş verdi:", err)
      window.clearTimeout(phaseTimer)
      setLoadingPhase(null)
    }
  }

  return (
    <div className="onboarding-page-wrapper">
      <Header />
      <main className={`onboarding-main-container${loadingPhase !== null ? ' loading-main-container' : ''}`}>
        {loadingPhase === null ? (
          <QuestionCard
            onboarding={onboarding}
            submittedFormData={null}
            onComplete={handleComplete}
          />
        ) : (
          <LoadingPlan phase={loadingPhase} />
        )}
      </main>
    </div>
  )
}