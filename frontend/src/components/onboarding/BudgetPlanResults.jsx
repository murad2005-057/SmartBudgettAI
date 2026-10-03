import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'
import {
  Download,
  ChevronRight,
  ChevronUp,
  FilePenLine,
  LineChart,
  Plus,
  PiggyBank,
  Printer,
  RefreshCw,
  TrendingUp
} from 'lucide-react'
import * as XLSX from 'xlsx'
import { ONBOARDING_ACTIVE_KEY, ONBOARDING_STORAGE_KEY, ACCOUNT_STORAGE_KEY, BUDGET_MONTHS_STORAGE_KEY } from '../../hooks/useOnboardingForm'
import { Header } from './Header'
import { LoadingPlan } from './LoadingPlan'
import { GoalCard } from './GoalCard'
import { API_BASE_URL as API_BASE } from '../../config'

const MONTHS = ['Yan', 'Fev', 'Mar', 'Apr', 'May', 'İyn', 'İyl', 'Avq', 'Sen', 'Okt', 'Noy', 'Dek']

const TABLE_COLUMNS = [
  { key: 'income', label: 'Gəlir' },
  { key: 'restaurant', label: 'Restoran' },
  { key: 'entertainment', label: 'Əyləncə' },
  { key: 'market', label: 'Qida' },
  { key: 'utilities', label: 'Kommunal' },
  { key: 'transport', label: 'Nəqliyyat' },
  { key: 'clothing', label: 'Geyim' },
  { key: 'online_shopping', label: 'Onlayn alış-veriş' },
  { key: 'credit', label: 'Kredit' },
  { key: 'other', label: 'Digər' },
  { key: 'savings', label: 'Yığım' },
  { key: 'balance', label: 'Qalıq', editable: false }
]

const STATUS_TONE = {
  'Prioritet ödəniş': 'priority',
  'Diqqət': 'attention',
  'Uyğundur': 'good',
  'Yüksək xərc': 'high',
  'Qənaətlidir': 'savings'
}

const CATEGORY_LABELS = {
  market: 'Qida və market',
  restaurant: 'Restoran və kafe',
  utilities: 'Kommunal ödənişlər',
  transport: 'Nəqliyyat',
  clothing: 'Geyim',
  entertainment: 'Əyləncə',
  online_shopping: 'Onlayn alış-veriş',
  other: 'Digər xərclər',
  credit: 'Kredit və borclar'
}

const CATEGORY_ALIASES = {
  market: ['market', 'food', 'qida', 'qida və market'],
  restaurant: ['restaurant', 'restoran', 'restoran və kafe'],
  transport: ['transport', 'nəqliyyat'],
  utilities: ['utilities', 'kommunal', 'kommunal ödənişlər'],
  clothing: ['clothing', 'geyim'],
  entertainment: ['entertainment', 'əyləncə'],
  online_shopping: ['online_shopping', 'onlayn alış-veriş'],
  other: ['other', 'digər', 'digər xərclər'],
  credit: ['credit', 'kredit', 'kredit və borclar']
}

const MODIFIED_FIELDS_STORAGE_KEY = 'budgetModifiedFields'

const readModifiedFields = () => {
  try {
    const stored = window.localStorage.getItem(MODIFIED_FIELDS_STORAGE_KEY)
    const parsed = stored ? JSON.parse(stored) : {}
    return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : {}
  } catch {
    return {}
  }
}

const numberValue = (value) => Number(value) || 0
const money = (value) => `${numberValue(value).toLocaleString('az-AZ')} AZN`
const categoryField = (categoryName) => {
  const normalized = String(categoryName || '').trim().toLowerCase()
  return Object.entries(CATEGORY_ALIASES).find(([, aliases]) => aliases.includes(normalized))?.[0] || null
}

const averageMonthlyValue = (monthlyTable, key) => (
  monthlyTable.length
    ? monthlyTable.reduce((total, month) => total + numberValue(month[key]), 0) / monthlyTable.length
    : 0
)

