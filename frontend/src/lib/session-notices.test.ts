import { describe, expect, it } from 'vitest'

import {
  noticeFromAudioPipelineError,
  noticeFromCaptureFailure,
  noticeFromCode,
  noticeFromSessionClosedReason,
  noticeFromWarningMessage,
  noticeFromWebSocketError,
} from './session-notices'

describe('session notices', () => {
  it('maps capture permission denial to a retryable user notice', () => {
    const notice = noticeFromCaptureFailure('permission_denied', {
      captureMode: 'tab_audio',
      sourcePlatform: 'google_meet',
    })

    expect(notice).toMatchObject({
      code: 'permission_denied',
      severity: 'warning',
      title: '无法开始捕获音频',
    })
    expect(notice.message).toContain('不会创建会议或消耗额度')
    expect(notice.action).toContain('重新点击“开始捕获”')
  })

  it('guides Tencent Meeting tab-audio failures to system audio fallback', () => {
    const notice = noticeFromCaptureFailure('no_audio_track', {
      captureMode: 'tab_audio',
      sourcePlatform: 'tencent_meeting_web',
    })

    expect(notice.title).toBe('没有捕获到会议声音')
    expect(notice.action).toContain('切换到系统音频模式后重新捕获')
    expect(notice.action).toContain('腾讯会议网页版')
  })

  it('maps silence timeout to a non-blocking audio warning', () => {
    const notice = noticeFromAudioPipelineError('audio_silent_timeout', {
      captureMode: 'system_audio',
      sourcePlatform: 'unknown',
    })

    expect(notice).toMatchObject({
      code: 'audio_silent_timeout',
      severity: 'warning',
      title: '暂未检测到会议声音',
    })
    expect(notice.action).toContain('检查共享音频')
  })

  it('maps provider warnings without making the session unrecoverable', () => {
    const interimNotice = noticeFromWarningMessage({
      code: 'qwen_interim_translation_failed',
      message: null,
      type: 'warning',
    })
    const finalNotice = noticeFromWarningMessage({
      code: 'qwen_final_translation_failed',
      message: '中文正式翻译失败，英文 final 已归档待重试。',
      type: 'warning',
    })

    expect(interimNotice.severity).toBe('warning')
    expect(interimNotice.action).toContain('继续会议')
    expect(finalNotice.title).toBe('正式中文翻译失败')
    expect(finalNotice.action).toContain('后续重试')
  })

  it('maps quota and budget denials to blocking notices', () => {
    const quotaNotice = noticeFromWebSocketError(
      Object.assign(new Error('quota exhausted'), {
        code: 'daily_quota_exhausted',
      }),
    )
    const budgetNotice = noticeFromCode('budget_fuse_triggered')

    expect(quotaNotice).toMatchObject({
      code: 'daily_quota_exhausted',
      severity: 'error',
      title: '今日免费额度已用完',
    })
    expect(budgetNotice).toMatchObject({
      code: 'budget_fuse_triggered',
      severity: 'error',
      title: '当前测试额度已暂停新会议',
    })
    expect(budgetNotice.action).toContain('已有记录仍可查看')
  })

  it('maps websocket resume failure and export failure to actionable notices', () => {
    const resumeNotice = noticeFromSessionClosedReason('session_resume_failed')
    const exportNotice = noticeFromCode('export_failed')

    expect(resumeNotice).toMatchObject({
      code: 'session_resume_failed',
      severity: 'error',
      title: '断线恢复失败',
    })
    expect(resumeNotice?.action).toContain('已归档片段会保留')
    expect(exportNotice).toMatchObject({
      code: 'export_failed',
      severity: 'warning',
      title: '导出暂时失败',
    })
    expect(exportNotice.action).toContain('重试导出')
  })

  it('does not show an error notice for user-stopped sessions', () => {
    expect(noticeFromSessionClosedReason('user_stopped')).toBeNull()
  })
})
