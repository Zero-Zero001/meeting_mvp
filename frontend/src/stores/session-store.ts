import { create } from 'zustand'

export type CaptureMode = 'tab_audio' | 'system_audio'
export type SessionStatus = 'idle' | 'capturing'

type SessionState = {
  captureMode: CaptureMode
  remainingSecondsToday: number
  status: SessionStatus
  beginCapture: (mode: CaptureMode) => void
  endSession: () => void
}

export const initialSessionState = {
  captureMode: 'tab_audio' as CaptureMode,
  remainingSecondsToday: 40 * 60,
  status: 'idle' as SessionStatus,
}

export const useSessionStore = create<SessionState>((set) => ({
  ...initialSessionState,
  beginCapture: (mode) =>
    set({
      captureMode: mode,
      status: 'capturing',
    }),
  endSession: () =>
    set({
      status: 'idle',
    }),
}))
