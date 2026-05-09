import { describe, expect, it } from 'vitest'

import {
  AUDIO_FORMAT,
  DEFAULT_EFFECTIVE_AUDIO_LEVEL_THRESHOLD,
  PCM16_FRAME_BYTES,
  PCM16_FRAME_SAMPLES,
  calculateRmsLevel,
  createPcm16AudioFrames,
  encodePcm16,
  isEffectiveAudio,
  mixToMono,
  resampleLinear,
} from './audio-frames'

describe('audio frame helpers', () => {
  it('uses the fixed Step 14 PCM16 audio format', () => {
    expect(AUDIO_FORMAT).toEqual({
      sample_rate_hz: 16000,
      channels: 1,
      encoding: 'pcm16',
    })
    expect(PCM16_FRAME_SAMPLES).toBe(1600)
    expect(PCM16_FRAME_BYTES).toBe(3200)
  })

  it('mixes multi-channel input to mono by averaging channels', () => {
    const mono = mixToMono([
      new Float32Array([1, 0, -1]),
      new Float32Array([0, 1, 1]),
    ])

    expect([...mono]).toEqual([0.5, 0.5, 0])
  })

  it('resamples input audio to 16 kHz with stable output length', () => {
    const input = new Float32Array(4800)
    input[0] = 0
    input[input.length - 1] = 1

    const resampled = resampleLinear(input, 48000, 16000)

    expect(resampled).toHaveLength(1600)
    expect(resampled[0]).toBeCloseTo(0)
  })

  it('encodes clamped samples as little-endian signed PCM16', () => {
    const pcm16 = encodePcm16(new Float32Array([-2, -1, 0, 0.5, 1, 2]))
    const view = new DataView(pcm16)

    expect(view.getInt16(0, true)).toBe(-32768)
    expect(view.getInt16(2, true)).toBe(-32768)
    expect(view.getInt16(4, true)).toBe(0)
    expect(view.getInt16(6, true)).toBe(16384)
    expect(view.getInt16(8, true)).toBe(32767)
    expect(view.getInt16(10, true)).toBe(32767)
  })

  it('calculates RMS level and applies the effective audio threshold', () => {
    expect(calculateRmsLevel(new Float32Array([0, 0, 0]))).toBe(0)
    expect(calculateRmsLevel(new Float32Array([1, -1]))).toBeCloseTo(1)
    expect(isEffectiveAudio(0.0149)).toBe(false)
    expect(isEffectiveAudio(DEFAULT_EFFECTIVE_AUDIO_LEVEL_THRESHOLD)).toBe(true)
  })

  it('creates 100ms PCM16 frames with audio-level metadata', () => {
    const frames = createPcm16AudioFrames({
      channels: [new Float32Array(4800).fill(0.1)],
      inputSampleRate: 48000,
    })

    expect(frames).toHaveLength(1)
    expect(frames[0].pcm16.byteLength).toBe(PCM16_FRAME_BYTES)
    expect(frames[0].samples).toHaveLength(PCM16_FRAME_SAMPLES)
    expect(frames[0].level).toBeGreaterThan(0.09)
    expect(frames[0].hasEffectiveAudio).toBe(true)
  })

  it('marks silent frames without treating them as uploadable audio', () => {
    const frames = createPcm16AudioFrames({
      channels: [new Float32Array(4800).fill(0)],
      inputSampleRate: 48000,
    })

    expect(frames).toHaveLength(1)
    expect(frames[0].level).toBe(0)
    expect(frames[0].hasEffectiveAudio).toBe(false)
  })
})
