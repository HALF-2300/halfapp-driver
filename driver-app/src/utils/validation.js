// Data Validation Middleware for Driver App
// Provides comprehensive validation for user inputs, API responses, and data integrity

class ValidationError extends Error {
  constructor(message, field = null, code = null) {
    super(message)
    this.name = 'ValidationError'
    this.field = field
    this.code = code
  }
}

// Email validation
export const validateEmail = (email) => {
  if (!email || typeof email !== 'string') {
    throw new ValidationError('Email is required', 'email', 'REQUIRED')
  }

  const emailRegex = /^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$/
  
  if (!emailRegex.test(email)) {
    throw new ValidationError('Please enter a valid email address', 'email', 'INVALID_FORMAT')
  }

  if (email.length > 254) {
    throw new ValidationError('Email address is too long', 'email', 'TOO_LONG')
  }

  return email.toLowerCase().trim()
}

// Password validation
export const validatePassword = (password, isRegistration = false) => {
  if (!password || typeof password !== 'string') {
    throw new ValidationError('Password is required', 'password', 'REQUIRED')
  }

  if (password.length < 6) {
    throw new ValidationError('Password must be at least 6 characters long', 'password', 'TOO_SHORT')
  }

  if (password.length > 128) {
    throw new ValidationError('Password is too long (max 128 characters)', 'password', 'TOO_LONG')
  }

  if (isRegistration) {
    // Additional validation for registration
    const hasLetter = /[a-zA-Z]/.test(password)
    const hasNumber = /[0-9]/.test(password)
    
    if (!hasLetter || !hasNumber) {
      throw new ValidationError('Password must contain both letters and numbers', 'password', 'WEAK_PASSWORD')
    }

    // Check for common weak passwords
    const weakPasswords = ['123456', 'password', '123456789', '12345678', 'qwerty', 'abc123']
    if (weakPasswords.includes(password.toLowerCase())) {
      throw new ValidationError('Please choose a stronger password', 'password', 'WEAK_PASSWORD')
    }
  }

  return password
}

