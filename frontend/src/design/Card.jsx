// Card Component - Figma-ready design system component
import React from 'react'
import { designTokens } from './tokens'

export const Card = ({ 
  children,
  padding = 'base',
  shadow = 'base',
  border = true,
  className,
  style = {},
  ...props 
}) => {
  const tokens = designTokens
  
  const paddingValues = {
    none: '0px',
    sm: tokens.spacing[3],
    base: tokens.spacing[5],
    lg: tokens.spacing[6],
    xl: tokens.spacing[8]
  }

  const cardStyle = {
    backgroundColor: tokens.colors.neutral[0],
    borderRadius: tokens.borderRadius.lg,
    padding: paddingValues[padding],
    border: border ? `1px solid ${tokens.colors.neutral[200]}` : 'none',
    boxShadow: tokens.boxShadow[shadow],
    fontFamily: tokens.typography.fontFamily.primary,
    ...style
  }

  return (
    <div style={cardStyle} className={className} {...props}>
      {children}
    </div>
  )
}

// Card Header Component
export const CardHeader = ({ 
  title,
  subtitle,
  actions,
  className,
  style = {},
  ...props 
}) => {
  const tokens = designTokens
  
  const headerStyle = {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: tokens.spacing[4],
    ...style
  }

  const titleStyle = {
    fontSize: tokens.typography.fontSize['2xl'],
    fontWeight: tokens.typography.fontWeight.semibold,
    color: tokens.colors.neutral[800],
    margin: 0,
    marginBottom: subtitle ? tokens.spacing[1] : 0
  }

  const subtitleStyle = {
    fontSize: tokens.typography.fontSize.sm,
    color: tokens.colors.neutral[500],
    margin: 0
  }

  return (
    <div style={headerStyle} className={className} {...props}>
      <div>
        <h3 style={titleStyle}>{title}</h3>
        {subtitle && <p style={subtitleStyle}>{subtitle}</p>}
      </div>
      {actions && <div>{actions}</div>}
    </div>
  )
}

// Card Content Component
export const CardContent = ({ 
  children,
  className,
  style = {},
  ...props 
}) => {
  const tokens = designTokens
  
  const contentStyle = {
    color: tokens.colors.neutral[700],
    lineHeight: tokens.typography.lineHeight.normal,
    ...style
  }

  return (
    <div style={contentStyle} className={className} {...props}>
      {children}
    </div>
  )
}

// Card Footer Component
export const CardFooter = ({ 
  children,
  className,
  style = {},
  ...props 
}) => {
  const tokens = designTokens
  
  const footerStyle = {
    marginTop: tokens.spacing[4],
    paddingTop: tokens.spacing[4],
    borderTop: `1px solid ${tokens.colors.neutral[200]}`,
    display: 'flex',
    justifyContent: 'flex-end',
    gap: tokens.spacing[3],
    ...style
  }

  return (
    <div style={footerStyle} className={className} {...props}>
      {children}
    </div>
  )
}

// Statistics Card Component
export const StatCard = ({ 
  title,
  value,
  subtitle,
  icon,
  color = 'primary',
  className,
  style = {},
  ...props 
}) => {
  const tokens = designTokens
  
  const colors = {
    primary: tokens.colors.primary[500],
    success: tokens.colors.success[500],
    warning: tokens.colors.warning[500],
    danger: tokens.colors.danger[500]
  }

  const statCardStyle = {
    backgroundColor: tokens.colors.neutral[0],
    borderRadius: tokens.borderRadius.lg,
    padding: tokens.spacing[5],
    border: `1px solid ${tokens.colors.neutral[200]}`,
    boxShadow: tokens.boxShadow.base,
    textAlign: 'center',
    fontFamily: tokens.typography.fontFamily.primary,
    ...style
  }

  const valueStyle = {
    fontSize: tokens.typography.fontSize['4xl'],
    fontWeight: tokens.typography.fontWeight.bold,
    color: colors[color],
    margin: 0,
    marginBottom: tokens.spacing[1]
  }

  const titleStyle = {
    fontSize: tokens.typography.fontSize.sm,
    color: tokens.colors.neutral[500],
    margin: 0,
    textTransform: 'uppercase',
    letterSpacing: '0.05em'
  }

  const subtitleStyle = {
    fontSize: tokens.typography.fontSize.xs,
    color: tokens.colors.neutral[400],
    margin: 0,
    marginTop: tokens.spacing[1]
  }

  const iconStyle = {
    fontSize: tokens.typography.fontSize['2xl'],
    color: colors[color],
    marginBottom: tokens.spacing[2]
  }

  return (
    <div style={statCardStyle} className={className} {...props}>
      {icon && <div style={iconStyle}>{icon}</div>}
      <div style={valueStyle}>{value}</div>
      <div style={titleStyle}>{title}</div>
      {subtitle && <div style={subtitleStyle}>{subtitle}</div>}
    </div>
  )
}

export default Card