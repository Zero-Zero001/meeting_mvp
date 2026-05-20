import type { CaptureFailureCode } from './audio-capture'
import type { MeetingWebSocketError } from './meeting-websocket'
import type { ServerMessage } from '@/protocol/websocket-messages'

export type NoticeSeverity = 'info' | 'warning' | 'error'

export type SessionNotice = {
  action: string
  code: string
  message: string
  severity: NoticeSeverity
  title: string
}

type CaptureMode = 'tab_audio' | 'system_audio'
type SourcePlatform =
  | 'google_meet'
  | 'teams_web'
  | 'zoom_web'
  | 'tencent_meeting_web'
  | 'unknown'

type NoticeContext = {
  captureMode: CaptureMode
  sourcePlatform: SourcePlatform
}

type WarningMessage = Extract<ServerMessage, { type: 'warning' }>

const DEFAULT_CONTEXT: NoticeContext = {
  captureMode: 'tab_audio',
  sourcePlatform: 'unknown',
}

export function noticeFromCaptureFailure(
  code: CaptureFailureCode,
  context: NoticeContext = DEFAULT_CONTEXT,
): SessionNotice {
  switch (code) {
    case 'permission_denied':
      return {
        action: '允许浏览器共享后，重新点击“开始捕获”。',
        code,
        message: '浏览器拒绝了屏幕共享授权，不会创建会议或消耗额度。',
        severity: 'warning',
        title: '无法开始捕获音频',
      }
    case 'no_audio_track':
      return {
        action: noAudioTrackAction(context),
        code,
        message: '已选择共享目标，但浏览器没有返回音频轨道，不会上传音频或消耗额度。',
        severity: 'warning',
        title: '没有捕获到会议声音',
      }
    case 'not_supported':
      return {
        action: '请使用 Windows Chrome 或 Edge，并通过 HTTPS 页面重新打开工具。',
        code,
        message: '当前浏览器环境不支持屏幕共享音频捕获。',
        severity: 'error',
        title: '当前浏览器不支持音频捕获',
      }
    case 'capture_failed':
      return {
        action: '检查浏览器共享窗口后稍后重试；如果仍失败，切换系统音频模式。',
        code,
        message: '浏览器没有成功返回可用的会议音频。',
        severity: 'warning',
        title: '捕获会议音频失败',
      }
  }
}

export function noticeFromAudioPipelineError(
  code: string | null,
  context: NoticeContext = DEFAULT_CONTEXT,
): SessionNotice | null {
  switch (code) {
    case 'identity_not_ready':
      return {
        action: '等待匿名身份同步完成后再开始捕获。',
        code,
        message: '本地身份还没有和服务端同步，暂时不能上传会议音频。',
        severity: 'warning',
        title: '匿名身份尚未同步',
      }
    case 'websocket_failed':
      return noticeFromCode('websocket_failed')
    case 'audio_processing_unsupported':
      return {
        action: '请使用 Windows Chrome 或 Edge 的最新版重新打开页面。',
        code,
        message: '当前浏览器不支持实时音频处理所需的 AudioWorklet。',
        severity: 'error',
        title: '音频处理不可用',
      }
    case 'audio_processing_failed':
      return {
        action: '结束当前捕获后重新开始；如果仍失败，请刷新页面。',
        code,
        message: '音频处理管线启动失败，尚未上传原始音频。',
        severity: 'error',
        title: '音频处理启动失败',
      }
    case 'audio_silent_timeout':
      return {
        action:
          context.captureMode === 'tab_audio'
            ? '检查共享时是否勾选共享音频；必要时切换系统音频。'
            : '检查共享音频和会议中是否有人讲话，并确认系统音量没有静音。',
        code,
        message: '已捕获窗口或屏幕，但 30 秒内没有有效声音，静音帧不会上传。',
        severity: 'warning',
        title: '暂未检测到会议声音',
      }
    default:
      return null
  }
}

export function noticeFromWarningMessage(message: WarningMessage): SessionNotice {
  const baseNotice = noticeFromCode(message.code, 'warning')
  if (message.message == null || message.message.trim() === '') {
    return baseNotice
  }

  return {
    ...baseNotice,
    message: message.message,
  }
}

export function noticeFromWebSocketError(error: Error): SessionNotice {
  const maybeError = error as Partial<MeetingWebSocketError>
  return noticeFromCode(maybeError.code ?? 'websocket_failed', 'error')
}

export function noticeFromSessionClosedReason(reason: string): SessionNotice | null {
  if (reason === 'user_stopped') {
    return null
  }

  return noticeFromCode(reason, 'error')
}

