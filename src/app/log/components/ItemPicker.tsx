'use client'

import { useMemo, useState } from 'react'
import type { InstallBudgetItem } from '@/lib/types'
import type { RecentItem } from '@/lib/use-recent-items'

interface Props {
  recents: RecentItem[]
  allItems: InstallBudgetItem[]
  onSelect: (item: InstallBudgetItem) => void
}

export function ItemPicker({ recents, allItems, onSelect }: Props) {
  const [query, setQuery] = useState('')
  const [activeCategory, setActiveCategory] = useState<string | null>(null)

  const categories = useMemo(() => {
    const set = new Set<string>()
    for (const i of allItems) set.add(i.category)
    return Array.from(set).sort()
  }, [allItems])

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    return allItems.filter((i) => {
      if (activeCategory && i.category !== activeCategory) return false
      if (!q) return true
      return (
        (i.name ?? '').toLowerCase().includes(q) ||
        i.category.toLowerCase().includes(q)
      )
    })
  }, [allItems, query, activeCategory])

  return (
    <div className="space-y-4">
      {recents.length > 0 && (
        <section>
          <h3 className="mb-2 text-xs uppercase tracking-wide text-gray-500">Recently logged</h3>
          <ul className="space-y-2">
            {recents.map((r) => (
              <li key={r.budgetItem.id}>
                <button
                  type="button"
                  onClick={() => onSelect(r.budgetItem)}
                  className="w-full rounded-xl bg-white p-3 text-left shadow"
                >
                  <div className="text-xs text-gray-500">{r.budgetItem.category}</div>
                  <div className="text-sm font-medium">{r.budgetItem.name ?? '(unnamed item)'}</div>
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}

      <div className="space-y-2">
        <input
          type="text"
          aria-label="Search items"
          placeholder="Search items…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <div className="-mx-1 flex gap-2 overflow-x-auto px-1 pb-1">
          <button
            type="button"
            onClick={() => setActiveCategory(null)}
            className={`shrink-0 rounded-full px-3 py-1 text-sm ${
              activeCategory === null ? 'bg-hytek-black text-white' : 'bg-gray-200'
            }`}
          >
            All
          </button>
          {categories.map((c) => (
            <button
              key={c}
              type="button"
              onClick={() => setActiveCategory(c)}
              className={`shrink-0 rounded-full px-3 py-1 text-sm ${
                activeCategory === c ? 'bg-hytek-black text-white' : 'bg-gray-200'
              }`}
            >
              {c}
            </button>
          ))}
        </div>
      </div>

      <ul className="space-y-2">
        {filtered.map((i) => (
          <li key={i.id}>
            <button
              type="button"
              onClick={() => onSelect(i)}
              className="w-full rounded-xl bg-white p-3 text-left shadow"
            >
              <div className="text-xs text-gray-500">{i.category}</div>
              <div className="text-sm">{i.name ?? '(unnamed item)'}</div>
            </button>
          </li>
        ))}
        {filtered.length === 0 && (
          <li className="py-8 text-center text-sm text-gray-500">No items match.</li>
        )}
      </ul>
    </div>
  )
}
