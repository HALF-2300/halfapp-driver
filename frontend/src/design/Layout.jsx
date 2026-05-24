// Layout Components - Figma-ready design system components
import React from 'react'
import { designTokens } from './tokens'

// Container Component
export const Container = ({ 
  children,
  maxWidth = 'lg',
  padding = 'base',
  center = true,
  className,
  style = {},
  ...props 
}) => {
  const tokens = designTokens
  
  const maxWidths = {
    sm: '640px',
    md: '768px',
    lg: '1024px',
    xl: '1280px',
    full: '100%'
  }

  const paddings = {
    none: '0px',
    sm: tokens.spacing[4],
    base: tokens.spacing[5],
    lg: tokens.spacing[6],
    xl: tokens.spacing[8]
  }

  const containerStyle = {
    width: '100%',
    maxWidth: maxWidths[maxWidth],
    margin: center ? '0 auto' : '0',
    padding: `0 ${paddings[padding]}`,
    fontFamily: tokens.typography.fontFamily.primary,
    ...style
  }

  return (
    <div style={containerStyle} className={className} {...props}>
      {children}
    </div>
  )
}

// Grid Component
export const Grid = ({ 
  children,
  columns = 1,
  gap = 'base',
  responsive = false,
  className,
  style = {},
  ...props 
}) => {
  const tokens = designTokens
  
  const gaps = {
    none: '0px',
    sm: tokens.spacing[2],
    base: tokens.spacing[4],
    lg: tokens.spacing[6],
    xl: tokens.spacing[8]
  }

  const getGridColumns = () => {
    if (responsive) {
      return `repeat(auto-fit, minmax(250px, 1fr))`
    }
    return typeof columns === 'number' ? `repeat(${columns}, 1fr)` : columns
  }

  const gridStyle = {
    display: 'grid',
    gridTemplateColumns: getGridColumns(),
    gap: gaps[gap],
    ...style
  }

  return (
    <div style={gridStyle} className={className} {...props}>
      {children}
    </div>
  )
}

// Flex Component
export const Flex = ({ 
  children,
  direction = 'row',
  justify = 'flex-start',
  align = 'stretch',
  wrap = 'nowrap',
  gap = 'base',
  className,
  style = {},
  ...props 
}) => {
  const tokens = designTokens
  
  const gaps = {
    none: '0px',
    sm: tokens.spacing[2],
    base: tokens.spacing[4],
    lg: tokens.spacing[6],
    xl: tokens.spacing[8]
  }

  const flexStyle = {
    display: 'flex',
    flexDirection: direction,
    justifyContent: justify,
    alignItems: align,
    flexWrap: wrap,
    gap: gaps[gap],
    ...style
  }

  return (
    <div style={flexStyle} className={className} {...props}>
      {children}
    </div>
  )
}

// Stack Component (Flex with column direction)
export const Stack = ({ 
  children,
  spacing = 'base',
  align = 'stretch',
  className,
  style = {},
  ...props 
}) => {
  return (
    <Flex
      direction="column"
      align={align}
      gap={spacing}
      className={className}
      style={style}
      {...props}
    >
      {children}
    </Flex>
  )
}

// Section Component
export const Section = ({ 
  children,
  padding = 'lg',
  background = 'transparent',
  className,
  style = {},
  ...props 
}) => {
  const tokens = designTokens
  
  const paddings = {
    none: '0px',
    sm: `${tokens.spacing[4]} 0`,
    base: `${tokens.spacing[6]} 0`,
    lg: `${tokens.spacing[8]} 0`,
    xl: `${tokens.spacing[12]} 0`
  }

  const backgrounds = {
    transparent: 'transparent',
    white: tokens.colors.neutral[0],
    light: tokens.colors.neutral[50],
    dark: tokens.colors.neutral[800]
  }

  const sectionStyle = {
    padding: paddings[padding],
    backgroundColor: backgrounds[background] || background,
    fontFamily: tokens.typography.fontFamily.primary,
    ...style
  }

  return (
    <section style={sectionStyle} className={className} {...props}>
      {children}
    </section>
  )
}

// Divider Component
export const Divider = ({ 
  orientation = 'horizontal',
  color = 'light',
  thickness = 1,
  spacing = 'base',
  className,
  style = {},
  ...props 
}) => {
  const tokens = designTokens
  
  const colors = {
    light: tokens.colors.neutral[200],
    medium: tokens.colors.neutral[300],
    dark: tokens.colors.neutral[400]
  }

  const spacings = {
    none: '0px',
    sm: tokens.spacing[2],
    base: tokens.spacing[4],
    lg: tokens.spacing[6]
  }

  const dividerStyle = orientation === 'horizontal' ? {
    width: '100%',
    height: `${thickness}px`,
    backgroundColor: colors[color] || color,
    margin: `${spacings[spacing]} 0`,
    border: 'none',
    ...style
  } : {
    width: `${thickness}px`,
    height: '100%',
    backgroundColor: colors[color] || color,
    margin: `0 ${spacings[spacing]}`,
    border: 'none',
    ...style
  }

  return (
    <div style={dividerStyle} className={className} {...props} />
  )
}

export default { Container, Grid, Flex, Stack, Section, Divider }