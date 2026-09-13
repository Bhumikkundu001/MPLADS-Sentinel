import { useState } from 'react'
import { HouseContext, STORAGE_KEY, VALID_HOUSES } from './house-context-definition'

function readInitialHouse() {
  const stored = window.localStorage.getItem(STORAGE_KEY)
  return VALID_HOUSES.includes(stored) ? stored : 'all'
}

export function HouseProvider({ children }) {
  const [selectedHouse, setSelectedHouseState] = useState(readInitialHouse)

  function setSelectedHouse(house) {
    if (!VALID_HOUSES.includes(house)) return
    setSelectedHouseState(house)
    window.localStorage.setItem(STORAGE_KEY, house)
  }

  // The value the backend expects — omit the "house" param entirely for "all".
  const houseParam = selectedHouse === 'all' ? undefined : selectedHouse
  const houseLabel = selectedHouse === 'all' ? 'All Houses' : selectedHouse

  const value = { selectedHouse, setSelectedHouse, houseParam, houseLabel }
  return <HouseContext.Provider value={value}>{children}</HouseContext.Provider>
}
