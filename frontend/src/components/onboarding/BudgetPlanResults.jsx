import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'
import {
  Download,
  Car,
  ChevronRight,
  ChevronUp,
  FilePenLine,
  GraduationCap,
  Home,
  LineChart,
  Plus,
  PiggyBank,
  Plane,
  Printer,
  RefreshCw,
  ShieldAlert,
  Target,
  TrendingUp
} from 'lucide-react'
import * as XLSX from 'xlsx'
import { ONBOARDING_ACTIVE_KEY, ONBOARDING_STORAGE_KEY, ACCOUNT_STORAGE_KEY, BUDGET_MONTHS_STORAGE_KEY } from '../../hooks/useOnboardingForm'
import { Header } from './Header'
import { LoadingPlan } from './LoadingPlan'

const API_BASE = 'http://127.0.0.1:8000/api'

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

const numberValue = (value) => Number(value) || 0
const money = (value) => `${numberValue(value).toLocaleString('az-AZ')} AZN`

const authHeaders = () => {
  const token = localStorage.getItem('access_token') || localStorage.getItem('token')
  return { Authorization: `Bearer ${token}` }
}

const calculateBalance = (month) => month.income - (
  month.restaurant + month.entertainment + month.market + month.utilities +
  month.transport + month.clothing + month.online_shopping + month.credit + month.other + month.savings
)

const getGoalIcon = (goal) => {
  const title = (goal.goal_name || '').toLowerCase()
  if (title.includes('home') || title.includes('ev') || title.includes('mənzil')) return Home
  if (title.includes('car') || title.includes('avtomobil')) return Car
  if (title.includes('travel') || title.includes('səyahət') || title.includes('tətil')) return Plane
  if (title.includes('education') || title.includes('təhsil')) return GraduationCap
  if (title.includes('emergency') || title.includes('təcili')) return ShieldAlert
  if (title.includes('business') || title.includes('biznes')) return Target
  if (title.includes('wedding') || title.includes('toy')) return Target
  return Target
}
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

  const loadPlanData = async (headers) => {
    const [summaryRes, goalsRes, tableRes, comparisonRes] = await Promise.all([
      axios.get(`${API_BASE}/summary/`, { headers, timeout: 15000 }),
      axios.get(`${API_BASE}/summary/goals/`, { headers, timeout: 15000 }),
      axios.get(`${API_BASE}/summary/table/`, { headers, timeout: 15000 }),
      axios.get(`${API_BASE}/summary/comparison/`, { headers, timeout: 15000 })
    ])

    if (summaryRes.data.status !== 'success' || tableRes.data.status !== 'success') {
      throw new Error('Plan məlumatları hələ hazır deyil.')
    }

    setSummary(summaryRes.data.data)
    setGoals(goalsRes.data.data || [])
    setMonths(tableRes.data.monthly_table || [])
    setComparison(comparisonRes.data.budget_comparison || [])
  }

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
  }, [])

  const updateCell = (monthIndex, key, value) => {
    setMonths((current) => current.map((month, index) => (
      index === monthIndex ? { ...month, [key]: value === '' ? 0 : numberValue(value) } : month
    )))
  }

  const updateComparisonCell = (index, value) => {
    setComparison((current) => current.map((row, i) => (
      i === index ? { ...row, recommended_monthly_amount: value === '' ? 0 : numberValue(value) } : row
    )))
  }

  const liveTotals = TABLE_COLUMNS.reduce((result, column) => ({
    ...result,
    [column.key]: months.reduce((total, month) => total + (column.key === 'balance' ? calculateBalance(month) : numberValue(month[column.key])), 0)
  }), {})

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
    setLoading(true)
    setLoadingPhase(1)
    const phaseTimer = window.setTimeout(() => setLoadingPhase(2), 1500)
    try {
      const headers = authHeaders()
      await axios.put(`${API_BASE}/summary/recalculate/`, {}, { headers, timeout: 60000 })
      await loadPlanData(headers)
    } catch (err) {
      setError(err.response?.data?.message || err.response?.data?.error || 'Cədvəli yeniləmək mümkün olmadı.')
    } finally {
      window.clearTimeout(phaseTimer)
      setLoading(false)
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
            {visibleGoals.map((goal, idx) => {
              const amount = numberValue(goal.current_amount)
              const target = numberValue(goal.target_amount)
              const monthlySaving = numberValue(goal.recommended_monthly_saving)

              const projectedAmount = Math.min(target, amount + monthlySaving * 12)
              const progress = target > 0 ? Math.min(100, Math.round((projectedAmount / target) * 100)) : 0

              const GoalIcon = getGoalIcon(goal)
              return (
                <div className="results-goal-card" key={idx}>
                  <div className="results-goal-title">
                    <span><GoalIcon size={20} strokeWidth={2} /></span>
                    {goal.goal_name || 'Yığım məqsədi'}
                  </div>
                  <div className="results-progress-track"><span style={{ width: `${progress}%` }} /></div>
                  <small>
                    <span>{money(goal.recommended_monthly_saving)}/ay</span>
                    <span className="results-goal-priority">
                      <span className="results-goal-priority-dot" aria-hidden="true" />
                      <span className="results-goal-priority-label">Prioritet:</span>
                      <span className="results-goal-priority-value">{goal.priority}</span>
                    </span>
                  </small>
                </div>
              )
            })}
          </div>
        ) : <div className="results-empty-state">Hələ yığım məqsədi seçilməyib.</div>}
      </section>

      <section className="annual-plan-section results-panel">
        <div className="results-section-heading plan-heading">
          <div><h2>AI tərəfindən hazırlanmış 12 aylıq plan</h2><p>Hər ay üçün xərcləri ayrıca bölür və yığım və qalıq məbləğini hesablayır.</p></div>
          <div className="results-actions">
            <button type="button" className="results-action" onClick={handleEdit}><FilePenLine size={14} /> Cavabı dəyiş</button>
            <button type="button" className="results-action" onClick={handleRefreshTable}><RefreshCw size={14} /> Cədvəli yenilə</button>
            <button type="button" className="results-action" onClick={() => setShowNewPlanModal(true)}><Plus size={14} /> Yeni plan əlavə et</button>
          </div>
        </div>
        <div className="results-table-scroll">
          <table className="annual-plan-table">
            <thead><tr><th>Ay</th>{TABLE_COLUMNS.map((column) => <th key={column.key}>{column.label}</th>)}</tr></thead>
            <tbody>{months.map((month, monthIndex) => <tr key={MONTHS[monthIndex] || monthIndex}>
              <th><span className="month-pill">{month.month_name || MONTHS[monthIndex]}</span></th>
              {TABLE_COLUMNS.map((column) => <td key={column.key}>
                {column.editable === false
                  ? <strong className={calculateBalance(month) < 0 ? 'negative-value' : ''}>{money(calculateBalance(month))}</strong>
                  : <input aria-label={`${month.month_name} ${column.label}`} type="number" min="0" value={month[column.key] ?? ''} placeholder="0" onChange={(event) => updateCell(monthIndex, column.key, event.target.value)} />}
              </td>)}
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
            <tbody>{comparison.map((row, idx) => <tr key={idx}>
              <th>{CATEGORY_LABELS[row.category_name] || row.category_name}</th>
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
            </tr>)}</tbody>
          </table>
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