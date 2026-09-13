import { createContext } from 'react'

export const STORAGE_KEY = 'mplads_selected_house'
export const VALID_HOUSES = ['all', 'Lok Sabha', 'Rajya Sabha']

export const HouseContext = createContext(undefined)
