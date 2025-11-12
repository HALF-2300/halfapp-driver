// Table Component - Figma-ready design system component
import React, { useState } from 'react'
import { designTokens } from './tokens'
import Button from './Button'

export const Table = ({ 
  data = [],
  columns = [],
  sortable = true,
  filterable = false,
  pagination = false,
  pageSize = 10,
  className,
  style = {},
  ...props 
}) => {
  const [sortConfig, setSortConfig] = useState({ key: null, direction: 'asc' })
  const [currentPage, setCurrentPage] = useState(1)
  const [filter, setFilter] = useState('')

  const tokens = designTokens

  // Filter data
  const filteredData = filterable ? 
    data.filter(item => 
      Object.values(item).some(value => 
        value?.toString().toLowerCase().includes(filter.toLowerCase())
      )
    ) : data

  // Sort data
  const sortedData = [...filteredData].sort((a, b) => {
    if (!sortConfig.key) return 0
    
    const aVal = a[sortConfig.key]
    const bVal = b[sortConfig.key]
    
    if (aVal < bVal) return sortConfig.direction === 'asc' ? -1 : 1
    if (aVal > bVal) return sortConfig.direction === 'asc' ? 1 : -1
    return 0
  })

  // Paginate data
  const paginatedData = pagination ? 
    sortedData.slice((currentPage - 1) * pageSize, currentPage * pageSize) : sortedData

  const totalPages = pagination ? Math.ceil(sortedData.length / pageSize) : 1

  const handleSort = (key) => {
    if (!sortable) return
    
    setSortConfig(prev => ({
      key,
      direction: prev.key === key && prev.direction === 'asc' ? 'desc' : 'asc'
    }))
  }

  const tableStyle = {
    width: '100%',
    borderCollapse: 'collapse',
    backgroundColor: tokens.colors.neutral[0],
    borderRadius: tokens.borderRadius.lg,
    overflow: 'hidden',
    boxShadow: tokens.boxShadow.base,
    border: `1px solid ${tokens.colors.neutral[200]}`,
    fontFamily: tokens.typography.fontFamily.primary,
    ...style
  }

  const thStyle = {
    backgroundColor: tokens.colors.neutral[50],
    padding: `${tokens.spacing[3]} ${tokens.spacing[4]}`,
    textAlign: 'left',
    fontWeight: tokens.typography.fontWeight.semibold,
    color: tokens.colors.neutral[700],
    borderBottom: `2px solid ${tokens.colors.neutral[200]}`,
    fontSize: tokens.typography.fontSize.sm,
    cursor: sortable ? 'pointer' : 'default',
    userSelect: 'none',
    position: 'relative'
  }

  const tdStyle = {
    padding: `${tokens.spacing[3]} ${tokens.spacing[4]}`,
    borderBottom: `1px solid ${tokens.colors.neutral[100]}`,
    color: tokens.colors.neutral[800],
    fontSize: tokens.typography.fontSize.sm,
    verticalAlign: 'middle'
  }

  const filterStyle = {
    width: '100%',
    padding: tokens.spacing[3],
    marginBottom: tokens.spacing[4],
    border: `1px solid ${tokens.colors.neutral[300]}`,
    borderRadius: tokens.borderRadius.base,
    fontSize: tokens.typography.fontSize.sm,
    fontFamily: tokens.typography.fontFamily.primary
  }

  const paginationStyle = {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: tokens.spacing[4],
    fontSize: tokens.typography.fontSize.sm,
    color: tokens.colors.neutral[600]
  }

  const getSortIcon = (columnKey) => {
    if (sortConfig.key !== columnKey) return '↕️'
    return sortConfig.direction === 'asc' ? '↑' : '↓'
  }

  return (
    <div className={className} {...props}>
      {filterable && (
        <input
          type="text"
          placeholder="Search..."
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          style={filterStyle}
        />
      )}
      
      <div style={{ overflowX: 'auto' }}>
        <table style={tableStyle}>
          <thead>
            <tr>
              {columns.map((column) => (
                <th
                  key={column.key}
                  style={{
                    ...thStyle,
                    textAlign: column.align || 'left',
                    width: column.width || 'auto'
                  }}
                  onClick={() => handleSort(column.key)}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: tokens.spacing[2] }}>
                    {column.title}
                    {sortable && (
                      <span style={{ opacity: 0.5, fontSize: '12px' }}>
                        {getSortIcon(column.key)}
                      </span>
                    )}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {paginatedData.map((row, index) => (
              <tr key={index} style={{ backgroundColor: index % 2 === 0 ? tokens.colors.neutral[0] : tokens.colors.neutral[50] }}>
                {columns.map((column) => (
                  <td
                    key={column.key}
                    style={{
                      ...tdStyle,
                      textAlign: column.align || 'left'
                    }}
                  >
                    {column.render ? column.render(row[column.key], row, index) : row[column.key]}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {pagination && (
        <div style={paginationStyle}>
          <div>
            Showing {((currentPage - 1) * pageSize) + 1} to {Math.min(currentPage * pageSize, sortedData.length)} of {sortedData.length} entries
          </div>
          <div style={{ display: 'flex', gap: tokens.spacing[2] }}>
            <Button
              variant="secondary"
              size="sm"
              disabled={currentPage === 1}
              onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
            >
              Previous
            </Button>
            <span style={{ display: 'flex', alignItems: 'center', padding: `0 ${tokens.spacing[3]}` }}>
              Page {currentPage} of {totalPages}
            </span>
            <Button
              variant="secondary"
              size="sm"
              disabled={currentPage === totalPages}
              onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
            >
              Next
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}

// Simple table without advanced features
export const SimpleTable = ({ 
  headers = [],
  data = [],
  className,
  style = {},
  ...props 
}) => {
  const tokens = designTokens

  const tableStyle = {
    width: '100%',
    borderCollapse: 'collapse',
    backgroundColor: tokens.colors.neutral[0],
    borderRadius: tokens.borderRadius.lg,
    overflow: 'hidden',
    boxShadow: tokens.boxShadow.base,
    border: `1px solid ${tokens.colors.neutral[200]}`,
    fontFamily: tokens.typography.fontFamily.primary,
    ...style
  }

  const thStyle = {
    backgroundColor: tokens.colors.neutral[50],
    padding: `${tokens.spacing[3]} ${tokens.spacing[4]}`,
    textAlign: 'left',
    fontWeight: tokens.typography.fontWeight.semibold,
    color: tokens.colors.neutral[700],
    borderBottom: `2px solid ${tokens.colors.neutral[200]}`,
    fontSize: tokens.typography.fontSize.sm
  }

  const tdStyle = {
    padding: `${tokens.spacing[3]} ${tokens.spacing[4]}`,
    borderBottom: `1px solid ${tokens.colors.neutral[100]}`,
    color: tokens.colors.neutral[800],
    fontSize: tokens.typography.fontSize.sm,
    verticalAlign: 'middle'
  }

  return (
    <div style={{ overflowX: 'auto' }} className={className} {...props}>
      <table style={tableStyle}>
        <thead>
          <tr>
            {headers.map((header, index) => (
              <th key={index} style={thStyle}>
                {header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row, rowIndex) => (
            <tr key={rowIndex} style={{ backgroundColor: rowIndex % 2 === 0 ? tokens.colors.neutral[0] : tokens.colors.neutral[50] }}>
              {row.map((cell, cellIndex) => (
                <td key={cellIndex} style={tdStyle}>
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default Table