const calculateComparisonMetrics = (row, monthlyIncome) => {
  const categoryName = String(row.category_name || '').trim().toLowerCase()
  const recommended = numberValue(row.recommended_monthly_amount)
  const current = numberValue(row.current_monthly_amount)
  const isPriority = ['credit', 'kredit', 'kredit və borclar', 'utilities', 'kommunal', 'kommunal ödənişlər'].includes(categoryName)

  let status
  let aiRecommendation
  if (isPriority) {
    status = 'Prioritet ödəniş'
    aiRecommendation = 'Ödənişini vaxtında et.'
  } else if (recommended === 0) {
    status = 'Qənaətlidir'
    aiRecommendation = 'Bu sahədə qənaət edirsən.'
  } else if (recommended > current) {
    status = 'Yüksək xərc'
    aiRecommendation = 'Xərc tövsiyə olunan səviyyədən yüksəkdir.'
  } else {
    status = 'Uyğundur'
    aiRecommendation = 'Xərcin tövsiyə olunan səviyyədədir.'
  }

  return {
    ...row,
    percentage: monthlyIncome > 0 ? Math.round((recommended / monthlyIncome) * 10000) / 100 : 0,
    annual_amount: Math.round(recommended * 1200) / 100,
    status,
    ai_recommendation: aiRecommendation
  }
}

const authHeaders = () => {
  const token = localStorage.getItem('access_token') || localStorage.getItem('token')
  return { Authorization: `Bearer ${token}` }
}

const calculateBalance = (month) => month.income - (
  month.restaurant + month.entertainment + month.market + month.utilities +
  month.transport + month.clothing + month.online_shopping + month.credit + month.other + month.savings
)

