export const PUBLIC_CONFIG_ENV_NAMES = [
  'VITE_APP_ENV',
  'VITE_PUBLIC_BASE_URL',
  'VITE_API_BASE_URL',
  'VITE_WS_BASE_URL',
] as const

export type PublicConfigEnv = Partial<
  Record<(typeof PUBLIC_CONFIG_ENV_NAMES)[number], string>
>

export type PublicConfig = {
  appEnv: string
  publicBaseUrl: string
  apiBaseUrl: string
  wsBaseUrl: string
}

export function getPublicConfig(
  env: PublicConfigEnv = import.meta.env,
): PublicConfig {
  return {
    appEnv: env.VITE_APP_ENV ?? 'local',
    publicBaseUrl: env.VITE_PUBLIC_BASE_URL ?? '',
    apiBaseUrl: env.VITE_API_BASE_URL ?? '',
    wsBaseUrl: env.VITE_WS_BASE_URL ?? '',
  }
}

export const publicConfig = getPublicConfig()
