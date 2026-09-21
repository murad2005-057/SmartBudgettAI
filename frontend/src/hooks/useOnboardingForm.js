import { useEffect, useState } from 'react'
export const ONBOARDING_STORAGE_KEY = 'smartbudget-onboarding-state'
export const ONBOARDING_ACTIVE_KEY = 'smartbudget-onboarding-active'
export const ACCOUNT_STORAGE_KEY = 'smartbudget-account-state'
export const BUDGET_MONTHS_STORAGE_KEY = 'smartbudget-budget-plan-months'

import { 
  updateSalary, 
  updateExtraIncome, 
  updateHousing, 
  updateHasCredit, 
  syncCredits, 
  updateSavingsGoals, 
  updateMonthlyExpenses, 
  updateRecurringExpenses, 
  updateFinancialAssessment,
  updateMonthlySavingsAbility,
  completeOnboarding
} from '../services/api'

const EMPTY_CREDIT = () => ({
  monthly: '',
  remaining: '',
  rate: '',
  months: ''
})

const DEFAULT_GOAL_PRIORITY = 'Orta prioritet'

const createInitialFormData = () => ({
  salary: '',
  hasExtraIncome: null,
  extraIncome: '',
  housingType: null,
  housingAmount: '',
  hasCredit: null,
  credits: [EMPTY_CREDIT()],
  utilities: '',
  groceries: '',
  transport: '',
  monthlyExpenses: {
    market: '',
    utilities: '',
    transport: '',
    restaurant: '',
    clothing: '',
    entertainment: '',
    onlineShopping: '',
    other: ''
  },
  recurringExpenses: [],
  savingsGoal: '',
  savingsGoals: [],
  financialAssessment: '',
  monthlySavingsAbility: '',
  annualBudgetPriority: '',
  hasDebts: null,
  debtAmount: '',
  entertainment: '',
  financialGoal: ''
})

const getSavedState = () => {
  try {
    const savedState = window.localStorage.getItem(ONBOARDING_STORAGE_KEY)
    return savedState ? JSON.parse(savedState) : null
  } catch {
    return null
  }
}

