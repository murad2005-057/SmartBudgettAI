const API_BASE_URL = 'http://127.0.0.1:8000/api'

// --- HELPER FUNCTIONS ---

function getAccessToken() {
  return localStorage.getItem('accessToken') || localStorage.getItem('token')
}

function getRefreshToken() {
  return localStorage.getItem('refreshToken') || localStorage.getItem('refresh_token')
}

function setTokens(access, refresh) {
  if (access) {
    localStorage.setItem('accessToken', access)
    localStorage.setItem('token', access)
  }
  if (refresh) {
    localStorage.setItem('refreshToken', refresh)
    localStorage.setItem('refresh_token', refresh)
  }
}

function clearTokens() {
  localStorage.removeItem('accessToken')
  localStorage.removeItem('token')
  localStorage.removeItem('refreshToken')
  localStorage.removeItem('refresh_token')
}

async function refreshAccessToken() {
  const refreshToken = getRefreshToken()
  if (!refreshToken) return false

  try {
    const response = await fetch(`${API_BASE_URL}/token/refresh/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh: refreshToken })
    })

    if (!response.ok) {
      clearTokens()
      return false
    }

    const data = await response.json()
    setTokens(data.access, data.refresh)
    return data.access
  } catch {
    clearTokens()
    return false
  }
}

export async function fetchWithAuth(url, options = {}) {
  let token = getAccessToken()

  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  }

  let response = await fetch(url, { ...options, headers })

  // Əgər Token expired olubsa (401 Unauthorized)
  if (response.status === 401) {
    const newAccessToken = await refreshAccessToken()

    if (newAccessToken) {
      headers['Authorization'] = `Bearer ${newAccessToken}`
      response = await fetch(url, { ...options, headers })
    } else {
      window.location.href = '/login'
      return
    }
  }

  return response.json()
}

// --- API EXPORTS ---

export async function registerUser({ fullName, email, password }) {
  let response
  try {
    response = await fetch(`${API_BASE_URL}/register/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ fullName, email, password })
    })
  } catch (networkErr) {
    throw new Error('Serverlə əlaqə qurula bilmədi. Zəhmət olmasa bir az sonra yenidən cəhd edin.')
  }

  let data
  try {
    data = await response.json()
  } catch (parseErr) {
    throw new Error('Server xətası baş verdi. Zəhmət olmasa bir az sonra yenidən cəhd edin.')
  }

  if (!response.ok) {
    const firstError = data.errors ? Object.values(data.errors)[0]?.[0] : null
    throw new Error(firstError || 'Qeydiyyat uğursuz oldu.')
  }

  if (data.tokens?.access) {
    setTokens(data.tokens.access, data.tokens.refresh)
  }

  return data
}

export async function updateSalary(salary) {
  return fetchWithAuth(`${API_BASE_URL}/financial-inquiry/salary/`, {
    method: 'PATCH',
    body: JSON.stringify({ salary: Number(salary) })
  })
}

export async function updateExtraIncome({ hasExtraIncome, extraIncome }) {
  const isYes = hasExtraIncome === 'Bəli' || hasExtraIncome === true

  return fetchWithAuth(`${API_BASE_URL}/financial-inquiry/extra-income/`, {
    method: 'PATCH',
    body: JSON.stringify({
      hasExtraIncome: isYes ? 'Bəli' : 'Xeyr',
      has_extra_income: isYes ? 'Bəli' : 'Xeyr',
      extraIncome: isYes ? Number(extraIncome || 0) : 0,
      extra_income: isYes ? Number(extraIncome || 0) : 0
    })
  })
}

export async function updateHousing({ housingType, housingAmount }) {
  return fetchWithAuth(`${API_BASE_URL}/financial-inquiry/housing/`, {
    method: 'PATCH',
    body: JSON.stringify({
      housingType,
      housingAmount: housingAmount === '' ? null : Number(housingAmount)
    })
  })
}

export async function updateHasCredit(hasCredit) {
  return fetchWithAuth(`${API_BASE_URL}/financial-inquiry/has-credit/`, {
    method: 'PATCH',
    body: JSON.stringify({ hasCredit: hasCredit ? 'Bəli' : 'Xeyr' })
  })
}

export async function syncCredits(credits) {
  const existing = await fetchWithAuth(`${API_BASE_URL}/financial-inquiry/credits/`)
  const existingCredits = existing?.credits || []

  for (const c of existingCredits) {
    await fetchWithAuth(`${API_BASE_URL}/financial-inquiry/credits/${c.id}/`, { method: 'DELETE' })
  }

  for (const c of credits) {
    if (c.monthly === '' || c.remaining === '' || c.rate === '' || c.months === '') continue
    await fetchWithAuth(`${API_BASE_URL}/financial-inquiry/credits/`, {
      method: 'POST',
      body: JSON.stringify({
        monthly: Number(c.monthly),
        remaining: Number(c.remaining),
        rate: Number(c.rate),
        months: Number(c.months)
      })
    })
  }
}

export async function updateSavingsGoals(goals) {
  return fetchWithAuth(`${API_BASE_URL}/financial-inquiry/savings-goals/`, {
    method: 'PATCH',
    body: JSON.stringify({
      goals: goals.map((g) => {
        const goalId = String(g.id || g.goal_id || g.customName || 'goal')

        return {
          id: goalId,
          goal_id: goalId,
          title: g.title || g.label || g.name || g.customName || goalId,
          customName: g.customName || '',
          custom_name: g.customName || '',
          priority: g.priority || 'Orta prioritet',
          amount: Number(g.amount || 0)
        }
      })
    })
  })
}

export async function updateMonthlyExpenses(monthlyExpenses) {
  return fetchWithAuth(`${API_BASE_URL}/financial-inquiry/monthly-expenses/`, {
    method: 'PATCH',
    body: JSON.stringify({
      market: Number(monthlyExpenses.market || 0),
      utilities: Number(monthlyExpenses.utilities || 0),
      transport: Number(monthlyExpenses.transport || 0),
      restaurant: Number(monthlyExpenses.restaurant || 0),
      clothing: Number(monthlyExpenses.clothing || 0),
      entertainment: Number(monthlyExpenses.entertainment || 0),
      onlineShopping: Number(monthlyExpenses.onlineShopping || 0),
      other: Number(monthlyExpenses.other || 0)
    })
  })
}

export async function updateRecurringExpenses(recurringExpenses) {
  return fetchWithAuth(`${API_BASE_URL}/financial-inquiry/recurring-expenses/`, {
    method: 'PATCH',
    body: JSON.stringify({ recurringExpenses })
  })
}

export async function updateFinancialAssessment(financialAssessment) {
  return fetchWithAuth(`${API_BASE_URL}/financial-inquiry/financial-assessment/`, {
    method: 'PATCH',
    body: JSON.stringify({ 
      financialAssessment,
      financial_assessment: financialAssessment 
    })
  })
}

export async function updateMonthlySavingsAbility(monthlySavingsAbility) {
  return fetchWithAuth(`${API_BASE_URL}/financial-inquiry/monthly-savings-ability/`, {
    method: 'PATCH',
    body: JSON.stringify({ monthly_savings_ability: monthlySavingsAbility })
  })
}

export async function completeOnboarding(annualBudgetPriority) {
  return fetchWithAuth(`${API_BASE_URL}/financial-inquiry/complete/`, {
    method: 'POST',
    body: JSON.stringify({ annualBudgetPriority })
  })
}



export async function checkInquiryStatus() {
  return fetchWithAuth(`${API_BASE_URL}/financial-inquiry/status/`)
}