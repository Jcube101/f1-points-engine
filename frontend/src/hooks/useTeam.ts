import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { Driver, Constructor } from '../lib/types'

interface TeamState {
  drivers: Driver[]
  constructors: Constructor[]
  drsBoostDriverId: number | null
  noNegative: boolean
  addDriver: (d: Driver) => void
  removeDriver: (id: number) => void
  addConstructor: (c: Constructor) => void
  removeConstructor: (id: number) => void
  setDrsBoost: (id: number) => void
  setNoNegative: (v: boolean) => void
  clearTeam: () => void
  loadOptimized: (drivers: Driver[], constructors: Constructor[]) => void
  totalSpent: () => number
  isValid: () => boolean
}

export const useTeam = create<TeamState>()(
  persist(
    (set, get) => ({
      drivers: [],
      constructors: [],
      drsBoostDriverId: null,
      noNegative: false,

      addDriver: (d) => {
        const { drivers } = get()
        if (drivers.find((x) => x.id === d.id)) return
        if (drivers.length >= 5) return
        set({ drivers: [...drivers, d] })
      },

      removeDriver: (id) => {
        set((s) => ({
          drivers: s.drivers.filter((d) => d.id !== id),
          drsBoostDriverId: s.drsBoostDriverId === id ? null : s.drsBoostDriverId,
        }))
      },

      addConstructor: (c) => {
        const { constructors } = get()
        if (constructors.find((x) => x.id === c.id)) return
        if (constructors.length >= 2) return
        set({ constructors: [...constructors, c] })
      },

      removeConstructor: (id) => {
        set((s) => ({ constructors: s.constructors.filter((c) => c.id !== id) }))
      },

      setDrsBoost: (id) => set({ drsBoostDriverId: id }),

      setNoNegative: (v) => set({ noNegative: v }),

      clearTeam: () => set({ drivers: [], constructors: [], drsBoostDriverId: null }),

      loadOptimized: (drivers, constructors) => set({ drivers, constructors }),

      totalSpent: () => {
        const { drivers, constructors } = get()
        return drivers.reduce((s, d) => s + d.price, 0) + constructors.reduce((s, c) => s + c.price, 0)
      },

      isValid: () => {
        const { drivers, constructors } = get()
        const spent = get().totalSpent()
        return drivers.length === 5 && constructors.length === 2 && spent <= 100_000_000
      },
    }),
    { name: 'f1-team' }
  )
)