export function noticeFromCode(
  code: string,
  severityOverride?: NoticeSeverity,
): SessionNotice {
  const fallbackSeverity = severityOverride ?? severityForCode(code)
  switch (code) {
    case 'daily_quota_exhausted':
      return {
        action: '明天额度恢复后再开始新会议；已有记录仍可查看。',
        code,
        message: '今天的免费会议时长已经用完，系统不会继续创建新会议。',
        severity: 'error',
        title: '今日免费额度已用完',
      }
    case 'active_session_limit_reached':
      return {
        action: '请先结束另一个正在进行的会议，再开始新会议。',
        code,
        message: '同一个匿名用户一次只能开启一场实时会议。',
        severity: 'error',
        title: '已有会议正在进行',
      }
    case 'budget_fuse_triggered':
      return {
        action: '稍后再试；已有记录仍可查看，后续导出能力不受此提示清空。',
        code,
        message: '当前测试额度已达到预算保护阈值，系统暂时拒绝新会议。',
        severity: 'error',
        title: '当前测试额度已暂停新会议',
      }
    case 'qwen_asr_error':
      return {
        action: '稍后重新开始会议；已经归档的 final 片段会保留。',
        code,
        message: '核心英文转写连接异常，本场实时转写无法继续。',
        severity: 'error',
        title: '英文转写服务暂时不可用',
      }
    case 'qwen_asr_disabled':
      return {
        action: '稍后重试；维护者重新启用英文转写后再开始会议。',
        code,
        message: '当前英文实时转写开关已关闭，系统不会创建新会议或消耗额度。',
        severity: 'error',
        title: '英文转写服务已关闭',
      }
    case 'qwen_interim_translation_disabled':
      return {
        action: '可以继续会议；以英文 interim 和中文 final 为准。',
        code,
        message: '当前不会生成中文 interim，英文转写和正式中文 final 会继续。',
        severity: 'warning',
        title: '中文临时理解已关闭',
      }
    case 'qwen_interim_translation_failed':
      return {
        action: '继续会议即可；英文转写和正式中文翻译不会因此停止。',
        code,
        message: '中文临时理解暂时不可用，英文转写会继续。',
        severity: 'warning',
        title: '中文临时理解暂时不可用',
      }
    case 'qwen_final_translation_disabled':
      return {
        action: '可以继续会议；服务恢复后后台补译会补齐正式中文。',
        code,
        message: '中文正式翻译已关闭，英文 final 已归档待后续补译。',
        severity: 'warning',
        title: '正式中文翻译已关闭',
      }
    case 'qwen_final_translation_failed':
      return {
        action: '英文 final 已保留，后续重试能力会补齐正式中文。',
        code,
        message: '中文正式翻译失败，英文 final 已归档待重试。',
        severity: 'warning',
        title: '正式中文翻译失败',
      }
    case 'session_resume_failed':
      return {
        action: '请重新开始会议；已归档片段会保留，不会被当前错误清空。',
        code,
        message: '浏览器断线后无法恢复原来的实时连接。',
        severity: 'error',
        title: '断线恢复失败',
      }
    case 'browser_disconnected':
      return {
        action: '如果会议仍在继续，请重新开始捕获；已归档片段会保留。',
        code,
        message: '浏览器连接已断开，后端已清理实时会话。',
        severity: 'error',
        title: '会议连接已断开',
      }
    case 'websocket_reconnecting':
      return {
        action: '保持页面打开，系统会尝试恢复同一场会议。',
        code,
        message: '浏览器到后端的实时连接正在恢复。',
        severity: 'warning',
        title: '正在恢复实时连接',
      }
    case 'websocket_failed':
      return {
        action: '检查网络后稍后重试；如果已有归档片段，它们会保留。',
        code,
        message: '浏览器无法建立或维持实时会议连接。',
        severity: 'error',
        title: '实时连接失败',
      }
    case 'export_failed':
      return {
        action: '稍后重试导出；当前页面中的会议内容不会丢失。',
        code,
        message: '导出文件暂时没有生成成功。',
        severity: 'warning',
        title: '导出暂时失败',
      }
    case 'client_not_initialized':
      return {
        action: '刷新页面，等待匿名身份同步后再开始会议。',
        code,
        message: '服务端没有找到当前匿名身份。',
        severity: 'error',
        title: '匿名身份未初始化',
      }
    case 'configuration_error':
      return {
        action: '稍后重试；如果持续出现，请联系维护者检查后端配置。',
        code,
        message: '后端运行配置不完整，暂时不能创建实时会议。',
        severity: 'error',
        title: '服务配置暂不可用',
      }
    default:
      return {
        action:
          fallbackSeverity === 'error'
            ? '稍后重试；已经归档的内容会保留。'
            : '可以继续会议，并留意后续提示。',
        code,
        message:
          fallbackSeverity === 'error'
            ? '会话遇到不可继续的问题。'
            : '会话遇到可恢复问题。',
        severity: fallbackSeverity,
        title: fallbackSeverity === 'error' ? '会议暂时无法继续' : '会议出现提示',
      }
  }
}

function noAudioTrackAction(context: NoticeContext): string {
  if (
    context.captureMode === 'tab_audio' &&
    context.sourcePlatform === 'tencent_meeting_web'
  ) {
    return '腾讯会议网页版标签页音频可能不可用，请切换到系统音频模式后重新捕获。'
  }

  return '请确认共享时勾选“共享音频”，或切换到系统音频模式后重新捕获。'
}

function severityForCode(code: string): NoticeSeverity {
  if (
    code === 'qwen_interim_translation_failed' ||
    code === 'qwen_interim_translation_disabled' ||
    code === 'qwen_final_translation_failed' ||
    code === 'qwen_final_translation_disabled' ||
    code === 'export_failed' ||
    code === 'websocket_reconnecting'
  ) {
    return 'warning'
  }

  return 'error'
}
