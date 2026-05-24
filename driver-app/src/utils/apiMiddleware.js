// API Middleware for data verification and processing
import dataValidationMiddleware, { ValidationError } from './validation.js'

// Response interceptor for data verification
export class APIMiddleware {
  constructor(apiClient) {
    this.api = apiClient
    this.setupInterceptors()
  }

  setupInterceptors() {
    // Store original methods
    this.originalLogin = this.api.login.bind(this.api)
    this.originalRegister = this.api.register.bind(this.api)
    this.originalUpdateProfile = this.api.updateProfile.bind(this.api)

    // Override with middleware
    this.api.login = this.enhancedLogin.bind(this)
    this.api.register = this.enhancedRegister.bind(this)
    this.api.updateProfile = this.enhancedUpdateProfile.bind(this)
  }

  // Enhanced login with validation
  async enhancedLogin(email, password) {
    try {
      console.log('🔍 Validating login data...')
      
      // Pre-request validation
      const validatedCredentials = dataValidationMiddleware.validateRequest(
        { email, password },
        'login'
      )

      console.log('✅ Login data validated successfully')
      
      // Call original login
      const response = await this.originalLogin(
        validatedCredentials.email,
        validatedCredentials.password
      )

      console.log('🔍 Validating login response...')
      
      // Post-response validation
      const validatedResponse = dataValidationMiddleware.validateResponse(response, 'user')

      // Additional driver-specific checks
      if (!validatedResponse.access_token) {
        throw new ValidationError('Invalid response: Missing access token', null, 'MISSING_TOKEN')
      }

      console.log('✅ Login response validated successfully')
      
      return validatedResponse
    } catch (error) {
      console.error('❌ Login validation failed:', error.message)
      
      // Re-throw validation errors as-is
      if (error instanceof ValidationError) {
        throw error
      }
      
      // Wrap other errors
      throw new ValidationError(
        `Login failed: ${error.message}`,
        null,
        'LOGIN_FAILED'
      )
    }
  }

  // Enhanced registration with validation
  async enhancedRegister(userData) {
    try {
      console.log('🔍 Validating registration data...')
      
      // Pre-request validation and sanitization
      const sanitizedData = dataValidationMiddleware.sanitizeInputs(userData)
      const validatedData = dataValidationMiddleware.validateRequest(sanitizedData, 'registration')

      console.log('✅ Registration data validated successfully')

      // Call original register
      const response = await this.originalRegister(validatedData)

      console.log('🔍 Validating registration response...')
      
      // Post-response validation
      const validatedResponse = dataValidationMiddleware.validateResponse(response, 'user')

      // Additional checks for registration response
      if (!validatedResponse.access_token) {
        throw new ValidationError('Invalid response: Missing access token', null, 'MISSING_TOKEN')
      }

      if (validatedResponse.email !== validatedData.email) {
        throw new ValidationError('Response email mismatch', null, 'EMAIL_MISMATCH')
      }

      console.log('✅ Registration response validated successfully')
      
      return validatedResponse
    } catch (error) {
      console.error('❌ Registration validation failed:', error.message)
      
      // Re-throw validation errors as-is
      if (error instanceof ValidationError) {
        throw error
      }
      
      // Wrap other errors
      throw new ValidationError(
        `Registration failed: ${error.message}`,
        null,
        'REGISTRATION_FAILED'
      )
    }
  }

  // Enhanced profile update with validation
  async enhancedUpdateProfile(profileData) {
    try {
      console.log('🔍 Validating profile data...')
      
      // Pre-request validation and sanitization
      const sanitizedData = dataValidationMiddleware.sanitizeInputs(profileData)
      
      // Validate vehicle data if present
      if (sanitizedData.vehicle_make || sanitizedData.vehicle_model || sanitizedData.vehicle_year) {
        dataValidationMiddleware.validateRequest(sanitizedData, 'vehicle')
      }

      console.log('✅ Profile data validated successfully')

      // Call original update
      const response = await this.originalUpdateProfile(sanitizedData)

      console.log('🔍 Validating profile update response...')
      
      // Post-response validation
      const validatedResponse = dataValidationMiddleware.validateResponse(response)

      console.log('✅ Profile update response validated successfully')
      
      return validatedResponse
    } catch (error) {
      console.error('❌ Profile update validation failed:', error.message)
      
      // Re-throw validation errors as-is
      if (error instanceof ValidationError) {
        throw error
      }
      
      // Wrap other errors
      throw new ValidationError(
        `Profile update failed: ${error.message}`,
        null,
        'UPDATE_FAILED'
      )
    }
  }

  // General API call interceptor
  async interceptApiCall(method, endpoint, data = null) {
    try {
      console.log(`🔍 Intercepting API call: ${method} ${endpoint}`)
      
      // Sanitize input data if present
      const sanitizedData = data ? dataValidationMiddleware.sanitizeInputs(data) : null
      
      // Make the call (this would be implemented based on your API structure)
      const response = await this.api.call(endpoint, {
        method,
        body: sanitizedData ? JSON.stringify(sanitizedData) : undefined
      })

      // Validate response
      const validatedResponse = dataValidationMiddleware.validateResponse(response)
      
      console.log(`✅ API call validated: ${method} ${endpoint}`)
      
      return validatedResponse
    } catch (error) {
      console.error(`❌ API call validation failed: ${method} ${endpoint}`, error.message)
      throw error
    }
  }
}

// Error handler for validation errors
export const handleValidationError = (error) => {
  if (error instanceof ValidationError) {
    // Handle validation-specific errors
    const errorInfo = {
      message: error.message,
      field: error.field,
      code: error.code,
      type: 'validation'
    }

    // If there are multiple validation errors
    if (error.validationErrors) {
      errorInfo.validationErrors = error.validationErrors
      errorInfo.message = 'Please fix the following errors:'
    }

    return errorInfo
  }

  // Handle other errors
  return {
    message: error.message || 'An unexpected error occurred',
    type: 'general',
    code: 'UNKNOWN_ERROR'
  }
}

// Create middleware factory
export const createAPIMiddleware = (apiClient) => {
  return new APIMiddleware(apiClient)
}

export default APIMiddleware