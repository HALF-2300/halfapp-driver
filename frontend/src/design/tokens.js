// Design Tokens - Centralized design system values
// Optimized for Figma integration and consistent theming

export const designTokens = {
  // Color Palette
  colors: {
    // Primary Colors
    primary: {
      50: '#e3f2fd',
      100: '#bbdefb',
      500: '#007bff',
      600: '#0056b3',
      700: '#004085',
      900: '#002752'
    },
    
    // Semantic Colors
    success: {
      50: '#d4edda',
      100: '#c3e6cb',
      500: '#28a745',
      600: '#1e7e34',
      700: '#155724'
    },
    
    warning: {
      50: '#fff3cd',
      100: '#ffeaa7',
      500: '#fd7e14',
      600: '#e55100',
      700: '#d84315'
    },
    
    danger: {
      50: '#f8d7da',
      100: '#f5c6cb',
      500: '#dc3545',
      600: '#c82333',
      700: '#721c24'
    },
    
    // Neutral Colors
    neutral: {
      0: '#ffffff',
      50: '#f8f9fa',
      100: '#f1f3f4',
      200: '#e9ecef',
      300: '#dee2e6',
      400: '#ced4da',
      500: '#6c757d',
      600: '#495057',
      700: '#343a40',
      800: '#212529',
      900: '#000000'
    }
  },

  // Typography
  typography: {
    fontFamily: {
      primary: 'system-ui, -apple-system, sans-serif',
      monospace: '"SF Mono", Monaco, "Cascadia Code", "Roboto Mono", Consolas, "Courier New", monospace'
    },
    
    fontSize: {
      xs: '12px',
      sm: '14px',
      base: '16px',
      lg: '18px',
      xl: '20px',
      '2xl': '24px',
      '3xl': '28px',
      '4xl': '32px',
      '5xl': '36px'
    },
    
    fontWeight: {
      normal: '400',
      medium: '500',
      semibold: '600',
      bold: '700'
    },
    
    lineHeight: {
      tight: '1.2',
      normal: '1.5',
      relaxed: '1.75'
    }
  },

  // Spacing Scale
  spacing: {
    0: '0px',
    1: '4px',
    2: '8px',
    3: '12px',
    4: '16px',
    5: '20px',
    6: '24px',
    8: '32px',
    10: '40px',
    12: '48px',
    16: '64px',
    20: '80px'
  },

  // Border Radius
  borderRadius: {
    none: '0px',
    sm: '3px',
    base: '4px',
    md: '6px',
    lg: '8px',
    xl: '12px',
    full: '9999px'
  },

  // Shadows
  boxShadow: {
    none: 'none',
    sm: '0 1px 2px rgba(0, 0, 0, 0.05)',
    base: '0 1px 3px rgba(0, 0, 0, 0.1)',
    md: '0 2px 4px rgba(0, 0, 0, 0.1)',
    lg: '0 4px 6px rgba(0, 0, 0, 0.1)',
    xl: '0 10px 15px rgba(0, 0, 0, 0.1)'
  },

  // Component Sizes
  size: {
    xs: {
      padding: '6px 12px',
      fontSize: '12px',
      height: '28px'
    },
    sm: {
      padding: '8px 16px',
      fontSize: '14px',
      height: '32px'
    },
    base: {
      padding: '12px 16px',
      fontSize: '16px',
      height: '40px'
    },
    lg: {
      padding: '12px 24px',
      fontSize: '18px',
      height: '48px'
    },
    xl: {
      padding: '16px 32px',
      fontSize: '20px',
      height: '56px'
    }
  },

  // Animation & Transitions
  animation: {
    duration: {
      fast: '150ms',
      normal: '200ms',
      slow: '300ms'
    },
    easing: {
      easeOut: 'cubic-bezier(0.25, 0.46, 0.45, 0.94)',
      easeIn: 'cubic-bezier(0.55, 0.085, 0.68, 0.53)',
      easeInOut: 'cubic-bezier(0.445, 0.05, 0.55, 0.95)'
    }
  },

  // Breakpoints for responsive design
  breakpoints: {
    sm: '640px',
    md: '768px',
    lg: '1024px',
    xl: '1280px'
  }
}

// Helper function to create consistent component styles
export const createComponentStyle = (variant, size = 'base') => {
  const tokens = designTokens
  
  const baseStyles = {
    fontFamily: tokens.typography.fontFamily.primary,
    fontSize: tokens.size[size].fontSize,
    padding: tokens.size[size].padding,
    borderRadius: tokens.borderRadius.base,
    transition: `all ${tokens.animation.duration.normal} ${tokens.animation.easing.easeOut}`,
    border: 'none',
    cursor: 'pointer',
    fontWeight: tokens.typography.fontWeight.medium,
    boxSizing: 'border-box'
  }

  const variants = {
    primary: {
      backgroundColor: tokens.colors.primary[500],
      color: tokens.colors.neutral[0],
      ':hover': {
        backgroundColor: tokens.colors.primary[600]
      }
    },
    secondary: {
      backgroundColor: tokens.colors.neutral[100],
      color: tokens.colors.neutral[700],
      border: `1px solid ${tokens.colors.neutral[300]}`,
      ':hover': {
        backgroundColor: tokens.colors.neutral[200]
      }
    },
    success: {
      backgroundColor: tokens.colors.success[500],
      color: tokens.colors.neutral[0],
      ':hover': {
        backgroundColor: tokens.colors.success[600]
      }
    },
    danger: {
      backgroundColor: tokens.colors.danger[500],
      color: tokens.colors.neutral[0],
      ':hover': {
        backgroundColor: tokens.colors.danger[600]
      }
    },
    warning: {
      backgroundColor: tokens.colors.warning[500],
      color: tokens.colors.neutral[0],
      ':hover': {
        backgroundColor: tokens.colors.warning[600]
      }
    }
  }

  return {
    ...baseStyles,
    ...variants[variant]
  }
}

export default designTokens