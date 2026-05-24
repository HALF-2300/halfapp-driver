#!/usr/bin/env node
/**
 * Guard: driver-app/src must not contain forbidden payment-claim language
 * (HALFAPP_PAYMENTS_EXECUTION_04 semantic lock).
 *
 * Uses the same phrases + allowlist as betaTruthCopy.js so negations like
 * "not paid" and "no payout" remain valid.
 */
import { readFileSync, readdirSync, statSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { containsBetaForbiddenPaymentLanguage } from '../src/utils/betaTruthCopy.js'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const SRC = path.resolve(__dirname, '../src')

/** Driver-visible surfaces only (not phrase registries or eng-intel context). */
const SCAN_ROOTS = [
  path.join(SRC, 'components'),
  path.join(SRC, 'frontpage'),
  path.join(SRC, 'App.jsx'),
]

/** Infrastructure screens may reference provider field names (e.g. account ids), not marketing claims. */
const SKIP_REL_PATHS = new Set(['components/DriverSettings.jsx'])

function walk(dir, acc = []) {
  if (!statSync(dir).isDirectory()) {
    if (/\.(jsx?|tsx?)$/.test(dir)) acc.push(dir)
    return acc
  }
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name)
    if (entry.isDirectory()) {
      walk(full, acc)
    } else if (/\.(jsx?|tsx?)$/.test(entry.name)) {
      acc.push(full)
    }
  }
  return acc
}

const files = SCAN_ROOTS.flatMap((root) => walk(root))

let failed = false
for (const file of files) {
  const rel = path.relative(SRC, file).replace(/\\/g, '/')
  if (SKIP_REL_PATHS.has(rel)) continue

  const text = readFileSync(file, 'utf8')
  if (containsBetaForbiddenPaymentLanguage(text)) {
    console.error(`FORBIDDEN payment-claim language in src/${rel}`)
    failed = true
  }
}

if (failed) {
  process.exit(1)
}

console.log(
  `assert-no-money-claims: OK (${files.length} driver-facing files, no forbidden payment-claim language)`
)
