import React, { useState, useEffect } from 'react'
import StabilityDashboard from './StabilityDashboard'
import { 
  Card, 
  StatCard, 
  Table, 
  Button, 
  Select, 
  StatusBadge, 
  RoleBadge,
  Grid,
  Flex,
  Container
} from '../design/index.jsx'

export default function AdminDashboard({ apiBase }) {
  const [users, setUsers] = useState([])
  const [drivers, setDrivers] = useState([])
  const [rides, setRides] = useState([])
  const [activeTab, setActiveTab] = useState('overview')
  const [apiEndpoints, setApiEndpoints] = useState([])
  // const [invites, setInvites] = useState([])  // Temporarily disabled
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const fetchData = async () => {
    setLoading(true)
    try {
      const token = localStorage.getItem('token')
      const headers = { Authorization: `Bearer ${token}` }
      
      const [usersRes, driversRes, ridesRes, apiDocsRes] = await Promise.all([
        fetch(`${apiBase}/admin/users`, { headers }),
        fetch(`${apiBase}/admin/drivers`, { headers }),
        fetch(`${apiBase}/admin/rides`, { headers }),
        fetch(`${apiBase}/openapi.json`)
      ])
      
      if (usersRes.ok) setUsers(await usersRes.json())
      if (driversRes.ok) setDrivers(await driversRes.json())
      if (ridesRes.ok) setRides(await ridesRes.json())
      if (apiDocsRes.ok) {
        const apiData = await apiDocsRes.json()
        const endpoints = Object.entries(apiData.paths).map(([path, methods]) => ({
          path,
          methods: Object.keys(methods),
          ...methods
        }))
        setApiEndpoints(endpoints)
      }
    } catch (err) {
      setError('Failed to fetch admin data')
    } finally {
      setLoading(false)
    }
  }

  const toggleUserActive = async (userId) => {
    try {
      const token = localStorage.getItem('token')
      const res = await fetch(`${apiBase}/admin/users/${userId}/toggle-active`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` }
      })
      
      if (res.ok) {
        await fetchData()
      } else {
        const error = await res.json()
        setError(error.detail || 'Failed to toggle user status')
      }
    } catch (err) {
      setError('Failed to toggle user status')
    }
  }

  const createInvite = async (description = '') => {
    try {
      const token = localStorage.getItem('token')
      const res = await fetch(`${apiBase}/admin-invites/create`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ description })
      })
      
      if (res.ok) {
        await fetchData()
        return await res.json()
      } else {
        const error = await res.json()
        setError(error.detail?.message || 'Failed to create invite')
      }
    } catch (err) {
      setError('Failed to create invite')
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  // Calculate metrics
  const metrics = {
    totalUsers: users.length,
    activeUsers: users.filter(u => u.is_active === 'true').length,
    totalDrivers: drivers.length,
    activeDrivers: drivers.filter(d => d.is_active === 'true').length,
    totalRides: rides.length,
    completedRides: rides.filter(r => r.status === 'completed').length,
    pendingRides: rides.filter(r => r.status === 'requested').length,
    acceptedRides: rides.filter(r => r.status === 'accepted').length,
    customers: users.filter(u => u.role === 'customer').length,
    admins: users.filter(u => u.role === 'admin').length
  }

  const cardStyle = {
    background: 'white',
    borderRadius: '8px',
    padding: '24px',
    margin: '12px',
    boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
    border: '1px solid #e1e5e9'
  }

  const containerStyle = {
    background: '#f8f9fa',
    minHeight: '100vh',
    padding: '20px'
  }

  const headerStyle = {
    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    color: 'white',
    padding: '30px',
    borderRadius: '12px',
    marginBottom: '30px',
    textAlign: 'center'
  }

  const tabButtonStyle = (tab) => ({
    padding: '12px 24px',
    margin: '0 8px',
    border: 'none',
    background: activeTab === tab ? '#007bff' : 'white',
    color: activeTab === tab ? 'white' : '#495057',
    cursor: 'pointer',
    borderRadius: '8px',
    fontWeight: '500',
    boxShadow: activeTab === tab ? '0 4px 12px rgba(0,123,255,0.3)' : '0 2px 4px rgba(0,0,0,0.1)',
    transition: 'all 0.2s ease'
  })

  const metricCardStyle = {
    ...cardStyle,
    textAlign: 'center',
    minWidth: '200px',
    flex: '1'
  }

  const MetricCard = ({ title, value, subtitle, color = '#007bff', icon }) => (
    <div style={metricCardStyle}>
      <div style={{ fontSize: '14px', color: '#6c757d', marginBottom: '8px' }}>{icon} {title}</div>
      <div style={{ fontSize: '36px', fontWeight: 'bold', color: color, marginBottom: '4px' }}>{value}</div>
      {subtitle && <div style={{ fontSize: '12px', color: '#6c757d' }}>{subtitle}</div>}
    </div>
  )

  const OverviewTab = () => (
    <div>
      <h3 style={{ marginBottom: '24px', color: '#495057' }}>Platform Overview & Key Metrics</h3>
      <p style={{ marginBottom: '30px', color: '#6c757d' }}>
        Comprehensive summary of user activity, ride statistics, and platform performance for administrative reporting and decision making.
      </p>
      
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '16px', marginBottom: '30px' }}>
        <MetricCard 
          title="Total Users" 
          value={metrics.totalUsers} 
          subtitle={`${metrics.activeUsers} active users`}
          color="#28a745"
          icon="👥"
        />
        <MetricCard 
          title="Active Drivers" 
          value={metrics.activeDrivers} 
          subtitle={`of ${metrics.totalDrivers} total drivers`}
          color="#fd7e14"
          icon="🚗"
        />
        <MetricCard 
          title="Total Rides" 
          value={metrics.totalRides} 
          subtitle={`${metrics.completedRides} completed`}
          color="#6f42c1"
          icon="🛣️"
        />
        <MetricCard 
          title="Pending Requests" 
          value={metrics.pendingRides} 
          subtitle={`${metrics.acceptedRides} in progress`}
          color="#ffc107"
          icon="⏳"
        />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '20px' }}>
        <div style={cardStyle}>
          <h4 style={{ color: '#495057', marginBottom: '16px' }}>📊 User Distribution</h4>
          <div style={{ marginBottom: '12px' }}>
            <strong>Customers:</strong> {metrics.customers} users
          </div>
          <div style={{ marginBottom: '12px' }}>
            <strong>Drivers:</strong> {metrics.totalDrivers} users
          </div>
          <div style={{ marginBottom: '12px' }}>
            <strong>Administrators:</strong> {metrics.admins} users
          </div>
        </div>

        <div style={cardStyle}>
          <h4 style={{ color: '#495057', marginBottom: '16px' }}>🎯 Platform Health</h4>
          <div style={{ marginBottom: '12px' }}>
            <strong>User Activity Rate:</strong> {metrics.totalUsers > 0 ? Math.round((metrics.activeUsers / metrics.totalUsers) * 100) : 0}%
          </div>
          <div style={{ marginBottom: '12px' }}>
            <strong>Driver Availability:</strong> {metrics.totalDrivers > 0 ? Math.round((metrics.activeDrivers / metrics.totalDrivers) * 100) : 0}%
          </div>
          <div style={{ marginBottom: '12px' }}>
            <strong>Ride Completion Rate:</strong> {metrics.totalRides > 0 ? Math.round((metrics.completedRides / metrics.totalRides) * 100) : 0}%
          </div>
        </div>
      </div>
    </div>
  )

  const UsersTab = () => {
    const [userFilter, setUserFilter] = useState('all')
    const getUserCount = (role) => users.filter(u => u.role === role).length
    const filteredUsers = users.filter(user => {
      if (userFilter === 'all') return true
      return user.role === userFilter
    })

    // Define table columns using the new design system
    const columns = [
      {
        key: 'name',
        title: '👤 Name',
        render: (value, user) => (
          <div>
            <div style={{ fontWeight: '600' }}>{user.name}</div>
            <div style={{ fontSize: '12px', color: '#6c757d' }}>ID: {user.id}</div>
          </div>
        )
      },
      {
        key: 'email',
        title: '📧 Email',
        render: (value) => <div style={{ color: '#495057' }}>{value}</div>
      },
      {
        key: 'role',
        title: '🏷️ Role',
        render: (value) => <RoleBadge role={value} />
      },
      {
        key: 'created_at',
        title: '📅 Joined',
        render: (value) => (
          <div>
            <div>{new Date(value).toLocaleDateString()}</div>
            <div style={{ fontSize: '12px', color: '#6c757d' }}>
              {new Date(value).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            </div>
          </div>
        )
      },
      {
        key: 'license_no',
        title: '🪪 License',
        render: (value) => value ? (
          <span style={{ 
            fontFamily: 'monospace', 
            backgroundColor: '#f8f9fa', 
            padding: '4px 8px', 
            borderRadius: '4px',
            fontSize: '12px',
            fontWeight: '600'
          }}>
            {value}
          </span>
        ) : (
          <span style={{ color: '#6c757d', fontSize: '12px' }}>N/A</span>
        )
      },
      {
        key: 'is_active',
        title: '📊 Status',
        render: (value) => <StatusBadge status={value} />
      },
      {
        key: 'actions',
        title: '⚙️ Actions',
        render: (_, user) => (
          <Button
            variant={user.is_active === 'true' ? 'danger' : 'success'}
            size="sm"
            onClick={() => toggleUserActive(user.id)}
          >
            {user.is_active === 'true' ? 'Deactivate' : 'Activate'}
          </Button>
        )
      }
    ]

    return (
      <Container>
        <h3 style={{ marginBottom: '16px', color: '#495057' }}>User Management</h3>
        
        {/* User Statistics */}
        <Grid responsive gap="base" style={{ marginBottom: '24px' }}>
          <StatCard
            title="Total Users"
            value={users.length}
            color="primary"
          />
          <StatCard
            title="Customers"
            value={getUserCount('customer')}
            color="success"
          />
          <StatCard
            title="Drivers"
            value={getUserCount('driver')}
            color="warning"
          />
          <StatCard
            title="Admins"
            value={getUserCount('admin')}
            color="danger"
          />
        </Grid>

        {/* Filters and Controls */}
        <Flex gap="base" align="center" style={{ marginBottom: '20px', flexWrap: 'wrap' }}>
          <Select
            value={userFilter}
            onChange={(e) => setUserFilter(e.target.value)}
            options={[
              { value: 'all', label: `All Users (${users.length})` },
              { value: 'customer', label: `Customers (${getUserCount('customer')})` },
              { value: 'driver', label: `Drivers (${getUserCount('driver')})` },
              { value: 'admin', label: `Admins (${getUserCount('admin')})` }
            ]}
            label="Filter by type"
            size="sm"
          />
        </Flex>

        {/* Users Table */}
        <Card padding="none">
          <Table
            data={filteredUsers}
            columns={columns}
            sortable={true}
            filterable={true}
            pagination={true}
            pageSize={10}
          />
        </Card>
      </Container>
    )
  }

  const DriversTab = () => {
    const [driverSortBy, setDriverSortBy] = useState('created_at')
    const [driverSortOrder, setDriverSortOrder] = useState('desc')
    const [statusFilter, setStatusFilter] = useState('all')

    const filteredDrivers = drivers.filter(driver => {
      if (statusFilter === 'all') return true
      if (statusFilter === 'active') return driver.is_active === 'true'
      if (statusFilter === 'inactive') return driver.is_active !== 'true'
      return true
    })

    const sortedDrivers = [...filteredDrivers].sort((a, b) => {
      let aVal, bVal
      
      if (driverSortBy === 'created_at') {
        aVal = new Date(a.created_at).getTime()
        bVal = new Date(b.created_at).getTime()
      } else if (driverSortBy === 'name') {
        aVal = a.name.toLowerCase()
        bVal = b.name.toLowerCase()
      } else if (driverSortBy === 'email') {
        aVal = a.email.toLowerCase()
        bVal = b.email.toLowerCase()
      } else if (driverSortBy === 'license_no') {
        aVal = a.license_no || ''
        bVal = b.license_no || ''
      }
      
      if (driverSortOrder === 'asc') {
        return aVal > bVal ? 1 : -1
      } else {
        return aVal < bVal ? 1 : -1
      }
    })

    const activeDrivers = drivers.filter(d => d.is_active === 'true').length
    const inactiveDrivers = drivers.filter(d => d.is_active !== 'true').length

    const tableStyle = {
      width: '100%',
      borderCollapse: 'collapse',
      backgroundColor: 'white',
      borderRadius: '8px',
      overflow: 'hidden',
      boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
      border: '1px solid #e1e5e9'
    }
    
    const thStyle = {
      backgroundColor: '#f8f9fa',
      padding: '12px 16px',
      textAlign: 'left',
      fontWeight: '600',
      color: '#495057',
      borderBottom: '2px solid #e1e5e9',
      cursor: 'pointer',
      userSelect: 'none'
    }
    
    const tdStyle = {
      padding: '12px 16px',
      borderBottom: '1px solid #f1f3f4',
      verticalAlign: 'middle'
    }

    return (
      <div>
        <h3 style={{ marginBottom: '16px', color: '#495057' }}>Driver Management</h3>
        
        {/* Driver Statistics */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '16px', marginBottom: '24px' }}>
          <div style={{ ...cardStyle, textAlign: 'center', padding: '20px' }}>
            <div style={{ fontSize: '28px', fontWeight: 'bold', color: '#fd7e14', marginBottom: '4px' }}>
              {drivers.length}
            </div>
            <div style={{ color: '#6c757d', fontSize: '14px' }}>Total Drivers</div>
          </div>
          <div style={{ ...cardStyle, textAlign: 'center', padding: '20px' }}>
            <div style={{ fontSize: '28px', fontWeight: 'bold', color: '#28a745', marginBottom: '4px' }}>
              {activeDrivers}
            </div>
            <div style={{ color: '#6c757d', fontSize: '14px' }}>Active Drivers</div>
          </div>
          <div style={{ ...cardStyle, textAlign: 'center', padding: '20px' }}>
            <div style={{ fontSize: '28px', fontWeight: 'bold', color: '#dc3545', marginBottom: '4px' }}>
              {inactiveDrivers}
            </div>
            <div style={{ color: '#6c757d', fontSize: '14px' }}>Inactive Drivers</div>
          </div>
          <div style={{ ...cardStyle, textAlign: 'center', padding: '20px' }}>
            <div style={{ fontSize: '28px', fontWeight: 'bold', color: '#007bff', marginBottom: '4px' }}>
              {activeDrivers > 0 ? Math.round((activeDrivers / drivers.length) * 100) : 0}%
            </div>
            <div style={{ color: '#6c757d', fontSize: '14px' }}>Active Rate</div>
          </div>
        </div>

        {/* Controls */}
        <div style={{ display: 'flex', gap: '16px', marginBottom: '20px', alignItems: 'center', flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <label style={{ fontWeight: '500', color: '#495057' }}>Status:</label>
            <select 
              value={statusFilter} 
              onChange={(e) => setStatusFilter(e.target.value)}
              style={{
                padding: '8px 12px',
                border: '1px solid #ced4da',
                borderRadius: '4px',
                backgroundColor: 'white'
              }}
            >
              <option value="all">All Drivers ({drivers.length})</option>
              <option value="active">Active ({activeDrivers})</option>
              <option value="inactive">Inactive ({inactiveDrivers})</option>
            </select>
          </div>
          
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <label style={{ fontWeight: '500', color: '#495057' }}>Sort by:</label>
            <select 
              value={driverSortBy} 
              onChange={(e) => setDriverSortBy(e.target.value)}
              style={{
                padding: '8px 12px',
                border: '1px solid #ced4da',
                borderRadius: '4px',
                backgroundColor: 'white'
              }}
            >
              <option value="created_at">Join Date</option>
              <option value="name">Name</option>
              <option value="email">Email</option>
              <option value="license_no">License Number</option>
            </select>
            <button
              onClick={() => setDriverSortOrder(driverSortOrder === 'asc' ? 'desc' : 'asc')}
              style={{
                padding: '8px 12px',
                border: '1px solid #ced4da',
                borderRadius: '4px',
                backgroundColor: 'white',
                cursor: 'pointer'
              }}
            >
              {driverSortOrder === 'asc' ? '↑' : '↓'}
            </button>
          </div>
        </div>

        {/* Drivers Table */}
        <div style={{ overflowX: 'auto' }}>
          <table style={tableStyle}>
            <thead>
              <tr>
                <th style={thStyle} onClick={() => setDriverSortBy('name')}>
                  🚗 Driver {driverSortBy === 'name' && (driverSortOrder === 'asc' ? '↑' : '↓')}
                </th>
                <th style={thStyle} onClick={() => setDriverSortBy('email')}>
                  📧 Email {driverSortBy === 'email' && (driverSortOrder === 'asc' ? '↑' : '↓')}
                </th>
                <th style={thStyle} onClick={() => setDriverSortBy('license_no')}>
                  🪪 License {driverSortBy === 'license_no' && (driverSortOrder === 'asc' ? '↑' : '↓')}
                </th>
                <th style={thStyle} onClick={() => setDriverSortBy('created_at')}>
                  📅 Joined {driverSortBy === 'created_at' && (driverSortOrder === 'asc' ? '↑' : '↓')}
                </th>
                <th style={thStyle}>📊 Status</th>
              </tr>
            </thead>
            <tbody>
              {sortedDrivers.map(driver => (
                <tr key={driver.id} style={{ backgroundColor: driver.is_active !== 'true' ? '#fff5f5' : 'white' }}>
                  <td style={tdStyle}>
                    <div style={{ fontWeight: '600', color: '#212529' }}>{driver.name}</div>
                    <div style={{ fontSize: '12px', color: '#6c757d' }}>ID: {driver.id}</div>
                  </td>
                  <td style={tdStyle}>
                    <div style={{ color: '#495057' }}>{driver.email}</div>
                  </td>
                  <td style={tdStyle}>
                    <span style={{ 
                      fontFamily: 'monospace', 
                      backgroundColor: '#f8f9fa', 
                      padding: '4px 8px', 
                      borderRadius: '4px',
                      fontSize: '13px',
                      fontWeight: '600'
                    }}>
                      {driver.license_no}
                    </span>
                  </td>
                  <td style={tdStyle}>
                    <div>{new Date(driver.created_at).toLocaleDateString()}</div>
                    <div style={{ fontSize: '12px', color: '#6c757d' }}>
                      {new Date(driver.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </div>
                  </td>
                  <td style={tdStyle}>
                    <span style={{
                      padding: '6px 12px',
                      borderRadius: '12px',
                      fontSize: '12px',
                      fontWeight: '600',
                      background: driver.is_active === 'true' ? '#d4edda' : '#f8d7da',
                      color: driver.is_active === 'true' ? '#155724' : '#721c24'
                    }}>
                      {driver.is_active === 'true' ? '🟢 Available' : '🔴 Offline'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        
        {sortedDrivers.length === 0 && (
          <div style={{ textAlign: 'center', padding: '40px', color: '#6c757d' }}>
            No drivers found for the selected filter.
          </div>
        )}
        
        <div style={{ marginTop: '16px', fontSize: '14px', color: '#6c757d', textAlign: 'center' }}>
          Showing {sortedDrivers.length} of {drivers.length} drivers
        </div>
      </div>
    )
  }

  const RidesTab = () => (
    <div>
      <h3 style={{ marginBottom: '16px', color: '#495057' }}>Ride Management</h3>
      <p style={{ marginBottom: '24px', color: '#6c757d' }}>
        Track all ride requests, assignments, and completions. Monitor ride status and manage customer-driver interactions.
      </p>
      
      <div style={{ display: 'grid', gap: '16px' }}>
        {rides.map(ride => (
          <div key={ride.id} style={cardStyle}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div style={{ flex: 1 }}>
                <div style={{ display: 'flex', alignItems: 'center', marginBottom: '8px' }}>
                  <strong style={{ fontSize: '18px', marginRight: '12px' }}>🛣️ Ride #{ride.id}</strong>
                  <span style={{
                    padding: '4px 8px',
                    borderRadius: '12px',
                    fontSize: '12px',
                    fontWeight: '500',
                    background: ride.status === 'requested' ? '#ffc107' : 
                               ride.status === 'accepted' ? '#17a2b8' :
                               ride.status === 'completed' ? '#28a745' : '#6c757d',
                    color: 'white'
                  }}>
                    {ride.status.toUpperCase()}
                  </span>
                </div>
                <div style={{ color: '#6c757d', marginBottom: '4px' }}>👤 Customer: {ride.customer_name}</div>
                <div style={{ color: '#6c757d', marginBottom: '4px' }}>
                  🚗 Driver: {ride.driver_id ? `ID ${ride.driver_id}` : 'Unassigned'}
                </div>
                {ride.pickup_location && (
                  <div style={{ color: '#6c757d', marginBottom: '4px' }}>📍 From: {ride.pickup_location}</div>
                )}
                {ride.destination && (
                  <div style={{ color: '#6c757d', marginBottom: '4px' }}>🎯 To: {ride.destination}</div>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )

  const ReportsTab = () => (
    <div>
      <h3 style={{ marginBottom: '16px', color: '#495057' }}>Business Reports & Analytics</h3>
      <p style={{ marginBottom: '24px', color: '#6c757d' }}>
        Essential data summaries and key performance indicators for business decision making and operational insights.
      </p>
      
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '20px' }}>
        <div style={cardStyle}>
          <h4 style={{ color: '#495057', marginBottom: '16px' }}>📈 Growth Metrics</h4>
          <div style={{ marginBottom: '12px' }}>
            <strong>Total Platform Users:</strong> {metrics.totalUsers}
          </div>
          <div style={{ marginBottom: '12px' }}>
            <strong>Driver Network Size:</strong> {metrics.totalDrivers}
          </div>
          <div style={{ marginBottom: '12px' }}>
            <strong>Ride Requests Processed:</strong> {metrics.totalRides}
          </div>
          <div style={{ marginBottom: '12px' }}>
            <strong>Active User Retention:</strong> {metrics.totalUsers > 0 ? Math.round((metrics.activeUsers / metrics.totalUsers) * 100) : 0}%
          </div>
        </div>

        <div style={cardStyle}>
          <h4 style={{ color: '#495057', marginBottom: '16px' }}>⚡ Operational Efficiency</h4>
          <div style={{ marginBottom: '12px' }}>
            <strong>Ride Completion Rate:</strong> {metrics.totalRides > 0 ? Math.round((metrics.completedRides / metrics.totalRides) * 100) : 0}%
          </div>
          <div style={{ marginBottom: '12px' }}>
            <strong>Driver Utilization:</strong> {metrics.totalDrivers > 0 ? Math.round((metrics.activeDrivers / metrics.totalDrivers) * 100) : 0}%
          </div>
          <div style={{ marginBottom: '12px' }}>
            <strong>Pending Requests:</strong> {metrics.pendingRides}
          </div>
          <div style={{ marginBottom: '12px' }}>
            <strong>Active Rides:</strong> {metrics.acceptedRides}
          </div>
        </div>

        <div style={cardStyle}>
          <h4 style={{ color: '#495057', marginBottom: '16px' }}>👥 User Segmentation</h4>
          <div style={{ marginBottom: '12px' }}>
            <strong>Customer Base:</strong> {metrics.customers} users ({metrics.totalUsers > 0 ? Math.round((metrics.customers / metrics.totalUsers) * 100) : 0}%)
          </div>
          <div style={{ marginBottom: '12px' }}>
            <strong>Driver Community:</strong> {metrics.totalDrivers} users ({metrics.totalUsers > 0 ? Math.round((metrics.totalDrivers / metrics.totalUsers) * 100) : 0}%)
          </div>
          <div style={{ marginBottom: '12px' }}>
            <strong>Administrative Staff:</strong> {metrics.admins} users
          </div>
        </div>

        <div style={cardStyle}>
          <h4 style={{ color: '#495057', marginBottom: '16px' }}>🎯 Key Performance Indicators</h4>
          <div style={{ marginBottom: '12px' }}>
            <strong>Platform Health Score:</strong> {
              metrics.totalUsers > 0 && metrics.totalDrivers > 0 && metrics.totalRides > 0
                ? Math.round(((metrics.activeUsers / metrics.totalUsers) * 0.4 + 
                             (metrics.activeDrivers / metrics.totalDrivers) * 0.4 + 
                             (metrics.completedRides / metrics.totalRides) * 0.2) * 100)
                : 0
            }%
          </div>
          <div style={{ marginBottom: '12px' }}>
            <strong>Service Availability:</strong> {metrics.activeDrivers > 0 ? '🟢 Online' : '🔴 Limited'}
          </div>
          <div style={{ marginBottom: '12px' }}>
            <strong>System Status:</strong> {error ? '⚠️ Issues Detected' : '✅ Operational'}
          </div>
        </div>
      </div>
    </div>
  )

  const InvitesTab = () => {
    const [newInviteDescription, setNewInviteDescription] = useState('')
    const [showCreateForm, setShowCreateForm] = useState(false)

    const handleCreateInvite = async () => {
      const invite = await createInvite(newInviteDescription)
      if (invite) {
        setNewInviteDescription('')
        setShowCreateForm(false)
      }
    }

    return (
      <div>
        <h3 style={{ marginBottom: '16px', color: '#495057' }}>Admin Invitation Management</h3>
        <p style={{ marginBottom: '24px', color: '#6c757d' }}>
          Create and manage invitation codes for new administrators. Each code can be used once to register an admin account.
        </p>
        
        <div style={cardStyle}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
            <h4>Create New Invitation</h4>
            <button 
              onClick={() => setShowCreateForm(!showCreateForm)}
              style={{
                padding: '8px 16px',
                background: '#28a745',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                cursor: 'pointer'
              }}
            >
              {showCreateForm ? 'Cancel' : '+ Create Invite'}
            </button>
          </div>
          
          {showCreateForm && (
            <div style={{ marginBottom: '20px', padding: '16px', background: '#f8f9fa', borderRadius: '8px' }}>
              <input
                type="text"
                placeholder="Invitation description (optional)"
                value={newInviteDescription}
                onChange={(e) => setNewInviteDescription(e.target.value)}
                style={{
                  width: '100%',
                  padding: '8px 12px',
                  marginBottom: '12px',
                  border: '1px solid #ddd',
                  borderRadius: '4px'
                }}
              />
              <button 
                onClick={handleCreateInvite}
                style={{
                  padding: '8px 16px',
                  background: '#007bff',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer'
                }}
              >
                Generate Access Code
              </button>
            </div>
          )}
        </div>

        <div style={{ display: 'grid', gap: '16px' }}>
          {invites.map(invite => (
            <div key={invite.id} style={cardStyle}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', alignItems: 'center', marginBottom: '8px' }}>
                    <strong style={{ fontSize: '18px', marginRight: '12px', fontFamily: 'monospace' }}>
                      {invite.access_code}
                    </strong>
                    <span style={{
                      padding: '4px 8px',
                      borderRadius: '12px',
                      fontSize: '12px',
                      fontWeight: '500',
                      background: invite.is_used ? '#dc3545' : '#28a745',
                      color: 'white'
                    }}>
                      {invite.is_used ? 'USED' : 'ACTIVE'}
                    </span>
                  </div>
                  {invite.description && (
                    <div style={{ color: '#6c757d', marginBottom: '4px' }}>📝 {invite.description}</div>
                  )}
                  <div style={{ color: '#6c757d', marginBottom: '4px' }}>
                    👤 Created by: {invite.created_by}
                  </div>
                  <div style={{ color: '#6c757d', marginBottom: '4px' }}>
                    📅 Created: {new Date(invite.created_at).toLocaleDateString()}
                  </div>
                  {invite.is_used && invite.used_by_email && (
                    <div style={{ color: '#6c757d', marginBottom: '4px' }}>
                      ✅ Used by: {invite.used_by_email} on {new Date(invite.used_at).toLocaleDateString()}
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    )
  }

  const ApiDocsTab = () => (
    <div>
      <h3 style={{ marginBottom: '16px', color: '#495057' }}>API Documentation & Endpoints</h3>
      <p style={{ marginBottom: '24px', color: '#6c757d' }}>
        Complete API documentation showing all available endpoints, methods, and schemas. This data comes from FastAPI's OpenAPI specification.
      </p>
      
      <div style={{ marginBottom: '20px' }}>
        <div style={cardStyle}>
          <h4 style={{ marginBottom: '16px' }}>🌐 API Base URL</h4>
          <div style={{ fontFamily: 'monospace', background: '#f8f9fa', padding: '12px', borderRadius: '4px' }}>
            {apiBase}
          </div>
          <div style={{ marginTop: '12px' }}>
            <a 
              href={`${apiBase}/docs`} 
              target="_blank" 
              rel="noopener noreferrer"
              style={{
                color: '#007bff',
                textDecoration: 'none',
                fontWeight: '500'
              }}
            >
              🔗 Open Interactive API Documentation
            </a>
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gap: '16px' }}>
        {apiEndpoints.map((endpoint, index) => (
          <div key={index} style={cardStyle}>
            <div style={{ marginBottom: '12px' }}>
              <div style={{ display: 'flex', alignItems: 'center', marginBottom: '8px' }}>
                <span style={{ fontFamily: 'monospace', fontSize: '16px', fontWeight: 'bold' }}>
                  {endpoint.path}
                </span>
              </div>
              <div style={{ display: 'flex', gap: '8px' }}>
                {endpoint.methods.map(method => (
                  <span
                    key={method}
                    style={{
                      padding: '4px 8px',
                      borderRadius: '4px',
                      fontSize: '12px',
                      fontWeight: 'bold',
                      color: 'white',
                      background: 
                        method === 'get' ? '#28a745' :
                        method === 'post' ? '#007bff' :
                        method === 'put' ? '#ffc107' :
                        method === 'delete' ? '#dc3545' : '#6c757d'
                    }}
                  >
                    {method.toUpperCase()}
                  </span>
                ))}
              </div>
            </div>
            {endpoint.get?.summary && (
              <div style={{ color: '#6c757d', marginBottom: '4px' }}>
                📄 {endpoint.get.summary}
              </div>
            )}
            {endpoint.post?.summary && (
              <div style={{ color: '#6c757d', marginBottom: '4px' }}>
                📄 {endpoint.post.summary}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )

  return (
    <div style={containerStyle}>
      <div style={headerStyle}>
        <h1 style={{ margin: '0 0 10px 0', fontSize: '32px' }}>🏢 HalfApp Admin Dashboard</h1>
        <p style={{ margin: 0, opacity: 0.9 }}>Comprehensive platform management and business analytics</p>
      </div>

      {error && (
        <div style={{
          ...cardStyle,
          background: '#f8d7da',
          border: '1px solid #f5c6cb',
          color: '#721c24',
          marginBottom: '20px'
        }}>
          ⚠️ Error: {error}
        </div>
      )}
      
      <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'center', marginBottom: '30px' }}>
        <button style={tabButtonStyle('overview')} onClick={() => setActiveTab('overview')}>
          📊 Overview
        </button>
        <button style={tabButtonStyle('users')} onClick={() => setActiveTab('users')}>
          👥 Users ({users.length})
        </button>
        <button style={tabButtonStyle('drivers')} onClick={() => setActiveTab('drivers')}>
          🚗 Drivers ({drivers.length})
        </button>
        <button style={tabButtonStyle('rides')} onClick={() => setActiveTab('rides')}>
          🛣️ Rides ({rides.length})
        </button>
        <button style={tabButtonStyle('reports')} onClick={() => setActiveTab('reports')}>
          📈 Reports
        </button>

        <button style={tabButtonStyle('api')} onClick={() => setActiveTab('api')}>
          🔧 API Docs
        </button>
        <button style={tabButtonStyle('stability')} onClick={() => setActiveTab('stability')}>
          📈 Stability
        </button>
      </div>

      {loading ? (
        <div style={cardStyle}>
          <div style={{ textAlign: 'center', padding: '40px', color: '#6c757d' }}>
            <div style={{ fontSize: '24px', marginBottom: '16px' }}>⏳</div>
            <p>Loading dashboard data...</p>
          </div>
        </div>
      ) : (
        <div>
          {activeTab === 'overview' && <OverviewTab />}
          {activeTab === 'users' && <UsersTab />}
          {activeTab === 'drivers' && <DriversTab />}
          {activeTab === 'rides' && <RidesTab />}
          {activeTab === 'reports' && <ReportsTab />}
          {activeTab === 'api' && <ApiDocsTab />}
          {activeTab === 'stability' && <StabilityDashboard />}
        </div>
      )}
      
      <div style={{ textAlign: 'center', marginTop: '40px' }}>
        <button 
          onClick={fetchData} 
          style={{
            padding: '12px 24px',
            background: 'linear-gradient(135deg, #28a745, #20c997)',
            color: 'white',
            border: 'none',
            borderRadius: '8px',
            fontSize: '16px',
            fontWeight: '500',
            cursor: 'pointer',
            boxShadow: '0 4px 12px rgba(40, 167, 69, 0.3)'
          }}
        >
          🔄 Refresh Data
        </button>
      </div>
    </div>
  )
}