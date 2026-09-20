import React from 'react'

const SAVINGS_OPTIONS = ['Bəli, müntəzəm', 'Bəzən', 'Xeyr']

export function StepMonthlySavingsAbility({ value, onChange }) {
  return (
    <div className="step-content">
      <h4 className="question-title">Hər ay pul yığa bilirsiniz?</h4>
      <div className="savings-ability-options">
        {SAVINGS_OPTIONS.map((option) => (
          <button
            key={option}
            type="button"
            className={`savings-ability-option${value === option ? ' is-selected' : ''}`}
            onClick={() => onChange(option)}
            aria-pressed={value === option}
          >
            {option}
          </button>
        ))}
      </div>
    </div>
  )
}
