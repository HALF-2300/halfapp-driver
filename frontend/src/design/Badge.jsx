// Badge Component - Figma-ready design system component
import React from 'react'
import { designTokens } from './tokens'

export const Badge = ({ 
  children,
  variant = 'primary',
  size = 'base',
  className,
  style = {},
  ...props 
}) => {
  const tokens = designTokens
  
  const sizes = {
    sm: {
      padding: `${tokens.spacing[1]} ${tokens.spacing[2]}`,
      fontSize: tokens.typography.fontSize.xs,
    },
    base: {
      padding: `${tokens.spacing[1]} ${tokens.spacing[3]}`,
      fontSize: tokens.typography.fontSize.xs,
    },
    lg: {
      padding: `${tokens.spacing[2]} ${tokens.spacing[3]}`,
      fontSize: tokens.typography.fontSize.sm,
    }
  }

  const variants = {
    primary: {
      backgroundColor: tokens.colors.primary[500],
      color: tokens.colors.neutral[0]
    },
    secondary: {
      backgroundColor: tokens.colors.neutral[200],
      color: tokens.colors.neutral[700]
    },
    success: {
      backgroundColor: tokens.colors.success[500],
      color: tokens.colors.neutral[0]
    },
    warning: {
      backgroundColor: tokens.colors.warning[500],
      color: tokens.colors.neutral[0]
    },
    danger: {
      backgroundColor: tokens.colors.danger[500],
      color: tokens.colors.neutral[0]
    },
    light: {
      backgroundColor: tokens.colors.success[50],
      color: tokens.colors.success[700],
      border: `1px solid ${tokens.colors.success[200]}`
    },
    'light-warning': {
      backgroundColor: tokens.colors.warning[50],
      color: tokens.colors.warning[700],
      border: `1px solid ${tokens.colors.warning[200]}`
    },
    'light-danger': {
      backgroundColor: tokens.colors.danger[50],
      color: tokens.colors.danger[700],
      border: `1px solid ${tokens.colors.danger[200]}`
    }
  }

  const badgeStyle = {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: tokens.borderRadius.full,
    fontWeight: tokens.typography.fontWeight.medium,
    textTransform: 'uppercase',
    letterSpacing: '0.025em',
    fontFamily: tokens.typography.fontFamily.primary,
    ...sizes[size],
    ...variants[variant],
    ...style
  }

  return (
    <span style={badgeStyle} className={className} {...props}>
      {children}
    </span>
  )
}

// Status Badge Component
export const StatusBadge = ({ 
  status,
  activeText = 'Active',
  inactiveText = 'Inactive',
  className,
  style = {},
  ...props 
}) => {
  const isActive = status === 'true' || status === true || status === 'active'
  
  return (
    <Badge
      variant={isActive ? 'light' : 'light-danger'}
      className={className}
      style={style}
      {...props}
    >
      {isActive ? `✅ ${activeText}` : `❌ ${inactiveText}`}
    </Badge>
  )
}

// Role Badge Component
export const RoleBadge = ({ 
  role,
  className,
  style = {},
  ...props 
}) => {
  const roleVariants = {
    admin: 'danger',
    driver: 'warning',
    customer: 'success',
    user: 'secondary'
  }

  return (
    <Badge
      variant={roleVariants[role?.toLowerCase()] || 'secondary'}
      className={className}
      style={style}
      {...props}
    >
      {role?.toUpperCase()}
    </Badge>
  )
}

export default Badge