import { useEffect, useState } from 'react'
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
import { BUDGET_MONTHS_STORAGE_KEY } from '../../hooks/useOnboardingForm'

const MONTHS = ['Yan', 'Fev', 'Mar', 'Apr', 'May', 'İyn', 'İyl', 'Avq', 'Sen', 'Okt', 'Noy', 'Dek']
const TABLE_COLUMNS = [
  { key: 'income', label: 'Gəlir' },
  { key: 'restaurant', label: 'Restoran' },
  { key: 'entertainment', label: 'Əyləncə' },
  { key: 'food', label: 'Qida' },
  { key: 'utilities', label: 'Kommunal' },
  { key: 'transport', label: 'Nəqliyyat' },
  { key: 'credit', label: 'Kredit' },
  { key: 'other', label: 'Digər' },
  { key: 'savings', label: 'Yığım' },
  { key: 'balance', label: 'Qalıq', editable: false }
]

const numberValue = (value) => Number(value) || 0
const money = (value) => `${value.toLocaleString('az-AZ')} AZN`

const getInitialMonth = (formData) => ({
  income: numberValue(formData.salary) + (formData.hasExtraIncome === 'Bəli' ? numberValue(formData.extraIncome) : 0),
  restaurant: numberValue(formData.monthlyExpenses?.restaurant),
  entertainment: numberValue(formData.monthlyExpenses?.entertainment),
  food: numberValue(formData.monthlyExpenses?.market),
  utilities: numberValue(formData.monthlyExpenses?.utilities),
  transport: numberValue(formData.monthlyExpenses?.transport),
  credit: formData.hasCredit === 'Bəli'
    ? (formData.credits || []).reduce((total, credit) => total + numberValue(credit.monthly), 0)
    : 0,
  other: numberValue(formData.housingAmount) + numberValue(formData.monthlyExpenses?.other),
  savings: numberValue(formData.savingsGoal),
  balance: 0
})

const createMonths = (formData) => Array.from({ length: 12 }, () => getInitialMonth(formData))

const getSavedMonths = () => {
  try {
    const savedMonths = window.localStorage.getItem(BUDGET_MONTHS_STORAGE_KEY)
    const parsedMonths = savedMonths ? JSON.parse(savedMonths) : null
    return Array.isArray(parsedMonths) && parsedMonths.length === 12 ? parsedMonths : null
  } catch {
    return null
  }
}

const calculateBalance = (month) => month.income - (
  month.restaurant +
  month.entertainment +
  month.food +
  month.utilities +
  month.transport +
  month.credit +
  month.other +
  month.savings
)

const getBudgetTag = (key, value, total) => {
  if (key === 'credit' || key === 'utilities') return { label: 'Prioritet Ödəniş', tone: 'priority' }
  if (total > 0 && value / total > 0.3) return { label: 'Diqqət', tone: 'attention' }
  return { label: 'Uyğundur', tone: 'good' }
}

const getGoalIcon = (goal) => {
  const title = (goal.label || goal.name || '').toLocaleLowerCase('az-AZ')

  if (title.includes('ev')) return Home
  if (title.includes('avtomobil')) return Car
  if (title.includes('səyahət')) return Plane
  if (title.includes('təhsil')) return GraduationCap
  if (title.includes('təcili')) return ShieldAlert
  return Target
}

