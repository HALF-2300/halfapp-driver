import React, { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { formatDate, listDrivers, statusBadgeClass, updateDriverReadiness } from '../utils/api.js'

const POLL_MS = 5000

export default function DriverListPage() {
  const [drivers, setDrivers] = useState([])
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)
  const [lastUpdated, setLastUpdated] = useState(null)
  const [savingId, setSavingId] = useState(null)

  const load = useCallback(async () => {
    try {
      const rows = await listDrivers()
      setDrivers(rows)
      setError(null)
      setLastUpdated(new Date())
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    setLoading(true)
    load()
    const timer = setInterval(load, POLL_MS)
    return () => clearInterval(timer)
  }, [load])

  const markVehicleReady = async (driver) => {
    setSavingId(driver.id)
    setError(null)
    try {
      const expires = new Date()
      expires.setFullYear(expires.getFullYear() + 1)
      await updateDriverReadiness(driver.id, {
        vehicle_ready: true,
        insurance_expires_at: expires.toISOString(),
        insurance_policy: driver.insurance?.policy || `OPS-${driver.id}`,
        reason: 'ops_closed_beta_readiness',
      })
      await load()
    } catch (err) {
      setError(err.message)
    } finally {
      setSavingId(null)
    }
  }

  return (
    <div>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">Drivers</h1>
          <p className="text-sm text-[var(--ops-muted)]">
            {drivers.length} drivers
            {lastUpdated ? ` · updated ${lastUpdated.toLocaleTimeString()}` : ''}
          </p>
        </div>
        <button type="button" className="ops-btn" onClick={load}>
          Refresh
        </button>
      </div>

      {error ? <p className="mb-4 text-sm text-red-300">{error}</p> : null}

      <div className="overflow-x-auto rounded-xl border border-white/10 bg-[var(--ops-surface)]">
        {loading && !drivers.length ? (
          <p className="p-6 text-sm text-[var(--ops-muted)]">Loading drivers…</p>
        ) : (
          <table className="ops-table" data-testid="drivers-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Name</th>
                <th>Status</th>
                <th>Online</th>
                <th>Approval</th>
                <th>Readiness</th>
                <th>Active ride</th>
                <th>Presence</th>
                <th>Ops action</th>
              </tr>
            </thead>
            <tbody>
              {drivers.map((driver) => (
                <tr key={driver.id}>
                  <td>#{driver.id}</td>
                  <td>
                    <div>{driver.name || '—'}</div>
                    <div className="text-xs text-[var(--ops-muted)]">{driver.email}</div>
                  </td>
                  <td>
                    <span className={`ops-badge ${statusBadgeClass(driver.availability_label)}`}>
                      {driver.availability_label}
                    </span>
                  </td>
                  <td>{driver.online ? 'Yes' : 'No'}</td>
                  <td>{driver.approval?.status || '—'}</td>
                  <td>
                    <div className="text-xs">
                      <div>Vehicle: {driver.readiness?.vehicle_ready ? 'Ready' : 'Needs review'}</div>
                      <div>Insurance: {driver.insurance?.expires_at ? formatDate(driver.insurance.expires_at) : 'Expiry missing'}</div>
                    </div>
                  </td>
                  <td>
                    {driver.active_ride_id ? (
                      <Link to={`/rides/${driver.active_ride_id}`} className="text-orange-300 hover:underline">
                        #{driver.active_ride_id}
                      </Link>
                    ) : (
                      '—'
                    )}
                  </td>
                  <td>{driver.presence?.effective_state || '—'}</td>
                  <td>
                    <button
                      type="button"
                      className="ops-btn"
                      disabled={savingId === driver.id}
                      onClick={() => markVehicleReady(driver)}
                      data-testid={`driver-readiness-ready-${driver.id}`}
                    >
                      {savingId === driver.id ? 'Saving…' : 'Mark ready'}
                    </button>
                  </td>
                </tr>
              ))}
              {!drivers.length ? (
                <tr>
                  <td colSpan={9} className="text-center text-[var(--ops-muted)]">
                    No drivers found
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