export function BudgetPlanResults() {
  const navigate = useNavigate()

  const [loading, setLoading] = useState(true)
  const [loadingPhase, setLoadingPhase] = useState(1)
  const [error, setError] = useState(null)

  const [summary, setSummary] = useState(null)
  const [goals, setGoals] = useState([])
  const [months, setMonths] = useState([])
  const [comparison, setComparison] = useState([])

  const [showAllGoals, setShowAllGoals] = useState(false)
  const [showNewPlanModal, setShowNewPlanModal] = useState(false)

  const [modifiedFields, setModifiedFields] = useState(readModifiedFields)
  const [refreshing, setRefreshing] = useState(false)

  const persistModifiedFields = (next) => {
    setModifiedFields(next)
    try {
      window.localStorage.setItem(MODIFIED_FIELDS_STORAGE_KEY, JSON.stringify(next))
    } catch {
      // Keep the in-memory edit even when storage is unavailable.
    }
  }

  const mergeModifiedFields = useCallback((monthlyTable, budgetComparison, monthlyIncome) => {
    const fields = readModifiedFields()
    const mergedMonths = monthlyTable.map((month, monthIndex) => {
      const updatedMonth = { ...month }
      Object.values(fields).forEach((field) => {
        if (field.month_index === monthIndex && typeof field.category_name === 'string' && field.category_name in updatedMonth) {
          updatedMonth[field.category_name] = field.new_value
        }
      })
      return updatedMonth
    })
    const mergedComparison = budgetComparison.map((row) => {
      const key = categoryField(row.category_name)
      const amount = key ? averageMonthlyValue(mergedMonths, key) : numberValue(row.recommended_monthly_amount)
      return calculateComparisonMetrics({ ...row, recommended_monthly_amount: amount }, monthlyIncome)
    })
    const normalizedFields = Object.fromEntries(
      Object.entries(fields).filter(([, field]) => Number.isInteger(field.month_index))
    )
    mergedComparison.forEach((row) => {
      normalizedFields[`comparison:${row.category_name}`] = {
        category_name: row.category_name,
        new_value: row.recommended_monthly_amount
      }
    })
    setModifiedFields(normalizedFields)
    try {
      window.localStorage.setItem(MODIFIED_FIELDS_STORAGE_KEY, JSON.stringify(normalizedFields))
    } catch {
      // Keep the in-memory merge when storage is unavailable.
    }
    return { mergedMonths, mergedComparison }
  }, [])

  const loadPlanData = useCallback(async (headers) => {
    const [summaryRes, goalsRes, tableRes, comparisonRes] = await Promise.all([
      axios.get(`${API_BASE}/summary/`, { headers, timeout: 15000 }),
      axios.get(`${API_BASE}/summary/goals/`, { headers, timeout: 15000 }),
      axios.get(`${API_BASE}/summary/table/`, { headers, timeout: 15000 }),
      axios.get(`${API_BASE}/summary/comparison/`, { headers, timeout: 15000 })
    ])

    if (summaryRes.data.status !== 'success' || tableRes.data.status !== 'success') {
      throw new Error('Plan məlumatları hələ hazır deyil.')
    }

    const monthlyTable = tableRes.data.monthly_table || []
    const monthlyIncome = numberValue(summaryRes.data.data?.reliable_monthly_income) || (
      monthlyTable.length
        ? monthlyTable.reduce((total, month) => total + numberValue(month.income), 0) / monthlyTable.length
        : 0
    )
    const { mergedMonths, mergedComparison } = mergeModifiedFields(
      monthlyTable,
      comparisonRes.data.budget_comparison || [],
      monthlyIncome
    )
    setSummary(summaryRes.data.data)
    setGoals(goalsRes.data.data || [])
    setMonths(mergedMonths)
    setComparison(mergedComparison)
  }, [mergeModifiedFields])

  const userName = (() => {
    try {
      const stored = window.localStorage.getItem(ACCOUNT_STORAGE_KEY)
      const parsed = stored ? JSON.parse(stored) : null
      return parsed?.formData?.fullName?.trim().split(' ')[0] || 'İstifadəçi'
    } catch {
      return 'İstifadəçi'
    }
  })()

  // Polling effect: checks plan status, fetches summary/goals/table/comparison once
  // completed. Caps retries on repeated errors so a down backend doesn't loop forever.
  useEffect(() => {
    let timeoutId = null
    let isMounted = true
    let errorCount = 0
    const MAX_ERRORS = 5

    const pollPlanStatus = async () => {
      try {
        const headers = authHeaders()
        const response = await axios.get(`${API_BASE}/financial-inquiry/status/`, { headers, timeout: 5000 })

        if (!isMounted) return
        errorCount = 0

        const status = response.data.status

        if (status === 'completed' || status === 'complete') {
          await loadPlanData(headers)
          if (!isMounted) return
          setLoading(false)
          return
        }

        if (status === 'failed') {
          setError('Plan hazırlanarkən xəta baş verdi.')
          setLoading(false)
          return
        }

        // Still processing — poll again shortly
        timeoutId = setTimeout(pollPlanStatus, 2000)

      } catch (err) {
        console.error('Məlumatı yükləmək mümkün olmadı:', err)
        errorCount += 1
        if (!isMounted) return

        if (errorCount >= MAX_ERRORS) {
          setError('Serverlə əlaqə qurula bilmədi. İnternet bağlantınızı yoxlayın.')
          setLoading(false)
          return
        }
        timeoutId = setTimeout(pollPlanStatus, 3000)
      }
    }

    pollPlanStatus()

    return () => {
      isMounted = false
      if (timeoutId) clearTimeout(timeoutId)
    }
  }, [loadPlanData])

  const updateCell = (monthIndex, key, value) => {
    const newValue = value === '' ? 0 : numberValue(value)
    const updatedMonths = months.map((month, index) => (
      index === monthIndex ? { ...month, [key]: value === '' ? 0 : numberValue(value) } : month
    ))
    const nextModifiedFields = {
      ...modifiedFields,
      [`month:${monthIndex}:${key}`]: { category_name: key, month_index: monthIndex, new_value: newValue }
    }
    const updatedComparison = comparison.map((row) => {
      const category = categoryField(row.category_name)
      if (!category) return row
      const amount = averageMonthlyValue(updatedMonths, category)
      nextModifiedFields[`comparison:${row.category_name}`] = { category_name: row.category_name, new_value: amount }
      return calculateComparisonMetrics({ ...row, recommended_monthly_amount: amount }, monthlyIncome)
    })
    persistModifiedFields(nextModifiedFields)
    setMonths(updatedMonths)
    setComparison(updatedComparison)
  }

  const updateComparisonCell = (index, value) => {
    const row = comparison[index]
    const key = categoryField(row?.category_name)
    if (!key) return

    const newValue = value === '' ? 0 : numberValue(value)
    const updatedMonths = months.map((month) => ({ ...month, [key]: newValue }))
    const nextModifiedFields = { ...modifiedFields }
    updatedMonths.forEach((month, monthIndex) => {
      nextModifiedFields[`month:${monthIndex}:${key}`] = {
        category_name: key,
        month_index: monthIndex,
        new_value: newValue
      }
    })
    nextModifiedFields[`comparison:${row.category_name}`] = {
      category_name: row.category_name,
      new_value: newValue
    }
    persistModifiedFields(nextModifiedFields)
    setMonths(updatedMonths)
    setComparison((current) => current.map((item, itemIndex) => (
      itemIndex === index
        ? calculateComparisonMetrics({ ...item, recommended_monthly_amount: newValue }, monthlyIncome)
        : item
    )))
  }

  const liveTotals = TABLE_COLUMNS.reduce((result, column) => ({
    ...result,
    [column.key]: months.reduce((total, month) => total + (column.key === 'balance' ? calculateBalance(month) : numberValue(month[column.key])), 0)
  }), {})

  const monthlyIncome = numberValue(summary?.reliable_monthly_income) || (
    months.length ? months.reduce((total, month) => total + numberValue(month.income), 0) / months.length : 0
  )

  const monthlySavingsDisplay = summary ? summary.recommended_monthly_savings : (liveTotals.savings || 0) / 12
  const annualSavingsDisplay = summary ? summary.recommended_annual_savings : liveTotals.savings

  const jumpToStep = (step) => {
    try {
      const saved = window.localStorage.getItem(ONBOARDING_STORAGE_KEY)
      const parsed = saved ? JSON.parse(saved) : { formData: {} }
      window.localStorage.setItem(
        ONBOARDING_STORAGE_KEY,
        JSON.stringify({ ...parsed, currentStep: step })
      )
    } catch {
      window.localStorage.removeItem(ONBOARDING_STORAGE_KEY)
    }
    window.localStorage.setItem(ONBOARDING_ACTIVE_KEY, 'true')
    navigate('/')
  }

  const handleEdit = () => jumpToStep(1)

  const handleRefreshTable = async () => {
    setError(null)
    setRefreshing(true)
    try {
      const headers = authHeaders()
      const payload = { modifiedFields, monthly_table: months }
      await axios.put(`${API_BASE}/summary/recalculate/`, payload, { headers, timeout: 60000 })
      await loadPlanData(headers)
    } catch (err) {
      setError(err.response?.data?.message || err.response?.data?.error || 'Cədvəli yeniləmək mümkün olmadı.')
    } finally {
      setRefreshing(false)
    }
  }

  const handleRetry = async () => {
    setError(null)
    setLoading(true)
    setLoadingPhase(1)
    const phaseTimer = window.setTimeout(() => setLoadingPhase(2), 1500)
    try {
      const headers = authHeaders()
      await axios.post(`${API_BASE}/financial-inquiry/retry/`, {}, { headers, timeout: 60000 })
      await loadPlanData(headers)
    } catch (err) {
      setError(err.response?.data?.message || err.response?.data?.error || 'Planı yenidən yükləmək mümkün olmadı.')
    } finally {
      window.clearTimeout(phaseTimer)
      setLoading(false)
    }
  }

  const handleNewPlan = () => {
    setShowNewPlanModal(false)
    ;['access_token', 'accessToken', 'token', 'refresh_token', 'refreshToken'].forEach((key) => {
      window.localStorage.removeItem(key)
    })
    window.localStorage.removeItem(ONBOARDING_STORAGE_KEY)
    window.localStorage.removeItem(ONBOARDING_ACTIVE_KEY)
    window.localStorage.removeItem(ACCOUNT_STORAGE_KEY)
    window.localStorage.removeItem(BUDGET_MONTHS_STORAGE_KEY)
    window.localStorage.removeItem(MODIFIED_FIELDS_STORAGE_KEY)
    navigate('/login', { replace: true })
  }

  const exportExcel = () => {
    const header = ['Ay', ...TABLE_COLUMNS.map((column) => column.label)]
    const rows = months.map((month, index) => [
      MONTHS[index],
      ...TABLE_COLUMNS.map((column) => column.key === 'balance' ? calculateBalance(month) : numberValue(month[column.key]))
    ])
    const worksheet = XLSX.utils.aoa_to_sheet([
      header,
      ...rows,
      ['İllik cəmi', ...TABLE_COLUMNS.map((column) => liveTotals[column.key])]
    ])
    worksheet['!cols'] = [{ wch: 14 }, ...TABLE_COLUMNS.map(() => ({ wch: 14 }))]
    const workbook = XLSX.utils.book_new()
    XLSX.utils.book_append_sheet(workbook, worksheet, '12 aylıq plan')
    XLSX.writeFile(workbook, 'smartbudget-plan.xlsx')
  }

  const visibleGoals = showAllGoals ? goals : goals.slice(0, 3)

  if (loading) {
      return (
        <div className="results-page-wrapper">
          <Header />
          <main className="results-main-container results-loading-container">
            <LoadingPlan phase={loadingPhase} />
          </main>
        </div>
      )
    }

  if (error) {
    return (
      <div className="results-page-wrapper">
        <Header />
        <main className="results-main-container results-error-container">
          <p role="alert">{error}</p>
          <button type="button" className="btn-restart" onClick={handleRetry}>Yenidən cəhd et</button>
        </main>
      </div>
    )
  }

  return (
    <div className="results-page-wrapper">
      <Header />
      <main className="results-main-container">
      <div className="budget-results" id="budget-plan-results">
      <div className="results-heading">
        <div>
          <h1>{userName}, illik büdcə planınız hazırdır</h1>
          <p>Cavablarınıza əsaslanan fərdiləşdirilmiş illik plan</p>
        </div>
        <button type="button" className="results-action results-action-primary" onClick={() => window.print()}>
          <Printer size={15} /> Çap/PDF
        </button>
      </div>

      <section className="results-summary-grid" aria-label="Büdcə xülasəsi">
        <div className="results-summary-card">
          <div className="results-summary-copy">
            <span>Tövsiyə olunan aylıq yığım</span>
            <strong>{money(monthlySavingsDisplay)}</strong>
          </div>
          <span className="results-summary-icon"><PiggyBank size={20} strokeWidth={2} /></span>
        </div>
        <div className="results-summary-card">
          <div className="results-summary-copy">
            <span>Tövsiyə olunan illik yığım</span>
            <strong>{money(annualSavingsDisplay)}</strong>
          </div>
          <span className="results-summary-icon"><TrendingUp size={20} strokeWidth={2} /></span>
        </div>
        <div className="results-summary-card results-summary-card-accent">
          <div className="results-summary-copy">
            <span>Maliyyə vəziyyəti</span>
            <strong>{summary?.financial_status || 'Naməlum'}</strong>
          </div>
          <span className="results-summary-icon"><LineChart size={20} strokeWidth={2} /></span>
        </div>
      </section>

      <section className="goals-section">
        <div className="results-section-heading">
          <h2>Yığım məqsədləri</h2>
          {goals.length > 3 && (
            <button type="button" className="results-link-button" onClick={() => setShowAllGoals((current) => !current)}>
              <span>{showAllGoals ? 'Gizlət' : 'Hamısına bax'}</span>
              {showAllGoals ? <ChevronUp className="results-link-icon" /> : <ChevronRight className="results-link-icon" />}
            </button>
          )}
        </div>
        {goals.length > 0 ? (
          <div className="results-goals-grid">
            {visibleGoals.map((goal, idx) => (
              <GoalCard key={idx} goal={goal} />
            ))}
          </div>
        ) : <div className="results-empty-state">Hələ yığım məqsədi seçilməyib.</div>}
      </section>

      <section className="annual-plan-section results-panel">
        <div className="results-section-heading plan-heading">
          <div><h2>AI tərəfindən hazırlanmış 12 aylıq plan</h2><p>Hər ay üçün xərcləri ayrıca bölür və yığım və qalıq məbləğini hesablayır.</p></div>
          <div className="results-actions">
            <button type="button" className="results-action" onClick={handleEdit}><FilePenLine size={14} /> Cavabı dəyiş</button>
            <button type="button" className="results-action" onClick={handleRefreshTable} disabled={refreshing}>
              <RefreshCw size={14} className={refreshing ? 'spin-icon' : ''} /> {refreshing ? 'Yenilənir...' : 'Cədvəli yenilə'}
            </button>
            <button type="button" className="results-action" onClick={() => setShowNewPlanModal(true)}><Plus size={14} /> Yeni plan əlavə et</button>
          </div>
        </div>
        <div className="results-table-scroll">
          <table className="annual-plan-table">
            <thead>
              <tr>
                <th>Ay</th>
                {TABLE_COLUMNS.map((column) => (
                  <th key={column.key}>
                    {column.label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>{months.map((month, monthIndex) => <tr key={MONTHS[monthIndex] || monthIndex}>
              <th><span className="month-pill">{month.month_name || MONTHS[monthIndex]}</span></th>
              {TABLE_COLUMNS.map((column) => {
                return (
                  <td key={column.key}>
                    {column.editable === false
                      ? <strong className={calculateBalance(month) < 0 ? 'negative-value' : ''}>{money(calculateBalance(month))}</strong>
                      : <input
                          aria-label={`${month.month_name} ${column.label}`}
                          type="number"
                          min="0"
                          value={month[column.key] ?? ''}
                          placeholder="0"
                          onChange={(event) => updateCell(monthIndex, column.key, event.target.value)}
                        />}
                  </td>
                )
              })}
            </tr>)}</tbody>
            <tfoot><tr><th>İllik cəmi</th>{TABLE_COLUMNS.map((column) => <th key={column.key} className={column.key === 'balance' && liveTotals.balance < 0 ? 'negative-value' : ''}>{money(liveTotals[column.key])}</th>)}</tr></tfoot>
          </table>
        </div>
        <div className="results-panel-footer"><button type="button" className="results-action results-action-primary" onClick={exportExcel}><Download size={14} /> Excel yüklə</button></div>
      </section>

      <section className="distribution-section results-panel">
        <div className="results-section-heading"><div><h2>Tövsiyə olunan büdcə bölgüsü</h2><p>Tövsiyə olunan aylıq mabləğləri dəyişə bilərsiniz. Yığım və qalıq avtomatik yenidən hesablanacaq.</p></div></div>
        <div className="results-table-scroll">
          <table className="distribution-table">
            <thead><tr><th>Kateqoriya</th><th>%</th><th>Hazırkı aylıq</th><th>Tövsiyə olunan aylıq</th><th>İllik</th><th>Status</th><th>AI tövsiyəsi</th></tr></thead>
            <tbody>{comparison.map((row, idx) => {
              return (
                <tr key={idx}>
                  <th>
                    <span>{CATEGORY_LABELS[row.category_name] || row.category_name}</span>
                  </th>
                  <td>{row.percentage}%</td>
                  <td>{money(row.current_monthly_amount)}</td>
                  <td>
                    <input
                      type="number"
                      min="0"
                      className="distribution-input"
                      aria-label={`${CATEGORY_LABELS[row.category_name] || row.category_name} tövsiyə olunan aylıq`}
                      value={row.recommended_monthly_amount ?? ''}
                      onChange={(event) => updateComparisonCell(idx, event.target.value)}
                    />
                  </td>
                  <td>{money(row.annual_amount)}</td>
                  <td><span className={`budget-tag ${STATUS_TONE[row.status] || 'good'}`}>{row.status}</span></td>
                  <td>{row.ai_recommendation}</td>
                </tr>
              )
            })}</tbody>
          </table>
        </div>

        {/* Refresh Table Action Bar below the Budget Component */}
        <div className="refresh-table-bottom-bar">
          <button
            type="button"
            className="btn-refresh-table"
            onClick={handleRefreshTable}
            disabled={refreshing}
          >
            <RefreshCw size={15} className={refreshing ? 'spin-icon' : ''} />
            <span>{refreshing ? 'Cədvəl yenilənir...' : 'Cədvəli yenilə'}</span>
          </button>
        </div>
      </section>

      {showNewPlanModal && (
        <div className="results-modal-backdrop" role="presentation" onClick={() => setShowNewPlanModal(false)}>
          <div className="results-modal" role="dialog" aria-modal="true" aria-labelledby="new-plan-title" onClick={(event) => event.stopPropagation()}>
            <h2 id="new-plan-title">Yeni plan yaradılsın?</h2>
            <p>Hazırkı plan hesabınızda saxlanılacaq. Başqa hesabla daxil olaraq yeni plan yarada bilərsiniz.</p>
            <div className="results-modal-actions">
              <button type="button" className="results-action" onClick={() => setShowNewPlanModal(false)}>Ləğv et</button>
              <button type="button" className="results-action results-action-primary" onClick={handleNewPlan}>Yeni plana başla</button>
            </div>
          </div>
        </div>
      )}
      </div>
      </main>
    </div>
  )
}

export default BudgetPlanResults