// Name validation
export const validateName = (name) => {
  if (!name || typeof name !== 'string') {
    throw new ValidationError('Full name is required', 'name', 'REQUIRED')
  }

  const trimmedName = name.trim()
  
  if (trimmedName.length < 2) {
    throw new ValidationError('Name must be at least 2 characters long', 'name', 'TOO_SHORT')
  }

  if (trimmedName.length > 100) {
    throw new ValidationError('Name is too long (max 100 characters)', 'name', 'TOO_LONG')
  }

  // Check for valid name characters (letters, spaces, hyphens, apostrophes)
  const nameRegex = /^[a-zA-Z\s\-'\.]+$/
  if (!nameRegex.test(trimmedName)) {
    throw new ValidationError('Name can only contain letters, spaces, hyphens, and apostrophes', 'name', 'INVALID_CHARACTERS')
  }

  // Check for at least one letter
  if (!/[a-zA-Z]/.test(trimmedName)) {
    throw new ValidationError('Name must contain at least one letter', 'name', 'INVALID_FORMAT')
  }

  return trimmedName
}

// Phone number validation
export const validatePhone = (phone) => {
  if (!phone) return null // Phone is optional

  if (typeof phone !== 'string') {
    throw new ValidationError('Phone number must be a string', 'phone', 'INVALID_TYPE')
  }

  // Remove all non-digit characters for validation
  const digitsOnly = phone.replace(/\D/g, '')
  
  if (digitsOnly.length < 10 || digitsOnly.length > 15) {
    throw new ValidationError('Phone number must be between 10-15 digits', 'phone', 'INVALID_LENGTH')
  }

  return phone.trim()
}

// Vehicle validation
export const validateVehicle = (vehicleData) => {
  const errors = {}

  if (vehicleData.make && vehicleData.make.length > 50) {
    errors.vehicle_make = 'Vehicle make is too long (max 50 characters)'
  }

  if (vehicleData.model && vehicleData.model.length > 50) {
    errors.vehicle_model = 'Vehicle model is too long (max 50 characters)'
  }

  if (vehicleData.year) {
    const year = parseInt(vehicleData.year)
    const currentYear = new Date().getFullYear()
    if (isNaN(year) || year < 1990 || year > currentYear + 1) {
      errors.vehicle_year = `Vehicle year must be between 1990 and ${currentYear + 1}`
    }
  }

  if (vehicleData.license_plate && vehicleData.license_plate.length > 20) {
    errors.license_plate = 'License plate is too long (max 20 characters)'
  }

  if (Object.keys(errors).length > 0) {
    throw new ValidationError('Vehicle validation failed', null, 'VALIDATION_FAILED', errors)
  }

  return vehicleData
}

// User role validation
export const validateUserRole = (userData) => {
  if (!userData || typeof userData !== 'object') {
    throw new ValidationError('Invalid user data', null, 'INVALID_DATA')
  }

  if (userData.role !== 'driver') {
    throw new ValidationError(
      `Access denied: This is a driver-only application. ${userData.role || 'Unknown'} accounts cannot access this app.`,
      'role',
      'ACCESS_DENIED'
    )
  }

  return userData
}

// Registration data validation
export const validateRegistrationData = (userData) => {
  const errors = {}

  try {
    validateEmail(userData.email)
  } catch (err) {
    errors.email = err.message
  }

  try {
    validatePassword(userData.password, true)
  } catch (err) {
    errors.password = err.message
  }

  try {
    validateName(userData.name)
  } catch (err) {
    errors.name = err.message
  }

  if (!userData.license_no || typeof userData.license_no !== 'string' || userData.license_no.trim().length < 5) {
    errors.license_no = "Driver's license number is required (at least 5 characters)"
  }

  try {
    validatePhone(userData.phone)
  } catch (err) {
    errors.phone = err.message
  }

  // Ensure role is driver
  if (userData.role && userData.role !== 'driver') {
    errors.role = 'Only driver registrations are allowed in this app'
  }

  if (Object.keys(errors).length > 0) {
    const error = new ValidationError('Registration validation failed')
    error.validationErrors = errors
    throw error
  }

  return {
    email: validateEmail(userData.email),
    password: validatePassword(userData.password, true),
    name: validateName(userData.name),
    license_no: userData.license_no.trim(),
    phone: validatePhone(userData.phone),
    role: 'driver'
  }
}

// Login data validation
export const validateLoginData = (credentials) => {
  const errors = {}

  try {
    validateEmail(credentials.email)
  } catch (err) {
    errors.email = err.message
  }

  try {
    validatePassword(credentials.password)
  } catch (err) {
    errors.password = err.message
  }

  if (Object.keys(errors).length > 0) {
    const error = new ValidationError('Login validation failed')
    error.validationErrors = errors
    throw error
  }

  return {
    email: validateEmail(credentials.email),
    password: validatePassword(credentials.password)
  }
}

// API response validation
export const validateApiResponse = (response, expectedShape = {}) => {
  if (!response || typeof response !== 'object') {
    throw new ValidationError('Invalid API response format', null, 'INVALID_RESPONSE')
  }

  // Check for error responses
  if (response.error) {
    throw new ValidationError(response.error.message || 'API Error', null, response.error.code || 'API_ERROR')
  }

  // Validate user role in responses
  if (response.role && response.role !== 'driver') {
    throw new ValidationError(
      `Access denied: Expected driver role, got ${response.role}`,
      'role',
      'ROLE_MISMATCH'
    )
  }

  return response
}

// Sanitize user input (prevent XSS)
export const sanitizeInput = (input) => {
  if (typeof input !== 'string') return input

  return input
    .replace(/[<>]/g, '') // Remove basic HTML tags
    .trim() // Remove leading/trailing whitespace
    .slice(0, 1000) // Limit length to prevent DoS
}

// Data validation middleware
export const dataValidationMiddleware = {
  // Pre-request validation
  validateRequest: (data, validationType) => {
    switch (validationType) {
      case 'login':
        return validateLoginData(data)
      case 'registration':
        return validateRegistrationData(data)
      case 'vehicle':
        return validateVehicle(data)
      default:
        return data
    }
  },

  // Post-response validation
  validateResponse: (response, expectedType) => {
    const validated = validateApiResponse(response)
    
    if (expectedType === 'user') {
      return validateUserRole(validated)
    }
    
    return validated
  },

  // Input sanitization
  sanitizeInputs: (data) => {
    if (typeof data !== 'object' || data === null) return data
    
    const sanitized = {}
    for (const [key, value] of Object.entries(data)) {
      sanitized[key] = sanitizeInput(value)
    }
    return sanitized
  }
}

export { ValidationError }
export default dataValidationMiddleware