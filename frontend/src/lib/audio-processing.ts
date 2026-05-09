import {
  DEFAULT_EFFECTIVE_AUDIO_LEVEL_THRESHOLD,
  PCM16_FRAME_SAMPLES,
  calculateRmsLevel,
  encodePcm16,
  isEffectiveAudio,
  mixToMono,
  resampleLinear,
  type Pcm16AudioFrame,
} from './audio-frames'

const AUDIO_WORKLET_MODULE_URL = '/audio-worklet/pcm16-processor.js'
const AUDIO_WORKLET_PROCESSOR_NAME = 'pcm16-capture-processor'

export const SILENCE_WARNING_TIMEOUT_MS = 30_000

export type AudioLevelState = {
  hasEffectiveAudio: boolean
  level: number
  silenceWarning: boolean
}

export type AudioFrameMetadata = {
  level: number
}

export type AudioSampleMessage = {
  channels: ArrayLike<number>[]
  inputSampleRate: number
  type?: 'audio_samples'
}

export type AudioSampleProcessor = {
  push: (message: AudioSampleMessage) => Pcm16AudioFrame[]
}

export type AudioProcessingController = {
  stop: () => Promise<void>
}

type AudioFrameCallback = (
  frame: ArrayBuffer,
  metadata: AudioFrameMetadata,
) => void

type AudioLevelCallback = (state: AudioLevelState) => void

type MinimalMediaStreamAudioSourceNode = {
  connect: (destinationNode: AudioNode) => unknown
  disconnect: () => void
}

type MinimalAudioContext = {
  audioWorklet?: {
    addModule: (moduleURL: string) => Promise<void>
  }
  close: () => Promise<void>
  createMediaStreamSource: (
    stream: MediaStream,
  ) => MinimalMediaStreamAudioSourceNode
  resume?: () => Promise<void>
  sampleRate: number
  state?: string
}

type MinimalAudioWorkletNode = {
  disconnect: () => void
  port: {
    onmessage: ((event: MessageEvent) => void) | null
  }
}

type AudioContextFactory = () => MinimalAudioContext

type AudioWorkletNodeFactory = (
  context: MinimalAudioContext,
) => MinimalAudioWorkletNode

export type StartAudioProcessingOptions = {
  audioContextFactory?: AudioContextFactory
  audioWorkletModuleUrl?: string
  audioWorkletNodeFactory?: AudioWorkletNodeFactory
  onFrame: AudioFrameCallback
  onLevel?: AudioLevelCallback
  onSilenceWarning?: () => void
  silenceTimeoutMs?: number
  stream: MediaStream
  threshold?: number
}

export class AudioProcessingUnsupportedError extends Error {
  constructor(message = 'AudioWorklet is not supported in this browser.') {
    super(message)
    this.name = 'AudioProcessingUnsupportedError'
  }
}

export class AudioProcessingFailedError extends Error {
  constructor(message = 'Audio processing failed.') {
    super(message)
    this.name = 'AudioProcessingFailedError'
  }
}

type SilenceMonitorOptions = {
  onWarning: () => void
  timeoutMs?: number
}

export function createSilenceMonitor({
  onWarning,
  timeoutMs = SILENCE_WARNING_TIMEOUT_MS,
}: SilenceMonitorOptions) {
  let active = false
  let timer: ReturnType<typeof setTimeout> | null = null

  function clearTimer() {
    if (timer !== null) {
      clearTimeout(timer)
      timer = null
    }
  }

  function schedule() {
    clearTimer()
    timer = setTimeout(() => {
      timer = null
      if (active) {
        onWarning()
      }
    }, timeoutMs)
  }

  return {
    markEffectiveAudio() {
      if (active) {
        schedule()
      }
    },
    start() {
      active = true
      schedule()
    },
    stop() {
      active = false
      clearTimer()
    },
  }
}

function toFloat32Array(channel: ArrayLike<number>): Float32Array {
  return channel instanceof Float32Array ? channel : Float32Array.from(channel)
}

function appendSamples(
  left: Float32Array,
  right: Float32Array,
): Float32Array {
  if (left.length === 0) {
    return right
  }

  if (right.length === 0) {
    return left
  }

  const combined = new Float32Array(left.length + right.length)
  combined.set(left)
  combined.set(right, left.length)
  return combined
}

