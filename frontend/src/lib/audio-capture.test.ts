import { describe, expect, it, vi } from 'vitest'

import { requestDisplayMediaCapture } from './audio-capture'

function createTrack(kind: 'audio' | 'video' = 'audio') {
  return {
    kind,
    stop: vi.fn(),
  } as unknown as MediaStreamTrack
}

function createStream(audioTracks: MediaStreamTrack[]) {
  const videoTrack = createTrack('video')
  const tracks = [...audioTracks, videoTrack]

  return {
    getAudioTracks: () => audioTracks,
    getTracks: () => tracks,
  } as unknown as MediaStream
}

describe('requestDisplayMediaCapture', () => {
  it('requests display media with audio and returns a stream with audio tracks', async () => {
    const stream = createStream([createTrack('audio')])
    const mediaDevices = {
      getDisplayMedia: vi.fn().mockResolvedValue(stream),
    } as unknown as Pick<MediaDevices, 'getDisplayMedia'>

    const result = await requestDisplayMediaCapture({
      mediaDevices,
      mode: 'tab_audio',
    })

    expect(mediaDevices.getDisplayMedia).toHaveBeenCalledWith({
      audio: true,
      video: true,
    })
    expect(result).toMatchObject({
      ok: true,
      stream,
    })
  })

  it('maps browser permission denial to permission_denied', async () => {
    const mediaDevices = {
      getDisplayMedia: vi
        .fn()
        .mockRejectedValue(Object.assign(new Error('denied'), { name: 'NotAllowedError' })),
    } as unknown as Pick<MediaDevices, 'getDisplayMedia'>

    const result = await requestDisplayMediaCapture({
      mediaDevices,
      mode: 'tab_audio',
    })

    expect(result).toMatchObject({
      errorCode: 'permission_denied',
      ok: false,
    })
  })

  it('returns not_supported when display media capture is unavailable', async () => {
    const result = await requestDisplayMediaCapture({
      isSecureContext: true,
      mediaDevices: null,
      mode: 'tab_audio',
    })

    expect(result).toMatchObject({
      errorCode: 'not_supported',
      ok: false,
    })
  })

  it('stops tracks when capture succeeds without an audio track', async () => {
    const stream = createStream([])
    const mediaDevices = {
      getDisplayMedia: vi.fn().mockResolvedValue(stream),
    } as unknown as Pick<MediaDevices, 'getDisplayMedia'>

    const result = await requestDisplayMediaCapture({
      mediaDevices,
      mode: 'tab_audio',
    })

    expect(stream.getTracks()[0].stop).toHaveBeenCalledOnce()
    expect(result).toMatchObject({
      errorCode: 'no_audio_track',
      ok: false,
    })
  })
})
