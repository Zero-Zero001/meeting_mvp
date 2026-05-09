class Pcm16CaptureProcessor extends AudioWorkletProcessor {
  process(inputs) {
    const input = inputs[0]
    if (!input || input.length === 0) {
      return true
    }

    this.port.postMessage({
      channels: input.map((channel) => channel.slice(0)),
      inputSampleRate: sampleRate,
      type: 'audio_samples',
    })

    return true
  }
}

registerProcessor('pcm16-capture-processor', Pcm16CaptureProcessor)
