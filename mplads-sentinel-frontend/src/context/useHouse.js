import { useContext } from 'react'
import { HouseContext } from './house-context-definition'

export function useHouse() {
  const ctx = useContext(HouseContext)
  if (!ctx) throw new Error('useHouse must be used within a HouseProvider')
  return ctx
}
