# HalfApp Design System

## 🎨 Figma-Ready UI Component Library

This design system provides isolated, reusable components optimized for Figma integration and consistent UI development.

## 📁 File Structure

```
frontend/src/design/
├── index.js           # Main export file
├── tokens.js          # Design tokens and theme
├── Button.jsx         # Button components
├── Input.jsx          # Form input components
├── Card.jsx          # Card and container components
├── Table.jsx         # Table and data display components
├── Badge.jsx         # Badge and status components
└── Layout.jsx        # Layout and grid components
```

## 🚀 Quick Start

### Basic Import
```jsx
import { Button, Card, Input, Table } from '../design'

// Or import specific components
import { PrimaryButton, SecondaryButton } from '../design'
```

### Using Design Tokens
```jsx
import { designTokens } from '../design/tokens'

const customStyle = {
  color: designTokens.colors.primary[500],
  padding: designTokens.spacing[4],
  borderRadius: designTokens.borderRadius.base
}
```

## 🧩 Component Library

### 🔘 Buttons
Consistent, accessible buttons with multiple variants and sizes.

```jsx
// Basic usage
<Button variant="primary" size="base">Primary Button</Button>
<Button variant="secondary" size="lg">Secondary Button</Button>

// Quick variants
<PrimaryButton>Save</PrimaryButton>
<DangerButton>Delete</DangerButton>

// With loading state
<Button loading={isLoading}>Submit</Button>

// With icons
<Button icon="🔍">Search</Button>

// Full width
<Button fullWidth>Full Width Button</Button>
```

**Props:**
- `variant`: 'primary' | 'secondary' | 'success' | 'danger' | 'warning'
- `size`: 'xs' | 'sm' | 'base' | 'lg' | 'xl'
- `loading`: boolean
- `disabled`: boolean
- `fullWidth`: boolean
- `icon`: string | ReactNode

### 📝 Form Inputs
Modern, accessible form components with validation states.

```jsx
// Text input with label
<Input 
  label="Email Address" 
  type="email"
  required
  placeholder="Enter your email"
  value={email}
  onChange={(e) => setEmail(e.target.value)}
/>

// Input with error state
<Input 
  error={true}
  helperText="Please enter a valid email"
  value={email}
  onChange={handleChange}
/>

// Select dropdown
<Select
  label="User Role"
  options={[
    { value: 'admin', label: 'Administrator' },
    { value: 'user', label: 'User' }
  ]}
  value={selectedRole}
  onChange={(e) => setSelectedRole(e.target.value)}
/>
```

**Input Props:**
- `type`: Standard HTML input types
- `label`: string
- `error`: boolean
- `helperText`: string
- `required`: boolean
- `fullWidth`: boolean
- `icon`: ReactNode

### 🃏 Cards
Flexible containers for content organization.

```jsx
// Basic card
<Card>
  <CardHeader title="User Profile" subtitle="Manage your account" />
  <CardContent>
    <p>Card content goes here</p>
  </CardContent>
  <CardFooter>
    <Button variant="primary">Save</Button>
    <Button variant="secondary">Cancel</Button>
  </CardFooter>
</Card>

// Statistics card
<StatCard
  title="Total Users"
  value={1250}
  subtitle="Active this month"
  color="primary"
  icon="👥"
/>
```

**Card Props:**
- `padding`: 'none' | 'sm' | 'base' | 'lg' | 'xl'
- `shadow`: 'none' | 'sm' | 'base' | 'md' | 'lg' | 'xl'
- `border`: boolean

### 📊 Tables
Feature-rich data tables with sorting, filtering, and pagination.

```jsx
// Advanced table
<Table
  data={users}
  columns={[
    {
      key: 'name',
      title: 'Name',
      render: (value, row) => <strong>{value}</strong>
    },
    {
      key: 'email',
      title: 'Email'
    },
    {
      key: 'status',
      title: 'Status',
      render: (value) => <StatusBadge status={value} />
    }
  ]}
  sortable={true}
  filterable={true}
  pagination={true}
  pageSize={10}
/>

// Simple table
<SimpleTable
  headers={['Name', 'Email', 'Role']}
  data={[
    ['John Doe', 'john@example.com', 'Admin'],
    ['Jane Smith', 'jane@example.com', 'User']
  ]}
/>
```

**Table Props:**
- `data`: Array of objects
- `columns`: Array of column definitions
- `sortable`: boolean
- `filterable`: boolean
- `pagination`: boolean
- `pageSize`: number

### 🏷️ Badges
Status indicators and labels.

```jsx
// Basic badges
<Badge variant="primary">Primary</Badge>
<Badge variant="success">Success</Badge>
<Badge variant="danger">Danger</Badge>

// Status badges
<StatusBadge status="active" />
<StatusBadge status="inactive" />

// Role badges
<RoleBadge role="admin" />
<RoleBadge role="user" />
```

### 📐 Layout Components
Responsive layout utilities.

```jsx
// Container with max width
<Container maxWidth="lg">
  Content here
</Container>

// Responsive grid
<Grid responsive gap="base">
  <Card>Item 1</Card>
  <Card>Item 2</Card>
  <Card>Item 3</Card>
</Grid>

// Flexbox layouts
<Flex justify="space-between" align="center">
  <h1>Title</h1>
  <Button>Action</Button>
</Flex>

// Vertical stack
<Stack spacing="lg">
  <Input label="First Name" />
  <Input label="Last Name" />
  <Button>Submit</Button>
</Stack>
```

## 🎨 Design Tokens

### Colors
```jsx
designTokens.colors.primary[500]    // #007bff
designTokens.colors.success[500]    // #28a745
designTokens.colors.danger[500]     // #dc3545
designTokens.colors.neutral[800]    // #212529
```

