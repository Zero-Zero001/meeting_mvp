import { describe, expect, it } from 'vitest'

import { getPublicConfig, PUBLIC_CONFIG_ENV_NAMES } from './public-config'

describe('public frontend config', () => {
  it('maps only Vite public environment variables', () => {
    const config = getPublicConfig({
      VITE_APP_ENV: 'local',
      VITE_PUBLIC_BASE_URL: 'http://localhost:5173',
      VITE_API_BASE_URL: 'http://localhost:8000',
      VITE_WS_BASE_URL: 'ws://localhost:8000/ws',
    })

    expect(config).toEqual({
      appEnv: 'local',
      publicBaseUrl: 'http://localhost:5173',
      apiBaseUrl: 'http://localhost:8000',
      wsBaseUrl: 'ws://localhost:8000/ws',
    })
  })

  it('does not expose private backend or provider config names', () => {
    const joinedNames = PUBLIC_CONFIG_ENV_NAMES.join('\n')

    for (const privateName of [
      'DATABASE_URL',
      'REDIS_URL',
      'GOOGLE_',
      'QWEN_',
      'OPENAI_',
      'TENCENT_COS_',
    ]) {
      expect(joinedNames).not.toContain(privateName)
    }
  })
})
