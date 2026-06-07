import { existsSync, readdirSync, statSync } from 'node:fs'
import path from 'node:path'
import { pathToFileURL } from 'node:url'

const patterns = process.argv.slice(2)
const cwd = process.cwd()

function walk(dir) {
  const entries = readdirSync(dir, { withFileTypes: true })
  return entries.flatMap((entry) => {
    const fullPath = path.join(dir, entry.name)
    if (entry.isDirectory()) return walk(fullPath)
    if (entry.isFile()) return [fullPath]
    return []
  })
}

function expandPattern(pattern) {
  const normalized = pattern.replace(/\\/g, '/')
  const recursiveTestSuffix = '/**/*.test.js'

  if (normalized.endsWith(recursiveTestSuffix)) {
    const base = normalized.slice(0, -recursiveTestSuffix.length) || '.'
    const basePath = path.resolve(cwd, base)
    if (!existsSync(basePath) || !statSync(basePath).isDirectory()) return []
    return walk(basePath).filter((file) => file.endsWith('.test.js'))
  }

  const exactPath = path.resolve(cwd, pattern)
  return existsSync(exactPath) ? [exactPath] : []
}

const files = [...new Set((patterns.length ? patterns : ['tests/unit/**/*.test.js']).flatMap(expandPattern))]
  .sort((a, b) => a.localeCompare(b))

if (files.length === 0) {
  console.error('No test files matched.')
  process.exitCode = 1
} else {
  for (const file of files) {
    await import(pathToFileURL(file).href)
  }
}
