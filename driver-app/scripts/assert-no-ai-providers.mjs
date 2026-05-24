#!/usr/bin/env node
/**
 * Guard: driver-app/src must not reference external AI provider endpoints or API keys.
 */
import { readFileSync, readdirSync, statSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const SRC = path.resolve(__dirname, '../src')
const FORBIDDEN = [
  'api.anthropic.com',
  'api.openai.com',
  'x-api-key',
  // Driver-app must not call dossier marketplace APIs (HALFAPP_DRIVER_API_BOUNDARY_CI_01)
  '/supply/',
  '/demand/',
  '/trip/',
]

function walk(dir, acc = []) {
  for (const entry of readdirSync(dir)) {
    const full = path.join(dir, entry)
    if (statSync(full).isDirectory()) {
      walk(full, acc)
    } else if (/\.(jsx?|tsx?|js|ts)$/.test(entry)) {
      acc.push(full)
    }
  }
  return acc
}

let failed = false
for (const file of walk(SRC)) {
  const text = readFileSync(file, 'utf8')
  for (const needle of FORBIDDEN) {
    if (text.includes(needle)) {
      console.error(`FORBIDDEN "${needle}" in ${path.relative(SRC, file)}`)
      failed = true
    }
  }
}

if (failed) {
  process.exit(1)
}

console.log('assert-no-ai-providers: OK (no forbidden strings in driver-app/src)')
