import { describe, expect, it } from 'vitest'

import {
  isAudioChunkFrame,
  parseClientMessage,
  parseServerMessage,
} from './websocket-messages'

const validAudioFormat = {
  sample_rate_hz: 16000,
  channels: 1,
  encoding: 'pcm16',
}

describe('websocket message schema', () => {
  it('parses a valid session_start client message', () => {
    const message = parseClientMessage({
      type: 'session_start',
      client_id: '77777777-7777-4777-8777-777777777777',
      capture_mode: 'tab_audio',
      source_platform: 'google_meet',
      audio_format: validAudioFormat,
    })

    expect(message).toMatchObject({
      type: 'session_start',
      client_id: '77777777-7777-4777-8777-777777777777',
      audio_format: validAudioFormat,
    })
  })

  it('rejects session_start when the audio format is not fixed PCM16', () => {
    expect(() =>
      parseClientMessage({
        type: 'session_start',
        client_id: '77777777-7777-4777-8777-777777777777',
        capture_mode: 'tab_audio',
        source_platform: 'google_meet',
        audio_format: {
          sample_rate_hz: 48000,
          channels: 2,
          encoding: 'opus',
        },
      }),
    ).toThrow()
  })

  it('rejects client messages with missing required fields', () => {
    expect(() =>
      parseClientMessage({
        type: 'session_start',
        client_id: '77777777-7777-4777-8777-777777777777',
        capture_mode: 'tab_audio',
        audio_format: validAudioFormat,
      }),
    ).toThrow()
  })

  it('rejects unknown client message types', () => {
    expect(() => parseClientMessage({ type: 'provider_start' })).toThrow()
  })

  it('parses session_resume client messages', () => {
    const message = parseClientMessage({
      type: 'session_resume',
      client_id: '77777777-7777-4777-8777-777777777777',
      session_id: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
      archive_token: 'archive-token',
      audio_format: validAudioFormat,
    })

    expect(message).toMatchObject({
      type: 'session_resume',
      session_id: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
      archive_token: 'archive-token',
    })
  })

  it('rejects session_resume with extra fields', () => {
    expect(() =>
      parseClientMessage({
        type: 'session_resume',
        client_id: '77777777-7777-4777-8777-777777777777',
        session_id: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
        archive_token: 'archive-token',
        audio_format: validAudioFormat,
        source_platform: 'google_meet',
      }),
    ).toThrow()
  })

  it('identifies WebSocket binary frames as audio chunks', () => {
    expect(isAudioChunkFrame(new Uint8Array([0, 1, 2, 3]).buffer)).toBe(true)
    expect(isAudioChunkFrame(new Uint8Array([0, 1, 2, 3]))).toBe(true)
    expect(isAudioChunkFrame({ type: 'audio_chunk' })).toBe(false)
  })

  it('parses required session_started response fields', () => {
    const message = parseServerMessage({
      type: 'session_started',
      session_id: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
      archive_token: 'archive-token',
      archive_url:
        '/archive/aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa?token=archive-token',
      remaining_seconds_today: 1800,
    })

    expect(message).toMatchObject({
      type: 'session_started',
      remaining_seconds_today: 1800,
    })
  })

  it('parses session_resumed response fields', () => {
    const message = parseServerMessage({
      type: 'session_resumed',
      session_id: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
      archive_url:
        '/archive/aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa?token=archive-token',
      remaining_seconds_today: 1800,
    })

    expect(message).toMatchObject({
      type: 'session_resumed',
      session_id: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
      remaining_seconds_today: 1800,
    })
  })

  it('parses segment_final response fields', () => {
    const message = parseServerMessage({
      type: 'segment_final',
      segment_id: 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',
      sequence: 1,
      start_ms: 1200,
      end_ms: 3600,
      english_text_final: 'We need to align on the timeline.',
      chinese_text_final: 'Timeline alignment translation.',
    })

    expect(message).toMatchObject({
      type: 'segment_final',
      sequence: 1,
      english_text_final: 'We need to align on the timeline.',
    })
  })

  it('parses asr_final response fields', () => {
    const message = parseServerMessage({
      type: 'asr_final',
      sequence: 1,
      start_ms: 0,
      end_ms: 2400,
      text: 'We need to align on the timeline.',
      confidence: 0.92,
    })

    expect(message).toMatchObject({
      type: 'asr_final',
      sequence: 1,
      start_ms: 0,
      end_ms: 2400,
      text: 'We need to align on the timeline.',
      confidence: 0.92,
    })
  })

  it('rejects invalid asr_final confidence', () => {
    expect(() =>
      parseServerMessage({
        type: 'asr_final',
        sequence: 1,
        start_ms: 0,
        end_ms: 2400,
        text: 'We need to align on the timeline.',
        confidence: 1.5,
      }),
    ).toThrow()
  })

  it('parses nullable optional server fields emitted by Pydantic defaults', () => {
    const audioStatus = parseServerMessage({
      type: 'audio_status',
      has_audio: false,
      level: null,
    })
    const warning = parseServerMessage({
      type: 'warning',
      code: 'quota_near_limit',
      message: null,
    })
    const timeline = parseServerMessage({
      type: 'timeline_update',
      items: [
        {
          id: 'timeline-1',
          item_type: 'segment',
          timestamp_ms: 1200,
          text: 'A final segment was created.',
          segment_id: null,
        },
      ],
    })

    expect(audioStatus).toMatchObject({ type: 'audio_status', level: null })
    expect(warning).toMatchObject({ type: 'warning', message: null })
    expect(timeline).toMatchObject({
      type: 'timeline_update',
      items: [{ segment_id: null }],
    })
  })

  it('rejects unknown server message types', () => {
    expect(() => parseServerMessage({ type: 'provider_debug' })).toThrow()
  })
})
