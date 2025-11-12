// Input Component - Figma-ready design system component
import React from 'react'
import { designTokens } from './tokens'

export const Input = ({ 
  type = 'text',
  placeholder,
  value,
  onChange,
  disabled = false,
  error = false,
  helperText,
  label,
  required = false,
  size = 'base',
  fullWidth = false,
  icon,
  className,
  style = {},
  ...props 
}) => {
  const tokens = designTokens
  
  const containerStyle = {
    display: 'flex',
    flexDirection: 'column',
    gap: tokens.spacing[1],
    width: fullWidth ? '100%' : 'auto',
    fontFamily: tokens.typography.fontFamily.primary
  }

  const labelStyle = {
    fontSize: tokens.typography.fontSize.sm,
    fontWeight: tokens.typography.fontWeight.medium,
    color: tokens.colors.neutral[700],
    marginBottom: tokens.spacing[1]
  }

  const inputWrapperStyle = {
    position: 'relative',
    display: 'flex',
    alignItems: 'center'
  }

  const inputStyle = {
    width: '100%',
    padding: tokens.size[size].padding,
    fontSize: tokens.size[size].fontSize,
    border: `2px solid ${error ? tokens.colors.danger[500] : tokens.colors.neutral[300]}`,
    borderRadius: tokens.borderRadius.base,
    backgroundColor: disabled ? tokens.colors.neutral[100] : tokens.colors.neutral[0],
    color: tokens.colors.neutral[800],
    fontFamily: tokens.typography.fontFamily.primary,
    transition: `border-color ${tokens.animation.duration.normal} ${tokens.animation.easing.easeOut}`,
    boxSizing: 'border-box',
    outline: 'none',
    paddingLeft: icon ? '40px' : tokens.size[size].padding.split(' ')[1],
    ...style
  }

  const iconStyle = {
    position: 'absolute',
    left: tokens.spacing[3],
    color: tokens.colors.neutral[500],
    pointerEvents: 'none'
  }

  const helperTextStyle = {
    fontSize: tokens.typography.fontSize.xs,
    color: error ? tokens.colors.danger[600] : tokens.colors.neutral[500],
    marginTop: tokens.spacing[1]
  }

  const focusStyle = {
    ':focus': {
      borderColor: error ? tokens.colors.danger[500] : tokens.colors.primary[500],
      boxShadow: `0 0 0 3px ${error ? tokens.colors.danger[100] : tokens.colors.primary[100]}`
    }
  }

  return (
    <div style={containerStyle} className={className}>
      {label && (
        <label style={labelStyle}>
          {label}
          {required && <span style={{ color: tokens.colors.danger[500] }}>*</span>}
        </label>
      )}
      <div style={inputWrapperStyle}>
        {icon && <span style={iconStyle}>{icon}</span>}
        <input
          type={type}
          placeholder={placeholder}
          value={value}
          onChange={onChange}
          disabled={disabled}
          style={{
            ...inputStyle,
            ...(document.activeElement === React.createRef().current ? focusStyle[':focus'] : {})
          }}
          onFocus={(e) => {
            e.target.style.borderColor = error ? tokens.colors.danger[500] : tokens.colors.primary[500]
            e.target.style.boxShadow = `0 0 0 3px ${error ? tokens.colors.danger[100] : tokens.colors.primary[100]}`
          }}
          onBlur={(e) => {
            e.target.style.borderColor = error ? tokens.colors.danger[500] : tokens.colors.neutral[300]
            e.target.style.boxShadow = 'none'
          }}
          {...props}
        />
      </div>
      {helperText && (
        <span style={helperTextStyle}>{helperText}</span>
      )}
    </div>
  )
}

// Select Component
export const Select = ({ 
  options = [],
  value,
  onChange,
  placeholder = 'Select an option',
  disabled = false,
  error = false,
  label,
  required = false,
  size = 'base',
  fullWidth = false,
  className,
  style = {},
  ...props 
}) => {
  const tokens = designTokens
  
  const containerStyle = {
    display: 'flex',
    flexDirection: 'column',
    gap: tokens.spacing[1],
    width: fullWidth ? '100%' : 'auto',
    fontFamily: tokens.typography.fontFamily.primary
  }

  const labelStyle = {
    fontSize: tokens.typography.fontSize.sm,
    fontWeight: tokens.typography.fontWeight.medium,
    color: tokens.colors.neutral[700],
    marginBottom: tokens.spacing[1]
  }

  const selectStyle = {
    width: '100%',
    padding: tokens.size[size].padding,
    fontSize: tokens.size[size].fontSize,
    border: `2px solid ${error ? tokens.colors.danger[500] : tokens.colors.neutral[300]}`,
    borderRadius: tokens.borderRadius.base,
    backgroundColor: disabled ? tokens.colors.neutral[100] : tokens.colors.neutral[0],
    color: tokens.colors.neutral[800],
    fontFamily: tokens.typography.fontFamily.primary,
    transition: `border-color ${tokens.animation.duration.normal} ${tokens.animation.easing.easeOut}`,
    boxSizing: 'border-box',
    outline: 'none',
    cursor: disabled ? 'not-allowed' : 'pointer',
    ...style
  }

  return (
    <div style={containerStyle} className={className}>
      {label && (
        <label style={labelStyle}>
          {label}
          {required && <span style={{ color: tokens.colors.danger[500] }}>*</span>}
        </label>
      )}
      <select
        value={value}
        onChange={onChange}
        disabled={disabled}
        style={selectStyle}
        onFocus={(e) => {
          e.target.style.borderColor = error ? tokens.colors.danger[500] : tokens.colors.primary[500]
          e.target.style.boxShadow = `0 0 0 3px ${error ? tokens.colors.danger[100] : tokens.colors.primary[100]}`
        }}
        onBlur={(e) => {
          e.target.style.borderColor = error ? tokens.colors.danger[500] : tokens.colors.neutral[300]
          e.target.style.boxShadow = 'none'
        }}
        {...props}
      >
        {placeholder && <option value="">{placeholder}</option>}
        {options.map((option, index) => (
          <option key={index} value={option.value || option}>
            {option.label || option}
          </option>
        ))}
      </select>
    </div>
  )
}

export default Input