// Design System - Figma-ready components export
// Centralized export for easy integration with Figma designs

// Design Tokens
export { designTokens, createComponentStyle } from './tokens'

// Core Components
export { default as Button, PrimaryButton, SecondaryButton, SuccessButton, DangerButton, WarningButton } from './Button'
export { default as Input, Select } from './Input'
export { default as Card, CardHeader, CardContent, CardFooter, StatCard } from './Card'
export { default as Table, SimpleTable } from './Table'
export { default as Badge, StatusBadge, RoleBadge } from './Badge'

// Layout Components
export { Container, Grid, Flex, Stack, Section, Divider } from './Layout'

// Component Groups for organized imports
export const Forms = {
  Input,
  Select,
  Button,
  PrimaryButton,
  SecondaryButton,
  SuccessButton,
  DangerButton,
  WarningButton
}

export const DataDisplay = {
  Table,
  SimpleTable,
  Card,
  CardHeader,
  CardContent,
  CardFooter,
  StatCard,
  Badge,
  StatusBadge,
  RoleBadge
}

export const Layout = {
  Container,
  Grid,
  Flex,
  Stack,
  Section,
  Divider
}

// Pre-configured component variants for common use cases
export const QuickComponents = {
  // Common button combinations
  ActionButtons: {
    Save: (props) => <Button variant="success" {...props}>Save</Button>,
    Cancel: (props) => <Button variant="secondary" {...props}>Cancel</Button>,
    Delete: (props) => <Button variant="danger" {...props}>Delete</Button>,
    Edit: (props) => <Button variant="primary" {...props}>Edit</Button>
  },
  
  // Common form layouts
  FormField: ({ label, error, children, ...props }) => (
    <Stack spacing="sm" {...props}>
      {label && <label style={{ fontWeight: '500', fontSize: '14px' }}>{label}</label>}
      {children}
      {error && <span style={{ color: designTokens.colors.danger[600], fontSize: '12px' }}>{error}</span>}
    </Stack>
  ),
  
  // Common card layouts
  DashboardCard: ({ title, value, subtitle, ...props }) => (
    <StatCard title={title} value={value} subtitle={subtitle} {...props} />
  ),
  
  // Common status displays
  UserStatus: ({ isActive, ...props }) => (
    <StatusBadge status={isActive} activeText="Active" inactiveText="Inactive" {...props} />
  ),
  
  DriverStatus: ({ isActive, ...props }) => (
    <StatusBadge status={isActive} activeText="Available" inactiveText="Offline" {...props} />
  )
}

// Theme presets for different UI modes
export const ThemePresets = {
  light: {
    ...designTokens,
    colors: {
      ...designTokens.colors,
      background: designTokens.colors.neutral[0],
      surface: designTokens.colors.neutral[50],
      text: designTokens.colors.neutral[800]
    }
  },
  
  dark: {
    ...designTokens,
    colors: {
      ...designTokens.colors,
      background: designTokens.colors.neutral[900],
      surface: designTokens.colors.neutral[800],
      text: designTokens.colors.neutral[100]
    }
  }
}