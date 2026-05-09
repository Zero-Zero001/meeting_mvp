import { afterEach, describe, expect, it, vi } from 'vitest'

import { PCM16_FRAME_BYTES } from './audio-frames'
import {
  SILENCE_WARNING_TIMEOUT_MS,
  createAudioSampleProcessor,
  createSilenceMonitor,
  startAudioProcessing,
  type AudioSampleMessage,
} from './audio-processing'

function samples(value: number, length = 4800) {
  return new Float32Array(length).fill(value)
}

describe('audio processing pipeline', () => {
  afterEach(() => {
    vi.useRealTimers()
  })

  it('emits binary PCM16 frames for effective audio samples', () => {
    const frames: ArrayBuffer[] = []
    const levels: number[] = []
    const processor = createAudioSampleProcessor({
      onFrame: (frame) => frames.push(frame),
      onLevel: ({ level }) => levels.push(level),
    })

    processor.push({
      channels: [samples(0.1)],
      inputSampleRate: 48000,
    })

    expect(frames).toHaveLength(1)
    expect(frames[0].byteLength).toBe(PCM16_FRAME_BYTES)
    expect(levels.at(-1)).toBeGreaterThan(0.09)
  })

  it('does not emit binary frames for silent samples', () => {
    const onFrame = vi.fn()
    const onLevel = vi.fn()
    const processor = createAudioSampleProcessor({
      onFrame,
      onLevel,
    })

    processor.push({
      channels: [samples(0)],
      inputSampleRate: 48000,
    })

    expect(onFrame).not.toHaveBeenCalled()
    expect(onLevel).toHaveBeenLastCalledWith({
      hasEffectiveAudio: false,
      level: 0,
      silenceWarning: false,
    })
  })

  it('carries partial samples across worklet messages to keep 100ms frames', () => {
    const frames: ArrayBuffer[] = []
    const processor = createAudioSampleProcessor({
      onFrame: (frame) => frames.push(frame),
    })
    const chunk: AudioSampleMessage = {
      channels: [samples(0.1, 2400)],
      inputSampleRate: 48000,
    }

    processor.push(chunk)
    expect(frames).toHaveLength(0)

    processor.push(chunk)
    expect(frames).toHaveLength(1)
  })

  it('raises a silence warning after 30 seconds without effective audio', () => {
    vi.useFakeTimers()
    const onWarning = vi.fn()
    const monitor = createSilenceMonitor({ onWarning })

    monitor.start()
    vi.advanceTimersByTime(SILENCE_WARNING_TIMEOUT_MS - 1)
    expect(onWarning).not.toHaveBeenCalled()

    vi.advanceTimersByTime(1)
    expect(onWarning).toHaveBeenCalledOnce()

    monitor.stop()
  })

  it('resets the silence timer when effective audio is detected', () => {
    vi.useFakeTimers()
    const onWarning = vi.fn()
    const monitor = createSilenceMonitor({ onWarning })

    monitor.start()
    vi.advanceTimersByTime(20_000)
    monitor.markEffectiveAudio()
    vi.advanceTimersByTime(20_000)

    expect(onWarning).not.toHaveBeenCalled()

    vi.advanceTimersByTime(10_000)
    expect(onWarning).toHaveBeenCalledOnce()
    monitor.stop()
  })

  it('stops the worklet graph and closes the audio context', async () => {
    const stream = {} as MediaStream
    const source = {
      connect: vi.fn(),
      disconnect: vi.fn(),
    }
    const node = {
      disconnect: vi.fn(),
      port: {
        onmessage: null as ((event: MessageEvent) => void) | null,
      },
    }
    const context = {
      audioWorklet: {
        addModule: vi.fn().mockResolvedValue(undefined),
      },
      close: vi.fn().mockResolvedValue(undefined),
      createMediaStreamSource: vi.fn(() => source),
      resume: vi.fn().mockResolvedValue(undefined),
      sampleRate: 48000,
      state: 'suspended',
    }

    const controller = await startAudioProcessing({
      audioContextFactory: () => context,
      audioWorkletNodeFactory: () => node,
      onFrame: vi.fn(),
      stream,
    })

    expect(context.audioWorklet.addModule).toHaveBeenCalled()
    expect(source.connect).toHaveBeenCalledWith(node)

    await controller.stop()

    expect(node.disconnect).toHaveBeenCalled()
    expect(source.disconnect).toHaveBeenCalled()
    expect(context.close).toHaveBeenCalled()
  })
})
