// Button Component - Figma-ready design system component
import React from 'react'
import { designTokens, createComponentStyle } from './tokens'

export const Button = ({ 
  children, 
  variant = 'primary', 
  size = 'base', 
  disabled = false, 
  loading = false, 
  fullWidth = false,
  onClick,
  type = 'button',
  icon,
  className,
  style = {},
  ...props 
}) => {
  const baseStyle = createComponentStyle(variant, size)
  
  const buttonStyle = {
    ...baseStyle,
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: designTokens.spacing[2],
    width: fullWidth ? '100%' : 'auto',
    opacity: disabled || loading ? 0.6 : 1,
    cursor: disabled || loading ? 'not-allowed' : 'pointer',
    position: 'relative',
    ...style
  }

  const loadingSpinnerStyle = {
    width: '16px',
    height: '16px',
    border: '2px solid transparent',
    borderTop: `2px solid ${variant === 'secondary' ? designTokens.colors.neutral[500] : designTokens.colors.neutral[0]}`,
    borderRadius: '50%',
    animation: 'spin 1s linear infinite'
  }

  return (
    <>
      <style>
        {`
          @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
          }
        `}
      </style>
      <button
        type={type}
        onClick={disabled || loading ? undefined : onClick}
        style={buttonStyle}
        className={className}
        {...props}
      >
        {loading && <div style={loadingSpinnerStyle} />}
        {!loading && icon && <span>{icon}</span>}
        {!loading && children}
      </button>
    </>
  )
}

// Button variants for easy Figma import
export const PrimaryButton = (props) => <Button variant="primary" {...props} />
export const SecondaryButton = (props) => <Button variant="secondary" {...props} />
export const SuccessButton = (props) => <Button variant="success" {...props} />
export const DangerButton = (props) => <Button variant="danger" {...props} />
export const WarningButton = (props) => <Button variant="warning" {...props} />

export default Button