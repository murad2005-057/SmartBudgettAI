const API_BASE_URL = 'http://127.0.0.1:8000/api'

function getAccessToken() {
  return localStorage.getItem('accessToken')
    || localStorage.getItem('token')
    || localStorage.getItem('access_token')
}

async function refreshAccessToken() {
  const refreshToken = localStorage.getItem('refreshToken')
    || localStorage.getItem('refresh_token')

  if (!refreshToken) return false

  try {
    const response = await fetch(`${API_BASE_URL}/token/refresh/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh: refreshToken })
    })

    if (!response.ok) return false

    const data = await response.json()
    localStorage.setItem('accessToken', data.access)
    return true
  } catch {
    return false
  }
}

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
    if (response.status >= 500) {
      throw new Error('Server xətası baş verdi. Zəhmət olmasa bir az sonra yenidən cəhd edin.')
    }
    const firstError = data.errors
      ? Object.values(data.errors)[0]?.[0]
      : null
    throw new Error(firstError || 'Qeydiyyat uğursuz oldu.')
  }

  return data
}

export async function updateSalary(salary) {
  return fetchWithAuth(`${API_BASE_URL}/financial-inquiry/salary/`, {
    method: 'PATCH',
    body: JSON.stringify({ salary })
  })
}


export async function updateExtraIncome({ hasExtraIncome, extraIncome }) {
  return fetchWithAuth(`${API_BASE_URL}/financial-inquiry/extra-income/`, {
    method: 'PATCH',
    body: JSON.stringify({
      hasExtraIncome,
      extraIncome: extraIncome === '' ? null : Number(extraIncome)
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
    body: JSON.stringify({ hasCredit })
  })
}

async function fetchWithAuth(url, options = {}, canRefresh = true) {
  let response
  try {
    response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': (() => {
          const token = localStorage.getItem('accessToken') || localStorage.getItem('token')
          return token ? `Bearer ${token}` : ''
        })(),
        ...(options.headers || {})
      }
    })
  } catch (networkErr) {
    throw new Error('Serverlə əlaqə qurula bilmədi. Zəhmət olmasa bir az sonra yenidən cəhd edin.')
  }

  if (response.status === 401 && canRefresh && await refreshAccessToken()) {
    return fetchWithAuth(url, options, false)
  }

  let data = null
  try {
    data = await response.json()
  } catch {
    // some responses (e.g. DELETE) may have no body — that's fine
  }

  if (!response.ok) {
    if (response.status >= 500) {
      throw new Error('Server xətası baş verdi. Zəhmət olmasa bir az sonra yenidən cəhd edin.')
    }
    const firstError = data?.errors ? Object.values(data.errors)[0]?.[0] : null
    throw new Error(firstError || 'Məlumat saxlanılmadı.')
  }

  return data
}

export async function syncCredits(credits) {
  // Replace all existing credits with the current list from the form.
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
      goals: goals.map((g) => ({
        id: g.id,
        customName: g.customName || '',
        priority: g.priority,
        amount: Number(g.amount)
      }))
    })
  })
}



export async function updateMonthlyExpenses(monthlyExpenses) {
  const payload = {}
  for (const key of ['market', 'utilities', 'transport', 'restaurant', 'clothing', 'entertainment', 'onlineShopping', 'other']) {
    const val = monthlyExpenses[key]
    payload[key] = val === '' || val === null || val === undefined ? 0 : Number(val)
  }

  return fetchWithAuth(`${API_BASE_URL}/financial-inquiry/monthly-expenses/`, {
    method: 'PATCH',
    body: JSON.stringify(payload)
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
    body: JSON.stringify({ financialAssessment })
  })
}