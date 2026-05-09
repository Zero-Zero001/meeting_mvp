export const AUDIO_FORMAT = {
  sample_rate_hz: 16000,
  channels: 1,
  encoding: 'pcm16',
} as const

export const TARGET_SAMPLE_RATE_HZ = AUDIO_FORMAT.sample_rate_hz
export const AUDIO_FRAME_DURATION_MS = 100
export const PCM16_FRAME_SAMPLES =
  (TARGET_SAMPLE_RATE_HZ * AUDIO_FRAME_DURATION_MS) / 1000
export const PCM16_FRAME_BYTES = PCM16_FRAME_SAMPLES * 2
export const DEFAULT_EFFECTIVE_AUDIO_LEVEL_THRESHOLD = 0.015

export type Pcm16AudioFrame = {
  hasEffectiveAudio: boolean
  level: number
  pcm16: ArrayBuffer
  samples: Float32Array
}

export function mixToMono(channels: Float32Array[]): Float32Array {
  if (channels.length === 0) {
    return new Float32Array()
  }

  if (channels.length === 1) {
    return channels[0].slice()
  }

  const frameLength = Math.min(...channels.map((channel) => channel.length))
  const mono = new Float32Array(frameLength)

  for (let sampleIndex = 0; sampleIndex < frameLength; sampleIndex += 1) {
    let sum = 0
    for (const channel of channels) {
      sum += channel[sampleIndex]
    }
    mono[sampleIndex] = sum / channels.length
  }

  return mono
}

export function resampleLinear(
  input: Float32Array,
  inputSampleRate: number,
  outputSampleRate = TARGET_SAMPLE_RATE_HZ,
): Float32Array {
  if (input.length === 0) {
    return new Float32Array()
  }

  if (inputSampleRate === outputSampleRate) {
    return input.slice()
  }

  const outputLength = Math.max(
    1,
    Math.round((input.length * outputSampleRate) / inputSampleRate),
  )
  const output = new Float32Array(outputLength)
  const ratio = inputSampleRate / outputSampleRate

  for (let outputIndex = 0; outputIndex < outputLength; outputIndex += 1) {
    const sourceIndex = outputIndex * ratio
    const lowerIndex = Math.floor(sourceIndex)
    const upperIndex = Math.min(lowerIndex + 1, input.length - 1)
    const interpolation = sourceIndex - lowerIndex
    output[outputIndex] =
      input[lowerIndex] * (1 - interpolation) + input[upperIndex] * interpolation
  }

  return output
}

export function calculateRmsLevel(samples: Float32Array): number {
  if (samples.length === 0) {
    return 0
  }

  let sumSquares = 0
  for (const sample of samples) {
    sumSquares += sample * sample
  }

  return Math.sqrt(sumSquares / samples.length)
}

export function isEffectiveAudio(
  level: number,
  threshold = DEFAULT_EFFECTIVE_AUDIO_LEVEL_THRESHOLD,
): boolean {
  return level >= threshold
}

export function encodePcm16(samples: Float32Array): ArrayBuffer {
  const buffer = new ArrayBuffer(samples.length * 2)
  const view = new DataView(buffer)

  for (let index = 0; index < samples.length; index += 1) {
    const clamped = Math.max(-1, Math.min(1, samples[index]))
    const pcmValue =
      clamped < 0 ? Math.round(clamped * 0x8000) : Math.round(clamped * 0x7fff)
    view.setInt16(index * 2, pcmValue, true)
  }

  return buffer
}

export function createPcm16AudioFrames({
  channels,
  inputSampleRate,
  threshold = DEFAULT_EFFECTIVE_AUDIO_LEVEL_THRESHOLD,
}: {
  channels: Float32Array[]
  inputSampleRate: number
  threshold?: number
}): Pcm16AudioFrame[] {
  const mono = mixToMono(channels)
  const samples = resampleLinear(mono, inputSampleRate, TARGET_SAMPLE_RATE_HZ)
  const frames: Pcm16AudioFrame[] = []

  for (
    let offset = 0;
    offset + PCM16_FRAME_SAMPLES <= samples.length;
    offset += PCM16_FRAME_SAMPLES
  ) {
    const frameSamples = samples.slice(offset, offset + PCM16_FRAME_SAMPLES)
    const level = calculateRmsLevel(frameSamples)
    frames.push({
      hasEffectiveAudio: isEffectiveAudio(level, threshold),
      level,
      pcm16: encodePcm16(frameSamples),
      samples: frameSamples,
    })
  }

  return frames
}
