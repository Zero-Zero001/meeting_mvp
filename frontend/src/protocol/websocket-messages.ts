import { z } from 'zod'

export type AudioChunkFrame = ArrayBuffer | ArrayBufferView | Blob

const nonNegativeInteger = z.number().int().nonnegative()

export const audioFormatSchema = z
  .object({
    sample_rate_hz: z.literal(16000),
    channels: z.literal(1),
    encoding: z.literal('pcm16'),
  })
  .strict()

export const sessionStartMessageSchema = z
  .object({
    type: z.literal('session_start'),
    client_id: z.string().min(1),
    capture_mode: z.union([z.literal('tab_audio'), z.literal('system_audio')]),
    source_platform: z.union([
      z.literal('google_meet'),
      z.literal('teams_web'),
      z.literal('zoom_web'),
      z.literal('tencent_meeting_web'),
      z.literal('unknown'),
    ]),
    audio_format: audioFormatSchema,
  })
  .strict()

export const heartbeatMessageSchema = z
  .object({
    type: z.literal('heartbeat'),
    session_id: z.string().min(1),
  })
  .strict()

export const sessionStopMessageSchema = z
  .object({
    type: z.literal('session_stop'),
    session_id: z.string().min(1),
  })
  .strict()

export const clientMessageSchema = z.discriminatedUnion('type', [
  sessionStartMessageSchema,
  heartbeatMessageSchema,
  sessionStopMessageSchema,
])

export const sessionStartedMessageSchema = z
  .object({
    type: z.literal('session_started'),
    session_id: z.string().min(1),
    archive_token: z.string().min(1),
    archive_url: z.string().min(1),
    remaining_seconds_today: nonNegativeInteger,
  })
  .strict()

export const quotaUpdateMessageSchema = z
  .object({
    type: z.literal('quota_update'),
    remaining_seconds_today: nonNegativeInteger,
  })
  .strict()

export const audioStatusMessageSchema = z
  .object({
    type: z.literal('audio_status'),
    has_audio: z.boolean(),
    level: z.number().min(0).max(1).nullable().optional(),
  })
  .strict()

export const asrInterimMessageSchema = z
  .object({
    type: z.literal('asr_interim'),
    text: z.string(),
  })
  .strict()

export const asrFinalMessageSchema = z
  .object({
    type: z.literal('asr_final'),
    sequence: nonNegativeInteger,
    start_ms: nonNegativeInteger,
    end_ms: nonNegativeInteger,
    text: z.string(),
    confidence: z.number().min(0).max(1).nullable().optional(),
  })
  .strict()

export const translationInterimMessageSchema = z
  .object({
    type: z.literal('translation_interim'),
    text: z.string(),
  })
  .strict()

export const segmentFinalMessageSchema = z
  .object({
    type: z.literal('segment_final'),
    segment_id: z.string().min(1),
    sequence: nonNegativeInteger,
    start_ms: nonNegativeInteger,
    end_ms: nonNegativeInteger,
    english_text_final: z.string(),
    chinese_text_final: z.string(),
  })
  .strict()

export const keySentenceUpdateMessageSchema = z
  .object({
    type: z.literal('key_sentence_update'),
    text: z.string(),
  })
  .strict()

export const timelineItemSchema = z
  .object({
    id: z.string().min(1),
    item_type: z.string().min(1),
    timestamp_ms: nonNegativeInteger,
    text: z.string(),
    segment_id: z.string().min(1).nullable().optional(),
  })
  .strict()

export const timelineUpdateMessageSchema = z
  .object({
    type: z.literal('timeline_update'),
    items: z.array(timelineItemSchema),
  })
  .strict()

export const warningMessageSchema = z
  .object({
    type: z.literal('warning'),
    code: z.string().min(1),
    message: z.string().nullable().optional(),
  })
  .strict()

export const errorMessageSchema = z
  .object({
    type: z.literal('error'),
    code: z.string().min(1),
    message: z.string().nullable().optional(),
  })
  .strict()

export const sessionClosedMessageSchema = z
  .object({
    type: z.literal('session_closed'),
    reason: z.string().min(1),
  })
  .strict()

export const serverMessageSchema = z.discriminatedUnion('type', [
  sessionStartedMessageSchema,
  quotaUpdateMessageSchema,
  audioStatusMessageSchema,
  asrInterimMessageSchema,
  asrFinalMessageSchema,
  translationInterimMessageSchema,
  segmentFinalMessageSchema,
  keySentenceUpdateMessageSchema,
  timelineUpdateMessageSchema,
  warningMessageSchema,
  errorMessageSchema,
  sessionClosedMessageSchema,
])

export type ClientMessage = z.infer<typeof clientMessageSchema>
export type ServerMessage = z.infer<typeof serverMessageSchema>

export function parseClientMessage(payload: unknown): ClientMessage {
  return clientMessageSchema.parse(payload)
}

export function parseServerMessage(payload: unknown): ServerMessage {
  return serverMessageSchema.parse(payload)
}

export function isAudioChunkFrame(payload: unknown): payload is AudioChunkFrame {
  return (
    payload instanceof ArrayBuffer ||
    ArrayBuffer.isView(payload) ||
    payload instanceof Blob
  )
}
