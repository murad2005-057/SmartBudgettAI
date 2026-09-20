import React from 'react'
import { ExpenseInputField } from './ExpenseInputField'

const EXPENSES = [
  { id: 'market', icon: '🛒', label: 'Market və qida' },
  { id: 'utilities', icon: '💰', label: 'Kommunal ödənişlər' },
  { id: 'transport', icon: '🚗', label: 'Nəqliyyat' },
  { id: 'restaurant', icon: '🍽️', label: 'Restoran və kafe' },
  { id: 'clothing', icon: '👗', label: 'Geyim' },
  { id: 'entertainment', icon: '🎮', label: 'Əyləncə' },
  { id: 'onlineShopping', icon: '🛍️', label: 'Onlayn alış-veriş' },
  { id: 'other', icon: '🎯', label: 'Digər xərclər' }
]

export function StepMonthlyExpenses({ values, onChange, onClear }) {
  return (
    <div className="step-content">
      <h4 className="question-title">Hazırda xərcləriniz nə qədərdir?</h4>
      <p className="expense-subtitle">
        Məbləğləri təxmini yaza bilərsiniz. Xərciniz yoxdursa 0 qeyd edin.
      </p>
      <div className="monthly-expenses-grid">
        {EXPENSES.map((expense) => (
          <ExpenseInputField
            key={expense.id}
            id={`monthly-expense-${expense.id}`}
            icon={expense.icon}
            label={expense.label}
            value={values[expense.id]}
            onChange={(value) => onChange(expense.id, value)}
            onClear={() => onClear(expense.id)}
          />
        ))}
      </div>
    </div>
  )
}
