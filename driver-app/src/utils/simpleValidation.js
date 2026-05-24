// Simple validation utilities without complex imports
export const validateEmail = (email) => {
  if (!email || typeof email !== 'string') {
    return { valid: false, error: 'Email is required' }
  }

  const emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/
  
  if (!emailRegex.test(email)) {
    return { valid: false, error: 'Please enter a valid email address' }
  }

  return { valid: true, value: email.toLowerCase().trim() }
}

export const validatePassword = (password, isRegistration = false) => {
  if (!password || typeof password !== 'string') {
    return { valid: false, error: 'Password is required' }
  }

  if (password.length < 6) {
    return { valid: false, error: 'Password must be at least 6 characters long' }
  }

  if (isRegistration) {
    const hasLetter = /[a-zA-Z]/.test(password)
    const hasNumber = /[0-9]/.test(password)
    
    if (!hasLetter || !hasNumber) {
      return { valid: false, error: 'Password must contain both letters and numbers' }
    }
  }

  return { valid: true, value: password }
}

export const validateName = (name) => {
  if (!name || typeof name !== 'string') {
    return { valid: false, error: 'Full name is required' }
  }

  const trimmedName = name.trim()
  
  if (trimmedName.length < 2) {
    return { valid: false, error: 'Name must be at least 2 characters long' }
  }

  if (trimmedName.length > 100) {
    return { valid: false, error: 'Name is too long (max 100 characters)' }
  }

  return { valid: true, value: trimmedName }
}

export const validateDriverAccess = (userData) => {
  if (!userData || typeof userData !== 'object') {
    return { valid: false, error: 'Invalid user data' }
  }

  if (userData.role !== 'driver') {
    return { 
      valid: false, 
      error: `Access denied: This is a driver-only application. ${userData.role || 'Unknown'} accounts cannot access this app.`
    }
  }

  return { valid: true, value: userData }
}

// Form validation helper
export const validateLoginForm = (email, password) => {
  const errors = {}
  
  const emailResult = validateEmail(email)
  if (!emailResult.valid) {
    errors.email = emailResult.error
  }

  const passwordResult = validatePassword(password)
  if (!passwordResult.valid) {
    errors.password = passwordResult.error
  }

  return {
    valid: Object.keys(errors).length === 0,
    errors,
    values: {
      email: emailResult.valid ? emailResult.value : email,
      password: passwordResult.valid ? passwordResult.value : password
    }
  }
}

export const validateRegistrationForm = (formData) => {
  const errors = {}
  
  const emailResult = validateEmail(formData.email)
  if (!emailResult.valid) {
    errors.email = emailResult.error
  }

  const passwordResult = validatePassword(formData.password, true)
  if (!passwordResult.valid) {
    errors.password = passwordResult.error
  }

  const nameResult = validateName(formData.name)
  if (!nameResult.valid) {
    errors.name = nameResult.error
  }

  return {
    valid: Object.keys(errors).length === 0,
    errors,
    values: {
      email: emailResult.valid ? emailResult.value : formData.email,
      password: passwordResult.valid ? passwordResult.value : formData.password,
      name: nameResult.valid ? nameResult.value : formData.name,
      role: 'driver' // Force driver role
    }
  }
}