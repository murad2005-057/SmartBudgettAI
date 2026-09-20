import React from 'react'
import { LuX } from 'react-icons/lu'

export function CustomInput({
  value,
  onChange,
  onClear,
  placeholder = '0',
  id,
  label,
  type = 'number'
}) {
  const handleInputChange = (e) => {
    const val = e.target.value

    if (type === 'text') {
      onChange(val)
      return
    }

    // Numeric mode: only digits or decimal allowed
    if (val === '' || /^\d*\.?\d*$/.test(val)) {
      onChange(val)
    }
  }

  return (
    <div className="custom-input-wrapper">
      {label && <label htmlFor={id} className="custom-input-label">{label}</label>}
      <div className="input-with-clear">
        <input
          id={id}
          type="text"
          inputMode={type === 'text' ? 'text' : 'decimal'}
          className="custom-input-field"
          value={value}
          onChange={handleInputChange}
          placeholder={placeholder}
        />
        {value && value !== '' && (
          <button
            type="button"
            className="clear-input-btn"
            onClick={onClear}
            aria-label="Təmizlə"
            title="Təmizlə"
          >
            <LuX size={16} />
          </button>
        )}
      </div>
    </div>
  )
}