export function BudgetPlanResults({ formData, userName, onEdit, onNewPlan, onReset }) {
  const [months, setMonths] = useState(() => getSavedMonths() || createMonths(formData))
  const [showAllGoals, setShowAllGoals] = useState(false)
  const [showNewPlanModal, setShowNewPlanModal] = useState(false)

  useEffect(() => {
    window.localStorage.setItem(BUDGET_MONTHS_STORAGE_KEY, JSON.stringify(months))
  }, [months])

  const updateCell = (monthIndex, key, value) => {
    setMonths((current) => current.map((month, index) => (
      index === monthIndex ? { ...month, [key]: value === '' ? 0 : numberValue(value) } : month
    )))
  }

  const totals = TABLE_COLUMNS.reduce((result, column) => ({
    ...result,
    [column.key]: months.reduce((total, month) => total + (column.key === 'balance' ? calculateBalance(month) : month[column.key]), 0)
  }), {})

  const monthlySavings = months.reduce((total, month) => total + month.savings, 0) / 12
  const annualIncome = totals.income
  const distributionRows = TABLE_COLUMNS.filter(({ key }) => !['income', 'balance'].includes(key)).map((column) => ({
    ...column,
    total: totals[column.key],
    percentage: annualIncome > 0 ? Math.round((totals[column.key] / annualIncome) * 1000) / 10 : 0,
    tag: getBudgetTag(column.key, totals[column.key], annualIncome)
  }))
  const goals = formData.savingsGoals || []

  const exportExcel = () => {
    const header = ['Ay', ...TABLE_COLUMNS.map((column) => column.label)]
    const rows = months.map((month, index) => [MONTHS[index], ...TABLE_COLUMNS.map((column) => column.key === 'balance' ? calculateBalance(month) : month[column.key])])
    const worksheet = XLSX.utils.aoa_to_sheet([
      header,
      ...rows,
      ['İllik cəmi', ...TABLE_COLUMNS.map((column) => totals[column.key])]
    ])
    worksheet['!cols'] = [{ wch: 14 }, ...TABLE_COLUMNS.map(() => ({ wch: 14 }))]
    const workbook = XLSX.utils.book_new()
    XLSX.utils.book_append_sheet(workbook, worksheet, '12 aylıq plan')
    XLSX.writeFile(workbook, 'smartbudget-plan.xlsx')
  }

  const visibleGoals = showAllGoals ? goals : goals.slice(0, 3)

  return (
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
            <strong>{money(Math.round(monthlySavings))}</strong>
          </div>
          <span className="results-summary-icon"><PiggyBank size={20} strokeWidth={2} /></span>
        </div>
        <div className="results-summary-card">
          <div className="results-summary-copy">
            <span>Tövsiyə olunan illik yığım</span>
            <strong>{money(totals.savings)}</strong>
          </div>
          <span className="results-summary-icon"><TrendingUp size={20} strokeWidth={2} /></span>
        </div>
        <div className="results-summary-card results-summary-card-accent">
          <div className="results-summary-copy">
            <span>Maliyyə vəziyyəti</span>
            <strong>{totals.balance >= 0 ? 'Balanslı' : 'Diqqət'}</strong>
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
            {visibleGoals.map((goal) => {
              const amount = numberValue(goal.amount)
              const target = numberValue(goal.target || goal.amount)
              const progress = target > 0 ? Math.min(100, Math.round((amount / target) * 100)) : 0
              const GoalIcon = getGoalIcon(goal)
              return (
                <div className="results-goal-card" key={goal.id}>
                  <div className="results-goal-title">
                    <span><GoalIcon size={20} strokeWidth={2} /></span>
                    {goal.label || goal.name || 'Yığım məqsədi'}
                  </div>
                  <div className="results-goal-amounts">{money(amount)} <b>/ {money(target)}</b><strong>{progress}%</strong></div>
                  <div className="results-progress-track"><span style={{ width: `${progress}%` }} /></div>
                  <small>
                    <span>{money(Math.round(amount / 12))}/ay</span>
                    <span className="results-goal-priority">
                      <span className="results-goal-priority-dot" aria-hidden="true" />
                      <span className="results-goal-priority-label">Prioritet:</span>
                      <span className="results-goal-priority-value">{ 'Orta'}</span>
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
            <button type="button" className="results-action" onClick={onEdit}><FilePenLine size={14} /> Cavabı dəyiş</button>
            <button type="button" className="results-action" onClick={() => setMonths(createMonths(formData))}><RefreshCw size={14} /> Cədvəli yenilə</button>
            <button type="button" className="results-action" onClick={() => setShowNewPlanModal(true)}><Plus size={14} /> Yeni plan əlavə et</button>
          </div>
        </div>
        <div className="results-table-scroll">
          <table className="annual-plan-table">
            <thead><tr><th>Ay</th>{TABLE_COLUMNS.map((column) => <th key={column.key}>{column.label}</th>)}</tr></thead>
            <tbody>{months.map((month, monthIndex) => <tr key={MONTHS[monthIndex]}>
              <th><span className="month-pill">{MONTHS[monthIndex]}</span></th>
              {TABLE_COLUMNS.map((column) => <td key={column.key}>
                {column.editable === false ? <strong className={calculateBalance(month) < 0 ? 'negative-value' : ''}>{money(calculateBalance(month))}</strong> : <input aria-label={`${MONTHS[monthIndex]} ${column.label}`} type="number" min="0" value={month[column.key] || ''} placeholder="0" onChange={(event) => updateCell(monthIndex, column.key, event.target.value)} />}
              </td>)}
            </tr>)}</tbody>
            <tfoot><tr><th>İllik cəmi</th>{TABLE_COLUMNS.map((column) => <th key={column.key} className={column.key === 'balance' && totals.balance < 0 ? 'negative-value' : ''}>{money(totals[column.key])}</th>)}</tr></tfoot>
          </table>
        </div>
        <div className="results-panel-footer"><button type="button" className="results-action results-action-primary" onClick={exportExcel}><Download size={14} /> Excel yüklə</button></div>
      </section>

      <section className="distribution-section results-panel">
        <div className="results-section-heading"><div><h2>Tövsiyə olunan büdcə bölgüsü</h2><p>İllik planınızın kateqoriyalar üzrə paylanması</p></div></div>
        <div className="results-table-scroll"><table className="distribution-table"><thead><tr><th>Kateqoriya</th><th>%</th><th>Hazırkı aylıq</th><th>Tövsiyə olunan aylıq</th><th>İllik məbləğ</th><th>Qiymətləndirmə</th></tr></thead><tbody>{distributionRows.map((row) => <tr key={row.key}><th>{row.label}</th><td>{row.percentage}%</td><td>{money(Math.round(row.total / 12))}</td><td><strong>{money(Math.round(row.total / 12))}</strong></td><td>{money(row.total)}</td><td><span className={`budget-tag ${row.tag.tone}`}>{row.tag.label}</span></td></tr>)}</tbody></table></div>
      </section>

      <button type="button" className="results-reset-button" onClick={onReset}>Yenidən başla</button>

      {showNewPlanModal && (
        <div className="results-modal-backdrop" role="presentation" onClick={() => setShowNewPlanModal(false)}>
          <div className="results-modal" role="dialog" aria-modal="true" aria-labelledby="new-plan-title" onClick={(event) => event.stopPropagation()}>
            <h2 id="new-plan-title">Yeni plan yaradılsın?</h2>
            <p>Hazırkı plan saxlanılmayacaq və yeni büdcə hesablaması başlayacaq.</p>
            <div className="results-modal-actions">
              <button type="button" className="results-action" onClick={() => setShowNewPlanModal(false)}>Ləğv et</button>
              <button type="button" className="results-action results-action-primary" onClick={onNewPlan}>Yeni plana başla</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}