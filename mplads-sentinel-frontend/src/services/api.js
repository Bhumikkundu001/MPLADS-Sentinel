const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

const SERVICE_UNAVAILABLE_MESSAGE =
  'MPLADS Sentinel service is temporarily unavailable. Please try again in a moment.'

async function request(path, options = {}) {
  let response

  const auth = getStoredAuth()
  const token = auth?.access_token

  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  }

  if (token) {
    headers.Authorization = `Bearer ${token}`
  }

  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      headers,
    })
  } catch {
    // Network-level failure (server down, no connection, CORS, etc.)
    throw new Error(SERVICE_UNAVAILABLE_MESSAGE)
  }

  if (!response.ok) {
    if (response.status >= 500 || response.status === 0) {
      throw new Error(SERVICE_UNAVAILABLE_MESSAGE)
    }

    let detail = ''

    try {
      const body = await response.json()
      detail = body?.detail || ''
    } catch {
      // Response wasn't JSON.
    }

    throw new Error(detail || `Request failed (${response.status})`)
  }

  return response.json()
}

// Real work IDs (e.g. "WS/MP005/2024-2025/145074") contain literal "/" —
// always encode the ID as a single path segment when building a URL.
function encodeWorkId(workId) {
  return encodeURIComponent(workId)
}


// ============================================================
// Authentication
// ============================================================

async function login(email, password) {
  const body = new URLSearchParams()

  body.append('username', email)
  body.append('password', password)

  let response

  try {
    response = await fetch(`${API_BASE_URL}/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body,
    })
  } catch {
    throw new Error(SERVICE_UNAVAILABLE_MESSAGE)
  }

  if (!response.ok) {
    if (response.status >= 500 || response.status === 0) {
      throw new Error(SERVICE_UNAVAILABLE_MESSAGE)
    }

    let detail = ''

    try {
      const data = await response.json()
      detail = data?.detail || ''
    } catch {
      // Response wasn't JSON.
    }

    throw new Error(detail || `Login failed (${response.status})`)
  }

  return response.json()
}


function getStoredAuth() {
  const raw = localStorage.getItem('mplads_auth')

  if (!raw) {
    return null
  }

  try {
    return JSON.parse(raw)
  } catch {
    localStorage.removeItem('mplads_auth')
    return null
  }
}


function saveAuth(authData) {
  localStorage.setItem(
    'mplads_auth',
    JSON.stringify(authData),
  )
}


function clearAuth() {
  localStorage.removeItem('mplads_auth')
}


// ============================================================
// API
// ============================================================

export const api = {

  // ----------------------------------------------------------
  // Authentication
  // ----------------------------------------------------------

  login,

async getMe() {
  return request('/auth/me')
},

getStoredAuth,

saveAuth,

clearAuth,

  // ----------------------------------------------------------
  // Works
  // ----------------------------------------------------------

  async getWorks({
    limit,
    offset,
    q,
    state,
    status,
    risk,
    house,
    data_source,
  } = {}) {
    const params = new URLSearchParams()

    if (limit !== undefined && limit !== null) {
      params.set('limit', limit)
    }

    if (offset !== undefined && offset !== null) {
      params.set('offset', offset)
    }

    if (q) params.set('q', q)
    if (state) params.set('state', state)
    if (status) params.set('status', status)
    if (risk) params.set('risk', risk)
    if (house) params.set('house', house)
    if (data_source) params.set('data_source', data_source)

    const query = params.toString()

    const res = await request(
      `/works${query ? `?${query}` : ''}`,
    )

    // Prefer the Phase 6 "items" contract;
    // fall back to "works" for safety.
    return {
      ...res,
      items: res.items || res.works || [],
    }
  },


  // ----------------------------------------------------------
  // Risk
  // ----------------------------------------------------------

  async getRiskOverview(house) {
    const params = new URLSearchParams()

    if (house) params.set('house', house)

    const query = params.toString()

    return request(
      `/risk${query ? `?${query}` : ''}`,
    )
  },


  async getWork(workId) {
    return request(
      `/works/${encodeWorkId(workId)}`,
    )
  },


  async getRiskAnalysis(workId) {
    return request(
      `/risk/${encodeWorkId(workId)}`,
    )
  },


  async getSimilarWorks(workId) {
    return request(
      `/works/${encodeWorkId(workId)}/similar`,
    )
  },


  // ----------------------------------------------------------
  // Analytics
  // ----------------------------------------------------------

  async getAnalytics(house) {
    const params = new URLSearchParams()

    if (house) params.set('house', house)

    const query = params.toString()

    return request(
      `/analytics${query ? `?${query}` : ''}`,
    )
  },


  // ----------------------------------------------------------
  // Alerts
  // ----------------------------------------------------------

  async getAlerts(house) {
    const params = new URLSearchParams()

    if (house) params.set('house', house)

    const query = params.toString()

    return request(
      `/alerts${query ? `?${query}` : ''}`,
    )
  },


  // ----------------------------------------------------------
  // Copilot
  // ----------------------------------------------------------

  async askCopilot(
    message,
    conversationId = null,
    house = null,
  ) {
    let response

    try {
      response = await fetch(
        `${API_BASE_URL}/copilot`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            message,
            conversation_id: conversationId,
            ...(house ? { house } : {}),
          }),
        },
      )
    } catch {
      throw new Error(SERVICE_UNAVAILABLE_MESSAGE)
    }

    if (!response.ok) {
      throw new Error(SERVICE_UNAVAILABLE_MESSAGE)
    }

    return response.json()
  },
}