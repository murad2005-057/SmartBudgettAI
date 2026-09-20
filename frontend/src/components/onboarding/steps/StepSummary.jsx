import React from 'react'
import { CheckCircle, TrendingUp, DollarSign, PieChart } from 'lucide-react'

export function StepSummary({ formData, userName, onReset }) {
  const salary = Number(formData.salary) || 0
  const extraIncome = formData.hasExtraIncome === 'Bəli' ? (Number(formData.extraIncome) || 0) : 0
  const totalIncome = salary + extraIncome

  const housing = Number(formData.housing) || 0
  const utilities = Number(formData.utilities) || 0
  const groceries = Number(formData.groceries) || 0
  const transport = Number(formData.transport) || 0
  const debt = formData.hasDebts === 'Bəli' ? (Number(formData.debtAmount) || 0) : 0
  const entertainment = Number(formData.entertainment) || 0
  const totalExpenses = housing + utilities + groceries + transport + debt + entertainment

  const savingsGoal = Number(formData.savingsGoal) || 0
  const netBalance = totalIncome - totalExpenses

  return (
    <div className="step-content summary-content">
      <div className="summary-badge">
        <CheckCircle size={24} className="summary-check-icon" />
        <span>Fərdiləşdirilmiş AI Planınız Hazırdır!</span>
      </div>

      <h4 className="question-title text-center">
        Əla, {userName}! Maliyyə planınız tam balanslaşdırıldı.
      </h4>

      <div className="summary-cards-grid">
        <div className="summary-card income-card">
          <div className="card-header-icon">
            <DollarSign size={20} />
          </div>
          <span className="summary-label">Ümumi Gəlir</span>
          <strong className="summary-amount">{totalIncome} ₼</strong>
        </div>

        <div className="summary-card expense-card">
          <div className="card-header-icon">
            <PieChart size={20} />
          </div>
          <span className="summary-label">Ümumi Xərc</span>
          <strong className="summary-amount">{totalExpenses} ₼</strong>
        </div>

        <div className="summary-card balance-card">
          <div className="card-header-icon">
            <TrendingUp size={20} />
          </div>
          <span className="summary-label">Xalis Balans</span>
          <strong className={`summary-amount ${netBalance >= 0 ? 'positive' : 'negative'}`}>
            {netBalance} ₼
          </strong>
        </div>
      </div>

      <div className="summary-recommendation">
        <h5>AI Tövsiyəsi:</h5>
        <p>
          {netBalance >= savingsGoal
            ? `Təbrik edirik! Aylıq ${savingsGoal} ₼ qənaət hədəfinizə tam çata bilirsiniz və əlavə ${netBalance - savingsGoal} ₼ ehtiyatınız qalır.`
            : netBalance > 0
            ? `Aylıq qalıq balansınız ${netBalance} ₼-dir. ${savingsGoal} ₼ hədəfinizə çatmaq üçün xərcləri biraz optimallaşdırmağı tövsiyə edirik.`
            : `Aylıq xərcləriniz gəlirinizi üstələyir. Xərc kateqoriyalarınızı yenidən nəzərdən keçirin.`}
        </p>
      </div>

      <div className="summary-actions">
        <button type="button" className="btn-restart" onClick={onReset}>
          Yenidən başla
        </button>
      </div>
    </div>
  )
}
