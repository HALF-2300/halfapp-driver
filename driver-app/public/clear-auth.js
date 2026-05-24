// Clear all authentication data from localStorage
// Run this in browser console if you need to reset the app completely

function clearAuthData() {
  console.log('Clearing all authentication data...')
  
  // Remove driver auth tokens
  localStorage.removeItem('driver_token')
  localStorage.removeItem('driver_role')
  localStorage.removeItem('authToken')
  
  // Clear driver database (if needed for testing)
  // localStorage.removeItem('halfapp_driver_database')
  
  console.log('Authentication data cleared!')
  console.log('Please refresh the page to start fresh.')
}

// Auto-run on script load
clearAuthData()