### Spacing
```jsx
designTokens.spacing[1]  // 4px
designTokens.spacing[4]  // 16px
designTokens.spacing[8]  // 32px
```

### Typography
```jsx
designTokens.typography.fontSize.lg      // 18px
designTokens.typography.fontWeight.bold  // 700
designTokens.typography.fontFamily.primary
```

### Border Radius
```jsx
designTokens.borderRadius.sm    // 3px
designTokens.borderRadius.base  // 4px
designTokens.borderRadius.lg    // 8px
```

## 🔧 Figma Integration

### Component Naming Convention
- Use consistent naming: `Button/Primary`, `Card/Default`, `Input/Default`
- Maintain variant structure: `Component/Variant/Size`
- Include state variants: `Button/Primary/Default`, `Button/Primary/Hover`

### Design Token Mapping
```jsx
// Figma → Design System
Figma Color Styles → designTokens.colors
Figma Text Styles → designTokens.typography
Figma Effect Styles → designTokens.boxShadow
```

### Auto-Layout Friendly
All components are designed with Figma's Auto Layout in mind:
- Consistent padding and margins
- Flexible sizing options
- Proper component constraints

## 📱 Responsive Design

### Breakpoints
```jsx
designTokens.breakpoints.sm   // 640px
designTokens.breakpoints.md   // 768px
designTokens.breakpoints.lg   // 1024px
designTokens.breakpoints.xl   // 1280px
```

### Responsive Components
```jsx
// Auto-responsive grid
<Grid responsive minItemWidth="250px">
  {items.map(item => <Card key={item.id}>{item}</Card>)}
</Grid>

// Responsive container
<Container maxWidth="lg" padding="base">
  Content adapts to screen size
</Container>
```

## 🚀 Performance Optimizations

### Tree Shaking
Import only what you need:
```jsx
// ✅ Good - imports only Button component
import { Button } from '../design'

// ❌ Avoid - imports entire library
import * as DesignSystem from '../design'
```

### Component Lazy Loading
```jsx
// For large applications, consider lazy loading
const Table = React.lazy(() => import('../design/Table'))
```

## 🎯 Best Practices

### 1. Consistent Component Usage
```jsx
// ✅ Use design system components
<Button variant="primary">Submit</Button>

// ❌ Avoid custom styling
<button style={{backgroundColor: 'blue'}}>Submit</button>
```

### 2. Token-Based Styling
```jsx
// ✅ Use design tokens
const customStyle = {
  color: designTokens.colors.primary[500],
  padding: designTokens.spacing[4]
}

// ❌ Avoid magic numbers
const customStyle = {
  color: '#007bff',
  padding: '16px'
}
```

### 3. Semantic Component Names
```jsx
// ✅ Semantic usage
<PrimaryButton>Save Changes</PrimaryButton>
<DangerButton>Delete Account</DangerButton>

// ✅ Also good
<Button variant="primary">Save Changes</Button>
<Button variant="danger">Delete Account</Button>
```

## 🔄 Migration Guide

### From Inline Styles
```jsx
// Before
<button style={{
  backgroundColor: '#007bff',
  color: 'white',
  padding: '12px 16px',
  border: 'none',
  borderRadius: '4px'
}}>
  Submit
</button>

// After
<Button variant="primary">Submit</Button>
```

### From Custom Components
```jsx
// Before - Custom component
const CustomCard = ({children}) => (
  <div style={{
    backgroundColor: 'white',
    padding: '20px',
    borderRadius: '8px',
    boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
  }}>
    {children}
  </div>
)

// After - Design system
<Card padding="lg">
  {children}
</Card>
```

## 📈 Future Enhancements

### Planned Components
- [ ] Modal/Dialog components
- [ ] Toast/Notification system
- [ ] Form validation wrapper
- [ ] Data visualization components
- [ ] Navigation components

### Theming Support
- [ ] Dark mode theme
- [ ] Custom brand themes
- [ ] Theme provider context
- [ ] CSS custom properties integration

## 🤝 Contributing

When adding new components:

1. **Follow naming conventions**: Use PascalCase for components
2. **Include props documentation**: Add JSDoc comments
3. **Support design tokens**: Use tokens for all styling values
4. **Add variants**: Include size and variant props where appropriate
5. **Test responsiveness**: Ensure components work on all screen sizes
6. **Figma compatibility**: Design with Figma Auto Layout in mind

## 💡 Example Implementation

```jsx
// Real-world usage example
import React, { useState } from 'react'
import { 
  Container, 
  Card, 
  CardHeader, 
  CardContent,
  Button, 
  Input, 
  Table,
  StatusBadge,
  Grid,
  StatCard
} from '../design'

export function UserManagement() {
  const [users, setUsers] = useState([])
  const [filter, setFilter] = useState('')

  const columns = [
    { key: 'name', title: 'Name' },
    { key: 'email', title: 'Email' },
    { 
      key: 'status', 
      title: 'Status',
      render: (value) => <StatusBadge status={value} />
    }
  ]

  return (
    <Container maxWidth="xl">
      <Grid responsive gap="lg">
        <StatCard title="Total Users" value={users.length} color="primary" />
        <StatCard title="Active Users" value={42} color="success" />
      </Grid>
      
      <Card>
        <CardHeader title="User Management" />
        <CardContent>
          <Input 
            placeholder="Search users..."
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
          />
          
          <Table
            data={users}
            columns={columns}
            sortable
            filterable
            pagination
          />
        </CardContent>
      </Card>
    </Container>
  )
}
```

This design system ensures consistent, maintainable, and Figma-compatible UI components across your entire application. 🎉