export function createAudioSampleProcessor({
  onFrame,
  onLevel,
  threshold = DEFAULT_EFFECTIVE_AUDIO_LEVEL_THRESHOLD,
}: {
  onFrame: AudioFrameCallback
  onLevel?: AudioLevelCallback
  threshold?: number
}): AudioSampleProcessor {
  let pendingSamples = new Float32Array()

  return {
    push(message) {
      const channels = message.channels.map(toFloat32Array)
      const mono = mixToMono(channels)
      const resampled = resampleLinear(mono, message.inputSampleRate)
      const samples = appendSamples(pendingSamples, resampled)
      const frames: Pcm16AudioFrame[] = []
      let offset = 0

      while (offset + PCM16_FRAME_SAMPLES <= samples.length) {
        const frameSamples = samples.slice(offset, offset + PCM16_FRAME_SAMPLES)
        const level = calculateRmsLevel(frameSamples)
        const frame: Pcm16AudioFrame = {
          hasEffectiveAudio: isEffectiveAudio(level, threshold),
          level,
          pcm16: encodePcm16(frameSamples),
          samples: frameSamples,
        }

        frames.push(frame)
        onLevel?.({
          hasEffectiveAudio: frame.hasEffectiveAudio,
          level,
          silenceWarning: false,
        })

        if (frame.hasEffectiveAudio) {
          onFrame(frame.pcm16, { level })
        }

        offset += PCM16_FRAME_SAMPLES
      }

      pendingSamples = samples.slice(offset)
      return frames
    },
  }
}

function getDefaultAudioContextFactory(): AudioContextFactory {
  return () => {
    const audioContextConstructor =
      typeof window === 'undefined'
        ? undefined
        : window.AudioContext ??
          (window as Window & { webkitAudioContext?: typeof AudioContext })
            .webkitAudioContext

    if (!audioContextConstructor) {
      throw new AudioProcessingUnsupportedError()
    }

    return new audioContextConstructor()
  }
}

function getDefaultAudioWorkletNodeFactory(): AudioWorkletNodeFactory {
  return (context) =>
    new AudioWorkletNode(context as AudioContext, AUDIO_WORKLET_PROCESSOR_NAME, {
      numberOfInputs: 1,
      numberOfOutputs: 0,
    })
}

function isAudioSamplePayload(payload: unknown): payload is AudioSampleMessage {
  if (typeof payload !== 'object' || payload === null) {
    return false
  }

  const candidate = payload as Partial<AudioSampleMessage> & {
    sampleRate?: number
  }
  return Array.isArray(candidate.channels)
}

export async function startAudioProcessing({
  audioContextFactory = getDefaultAudioContextFactory(),
  audioWorkletModuleUrl = AUDIO_WORKLET_MODULE_URL,
  audioWorkletNodeFactory = getDefaultAudioWorkletNodeFactory(),
  onFrame,
  onLevel,
  onSilenceWarning,
  silenceTimeoutMs = SILENCE_WARNING_TIMEOUT_MS,
  stream,
  threshold = DEFAULT_EFFECTIVE_AUDIO_LEVEL_THRESHOLD,
}: StartAudioProcessingOptions): Promise<AudioProcessingController> {
  let context: MinimalAudioContext
  try {
    context = audioContextFactory()
  } catch (error) {
    if (error instanceof AudioProcessingUnsupportedError) {
      throw error
    }
    throw new AudioProcessingUnsupportedError()
  }

  if (!context.audioWorklet) {
    await context.close()
    throw new AudioProcessingUnsupportedError()
  }

  try {
    await context.audioWorklet.addModule(audioWorkletModuleUrl)
    if (context.state === 'suspended') {
      await context.resume?.()
    }
  } catch (error) {
    await context.close()
    if (error instanceof AudioProcessingUnsupportedError) {
      throw error
    }
    throw new AudioProcessingFailedError()
  }

  const source = context.createMediaStreamSource(stream)
  const workletNode = audioWorkletNodeFactory(context)
  let lastLevel = 0
  const silenceMonitor = createSilenceMonitor({
    onWarning: () => {
      onLevel?.({
        hasEffectiveAudio: false,
        level: lastLevel,
        silenceWarning: true,
      })
      onSilenceWarning?.()
    },
    timeoutMs: silenceTimeoutMs,
  })
  const processor = createAudioSampleProcessor({
    onFrame: (frame, metadata) => {
      silenceMonitor.markEffectiveAudio()
      onFrame(frame, metadata)
    },
    onLevel: (state) => {
      lastLevel = state.level
      onLevel?.(state)
    },
    threshold,
  })

  workletNode.port.onmessage = (event) => {
    const payload = event.data
    if (!isAudioSamplePayload(payload)) {
      return
    }

    processor.push({
      channels: payload.channels,
      inputSampleRate:
        payload.inputSampleRate ??
        (payload as AudioSampleMessage & { sampleRate?: number }).sampleRate ??
        context.sampleRate,
      type: 'audio_samples',
    })
  }

  source.connect(workletNode as unknown as AudioNode)
  silenceMonitor.start()

  return {
    async stop() {
      silenceMonitor.stop()
      workletNode.port.onmessage = null
      workletNode.disconnect()
      source.disconnect()
      await context.close()
    },
  }
}
