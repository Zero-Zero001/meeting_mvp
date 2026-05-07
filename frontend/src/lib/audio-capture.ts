export type DisplayCaptureMode = 'tab_audio' | 'system_audio'

export type CaptureFailureCode =
  | 'permission_denied'
  | 'no_audio_track'
  | 'not_supported'
  | 'capture_failed'

export type DisplayMediaCaptureResult =
  | {
      ok: true
      stream: MediaStream
    }
  | {
      errorCode: CaptureFailureCode
      message: string
      ok: false
    }

type DisplayMediaCaptureOptions = {
  isSecureContext?: boolean
  mediaDevices?: Pick<MediaDevices, 'getDisplayMedia'> | null
  mode: DisplayCaptureMode
}

export function stopMediaStream(stream: MediaStream | null): void {
  stream?.getTracks().forEach((track) => track.stop())
}

function captureFailureMessage(errorCode: CaptureFailureCode): string {
  switch (errorCode) {
    case 'permission_denied':
      return '浏览器拒绝了捕获授权。'
    case 'no_audio_track':
      return '未捕获到音频轨道。'
    case 'not_supported':
      return '当前浏览器不支持屏幕共享音频捕获。'
    case 'capture_failed':
      return '捕获会议音频失败。'
  }
}

function resolveMediaDevices(
  mediaDevices: DisplayMediaCaptureOptions['mediaDevices'],
): Pick<MediaDevices, 'getDisplayMedia'> | null {
  if (mediaDevices !== undefined) {
    return mediaDevices
  }

  if (typeof navigator === 'undefined') {
    return null
  }

  return navigator.mediaDevices ?? null
}

function resolveSecureContext(isSecureContext: boolean | undefined): boolean {
  if (typeof isSecureContext === 'boolean') {
    return isSecureContext
  }

  if (typeof globalThis.isSecureContext === 'boolean') {
    return globalThis.isSecureContext
  }

  return true
}

function errorCodeFromException(error: unknown): CaptureFailureCode {
  if (error instanceof DOMException || error instanceof Error) {
    if (error.name === 'NotAllowedError' || error.name === 'SecurityError') {
      return 'permission_denied'
    }
  }

  return 'capture_failed'
}

function captureFailure(errorCode: CaptureFailureCode): DisplayMediaCaptureResult {
  return {
    errorCode,
    message: captureFailureMessage(errorCode),
    ok: false,
  }
}

export async function requestDisplayMediaCapture({
  isSecureContext,
  mediaDevices,
}: DisplayMediaCaptureOptions): Promise<DisplayMediaCaptureResult> {
  const resolvedMediaDevices = resolveMediaDevices(mediaDevices)

  if (
    !resolveSecureContext(isSecureContext) ||
    typeof resolvedMediaDevices?.getDisplayMedia !== 'function'
  ) {
    return captureFailure('not_supported')
  }

  try {
    const stream = await resolvedMediaDevices.getDisplayMedia({
      audio: true,
      video: true,
    })

    if (stream.getAudioTracks().length === 0) {
      stopMediaStream(stream)
      return captureFailure('no_audio_track')
    }

    return {
      ok: true,
      stream,
    }
  } catch (error: unknown) {
    return captureFailure(errorCodeFromException(error))
  }
}
