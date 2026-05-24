import React, { useEffect, useState } from 'react'
import {
  BETA_DRIVER_ACKNOWLEDGMENT_BLOCKS,
  BETA_FIRST_RUN_ACK_STORAGE_KEY,
  BETA_NO_MONEY_TRUTH_ENABLED,
} from '../utils/betaTruthCopy.js'

/**
 * First-run beta acknowledgment (localStorage). Ops may require a server-side ack later.
 */
export default function BetaFirstRunAck() {
  const [open, setOpen] = useState(false)
  const [checked, setChecked] = useState(false)

  useEffect(() => {
    if (!BETA_NO_MONEY_TRUTH_ENABLED) return
    try {
      const acked = localStorage.getItem(BETA_FIRST_RUN_ACK_STORAGE_KEY) === '1'
      setOpen(!acked)
    } catch {
      setOpen(true)
    }
  }, [])

  if (!BETA_NO_MONEY_TRUTH_ENABLED || !open) return null

  function handleConfirm() {
    if (!checked) return
    try {
      localStorage.setItem(BETA_FIRST_RUN_ACK_STORAGE_KEY, '1')
    } catch {
      /* ignore */
    }
    setOpen(false)
  }

  return (
    <div
      className="fixed inset-0 z-[80] flex items-end sm:items-center justify-center bg-black/70 p-4"
      data-testid="beta-first-run-ack"
      role="dialog"
      aria-modal="true"
      aria-labelledby="beta-first-run-ack-title"
    >
      <div className="w-full max-w-md rounded-[20px] border border-sky-500/30 bg-[#0b1224] p-4 shadow-xl">
        <p
          id="beta-first-run-ack-title"
          className="text-sm font-semibold text-sky-100"
        >
          Before you drive — beta truth
        </p>
        <ul className="mt-3 max-h-[50vh] overflow-y-auto space-y-2 text-[12px] text-sky-50/90 list-disc pl-4">
          {BETA_DRIVER_ACKNOWLEDGMENT_BLOCKS.map((block) => (
            <li key={block}>{block}</li>
          ))}
        </ul>
        <label className="mt-4 flex items-start gap-2 text-[12px] text-sky-100/90 cursor-pointer">
          <input
            type="checkbox"
            checked={checked}
            onChange={(e) => setChecked(e.target.checked)}
            data-testid="beta-first-run-ack-checkbox"
            className="mt-0.5"
          />
          <span>I understand this is a no-money comprehension beta.</span>
        </label>
        <button
          type="button"
          disabled={!checked}
          onClick={handleConfirm}
          data-testid="beta-first-run-ack-confirm"
          className="cockpit-pressable mt-4 w-full min-h-[44px] rounded-full bg-sky-600 text-[13px] font-semibold text-white disabled:opacity-40"
        >
          Continue to cockpit
        </button>
      </div>
    </div>
  )
}
