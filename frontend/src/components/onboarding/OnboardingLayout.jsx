import React, { useEffect, useState } from 'react'
import { Header } from './Header'
import { QuestionCard } from './QuestionCard'
import { LoadingPlan } from './LoadingPlan'
import { BudgetPlanResults } from './BudgetPlanResults'
import { BUDGET_MONTHS_STORAGE_KEY, useOnboardingForm } from '../../hooks/useOnboardingForm'

export function OnboardingLayout({ userName = 'User' }) {
  const onboarding = useOnboardingForm(userName)
  const [loadingPhase, setLoadingPhase] = useState(null)
  const [submittedFormData, setSubmittedFormData] = useState(null)

  useEffect(() => {
    if (loadingPhase === null) return undefined

    const phaseTimer = window.setTimeout(() => setLoadingPhase(2), 2500)
    const completionTimer = window.setTimeout(() => {
      setLoadingPhase(null)
      onboarding.finishOnboarding()
      onboarding.nextStep()
    }, 5000)

    return () => {
      window.clearTimeout(phaseTimer)
      window.clearTimeout(completionTimer)
    }
  }, [loadingPhase])

  const handleComplete = (formData) => {
    window.localStorage.removeItem(BUDGET_MONTHS_STORAGE_KEY)
    setSubmittedFormData({ ...formData })
    setLoadingPhase(1)
  }

  const handleEdit = () => {
    setSubmittedFormData(null)
    onboarding.goToStep(1)
  }

  return (
    <div className={`onboarding-page-wrapper${onboarding.currentStep > onboarding.totalSteps ? ' results-page-wrapper' : ''}`}>
      <Header />
      <main className={`onboarding-main-container${loadingPhase !== null ? ' loading-main-container' : ''}`}>
        {loadingPhase === null && onboarding.currentStep > onboarding.totalSteps ? (
          <BudgetPlanResults
            key="budget-plan-results"
            formData={submittedFormData || onboarding.formData}
            userName={userName}
            onEdit={handleEdit}
            onNewPlan={() => {
              onboarding.resetOnboarding()
              setSubmittedFormData(null)
            }}
            onReset={() => {
              onboarding.fullReset()
              window.location.reload()
            }}
          />
        ) : loadingPhase === null ? (
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