export function useOnboardingForm(initialUserName = 'User') {
  const savedState = getSavedState()
  const [currentStep, setCurrentStep] = useState(savedState?.currentStep || 1)
  const [userName] = useState(initialUserName)
  const [stepError, setStepError] = useState(null)
  const [formData, setFormData] = useState(() => ({
    ...createInitialFormData(),
    ...(savedState?.formData || {}),
    monthlyExpenses: {
      ...createInitialFormData().monthlyExpenses,
      ...(savedState?.formData?.monthlyExpenses || {})
    }
  }))

  const totalSteps = 10

  useEffect(() => {
    window.localStorage.setItem(ONBOARDING_STORAGE_KEY, JSON.stringify({ currentStep, formData }))
  }, [currentStep, formData])

  const finishOnboarding = () => {
    window.localStorage.setItem(ONBOARDING_ACTIVE_KEY, 'true')
  }

  const resetOnboarding = () => {
    window.localStorage.removeItem(ONBOARDING_STORAGE_KEY)
    window.localStorage.removeItem(BUDGET_MONTHS_STORAGE_KEY)
    setCurrentStep(1)
    setFormData(createInitialFormData())
  }

  const fullReset = () => {
    window.localStorage.removeItem(ONBOARDING_STORAGE_KEY)
    window.localStorage.removeItem(ONBOARDING_ACTIVE_KEY)
    window.localStorage.removeItem(ACCOUNT_STORAGE_KEY)
    window.localStorage.removeItem(BUDGET_MONTHS_STORAGE_KEY)
    setCurrentStep(1)
    setFormData(createInitialFormData())
  }

  const updateField = (fieldName, value) => {
    setFormData((prev) => ({ ...prev, [fieldName]: value }))
  }

  const updateMonthlyExpense = (expenseId, value) => {
    setFormData((prev) => ({
      ...prev,
      monthlyExpenses: { ...prev.monthlyExpenses, [expenseId]: value }
    }))
  }

  const clearMonthlyExpense = (expenseId) => {
    updateMonthlyExpense(expenseId, '')
  }

  const toggleRecurringExpense = (expenseId) => {
    setFormData((prev) => {
      const isSelected = prev.recurringExpenses.includes(expenseId)
      const recurringExpenses = isSelected
        ? prev.recurringExpenses.filter((id) => id !== expenseId)
        : [...prev.recurringExpenses, expenseId]

      return { ...prev, recurringExpenses }
    })
  }

  const clearField = (fieldName) => {
    setFormData((prev) => ({ ...prev, [fieldName]: '' }))
  }

  const addCredit = () => {
    setFormData((prev) => ({
      ...prev,
      credits: [...prev.credits, EMPTY_CREDIT()]
    }))
  }

  const updateCredit = (index, field, value) => {
    setFormData((prev) => {
      const credits = prev.credits.map((c, i) =>
        i === index ? { ...c, [field]: value } : c
      )
      return { ...prev, credits }
    })
  }

  const clearCredit = (index, field) => {
    updateCredit(index, field, '')
  }

  const removeCredit = (index) => {
    setFormData((prev) => ({
      ...prev,
      credits: prev.credits.filter((_, i) => i !== index)
    }))
  }

  const applySavingsGoals = (goals) => {
    const savingsGoal = goals.reduce((total, goal) => total + (Number(goal.amount) || 0), 0).toString()
    updateField('savingsGoals', goals)
    updateField('savingsGoal', savingsGoal)
  }

  const toggleSavingsGoal = (goal) => {
    const isSelected = formData.savingsGoals.some((selectedGoal) => selectedGoal.id === goal.id)
    const goals = isSelected
      ? formData.savingsGoals.filter((selectedGoal) => selectedGoal.id !== goal.id)
      : [...formData.savingsGoals, { ...goal, priority: DEFAULT_GOAL_PRIORITY, amount: '' }]

    applySavingsGoals(goals)
  }

  const updateSavingsGoal = (goalId, field, value) => {
    const goals = formData.savingsGoals.map((goal) =>
      goal.id === goalId ? { ...goal, [field]: value } : goal
    )
    applySavingsGoals(goals)
  }

  const nextStep = async () => {
    setStepError(null)

    if (currentStep === 1) {
      try {
        await updateSalary(Number(formData.salary))
      } catch (err) {
        setStepError(err.message)
        return
      }
    }

    if (currentStep === 2) {
      try {
        const isYes = formData.hasExtraIncome === 'Bəli' || formData.hasExtraIncome === true
        await updateExtraIncome({
          hasExtraIncome: isYes,
          extraIncome: isYes ? formData.extraIncome : 0
        })
      } catch (err) {
        setStepError(err.message)
        return
      }
    }

    if (currentStep === 3) {
      try {
        await updateHousing({
          housingType: formData.housingType,
          housingAmount: formData.housingAmount
        })
      } catch (err) {
        setStepError(err.message)
        return
      }
    }

    if (currentStep === 4) {
      try {
        await updateHasCredit(formData.hasCredit)

        if (formData.hasCredit === 'Bəli') {
          await syncCredits(formData.credits)
        }
      } catch (err) {
        setStepError(err.message)
        return
      }
    }

    if (currentStep === 5) {
      try {
        await updateSavingsGoals(formData.savingsGoals)
      } catch (err) {
        setStepError(err.message)
        return
      }
    }

    if (currentStep === 6) {
      try {
        await updateMonthlyExpenses(formData.monthlyExpenses)
      } catch (err) {
        setStepError(err.message)
        return
      }
    }

    if (currentStep === 7) {
      try {
        await updateRecurringExpenses(formData.recurringExpenses)
      } catch (err) {
        setStepError(err.message)
        return
      }
    }

    if (currentStep === 8) {
      try {
        await updateFinancialAssessment(formData.financialAssessment)
      } catch (err) {
        setStepError(err.message)
        return
      }
    }

    if (currentStep === 9) {
      try {
        await updateMonthlySavingsAbility(formData.monthlySavingsAbility)
      } catch (err) {
        setStepError(err.message)
        return
      }
    }

    if (currentStep === 10) {
      try {
        await completeOnboarding(formData.annualBudgetPriority)
        finishOnboarding()
        return
      } catch (err) {
        setStepError(err.message)
        return
      }
    }

    if (currentStep < totalSteps) {
      setCurrentStep((prev) => prev + 1)
    }
  }

  const prevStep = () => {
    if (currentStep > 1) {
      setCurrentStep((prev) => prev - 1)
    }
  }

  const goToStep = (step) => {
    setCurrentStep(Math.min(totalSteps, Math.max(1, step)))
  }

  const isCreditRowValid = (c) =>
    c.monthly.trim() !== '' &&
    c.remaining.trim() !== '' &&
    c.rate.trim() !== '' &&
    c.months.trim() !== ''

  const isCurrentStepValid = () => {
    switch (currentStep) {
      case 1:
        return formData.salary !== '' && !isNaN(Number(formData.salary))
      case 2:
        if (!formData.hasExtraIncome) return false
        if (formData.hasExtraIncome === 'Bəli') {
          return formData.extraIncome !== '' && !isNaN(Number(formData.extraIncome))
        }
        return true
      case 3:
        if (!formData.housingType) return false
        if (formData.housingType !== 'Özümündür') {
          return formData.housingAmount !== '' && !isNaN(Number(formData.housingAmount))
        }
        return true
      case 4:
        if (!formData.hasCredit) return false
        if (formData.hasCredit === 'Bəli') {
          return formData.credits.length > 0 && formData.credits.every(isCreditRowValid)
        }
        return true
      case 5:
        return formData.savingsGoals.length > 0 && formData.savingsGoals.every((goal) =>
          goal.amount !== '' && !isNaN(Number(goal.amount)) &&
          (goal.id !== 'other' || (goal.customName && goal.customName.trim() !== ''))
        )
      case 6:
        return Object.values(formData.monthlyExpenses).some(
          (value) => value !== '' && value !== null
        )
      case 7:
        return formData.recurringExpenses.length > 0
      case 8:
        return formData.financialAssessment !== ''
      case 9:
        return formData.monthlySavingsAbility !== ''
      case 10:
        return formData.annualBudgetPriority !== ''
      default:
        return true
    }
  }

  return {
    currentStep,
    totalSteps,
    userName,
    formData,
    stepError,
    updateField,
    updateMonthlyExpense,
    clearMonthlyExpense,
    toggleRecurringExpense,
    clearField,
    addCredit,
    updateCredit,
    clearCredit,
    removeCredit,
    toggleSavingsGoal,
    updateSavingsGoal,
    nextStep,
    prevStep,
    goToStep,
    finishOnboarding,
    resetOnboarding,
    fullReset,
    isCurrentStepValid: isCurrentStepValid()
  }
}