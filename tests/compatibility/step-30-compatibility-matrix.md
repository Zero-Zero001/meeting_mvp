# Step 30 Compatibility Matrix

This document records the Step 30 manual compatibility matrix. Step 30 is not complete until every required row has a real result from Windows Chrome or Edge against a real HTTPS/WSS backend whose `provider_status.qwen_realtime_asr` is `enabled`.

Current status: blocked. The public compatibility target is now `https://meeting.orileyi.cn`. No real Windows Chrome/Edge Qwen-backed meeting-platform test result is recorded yet.

## Required Evidence

- Use a same-origin HTTPS page and WSS backend.
- Confirm `session_started.provider_status.qwen_realtime_asr` is `enabled`.
- Use non-private English test speech or a non-private test audio source in the meeting.
- Record the first `asr_interim` latency from browser DevTools WebSocket timestamps or a manual stopwatch.
- Do not store meeting transcript content, API keys, endpoints, account details, signed URLs, or private user data in this file.

## Required Matrix

| Platform | Browser | Capture Mode | Required | Result |
|---|---|---|---:|---|
| Google Meet | Chrome | `tab_audio` | Yes | Blocked: no verified real Qwen HTTPS/WSS target |
| Google Meet | Edge | `tab_audio` | Yes | Blocked: no verified real Qwen HTTPS/WSS target |
| Microsoft Teams Web | Chrome | `tab_audio` | Yes | Blocked: no verified real Qwen HTTPS/WSS target |
| Microsoft Teams Web | Edge | `tab_audio` | Yes | Blocked: no verified real Qwen HTTPS/WSS target |
| Zoom Web | Chrome | `tab_audio` | Yes | Blocked: no verified real Qwen HTTPS/WSS target |
| Zoom Web | Edge | `tab_audio` | Yes | Blocked: no verified real Qwen HTTPS/WSS target |
| Tencent Meeting Web | Chrome | `tab_audio` | Yes | Blocked: no verified real Qwen HTTPS/WSS target |
| Tencent Meeting Web | Chrome | `system_audio` | Yes | Blocked: no verified real Qwen HTTPS/WSS target |
| Tencent Meeting Web | Edge | `tab_audio` | Yes | Blocked: no verified real Qwen HTTPS/WSS target |
| Tencent Meeting Web | Edge | `system_audio` | Yes | Blocked: no verified real Qwen HTTPS/WSS target |

## Tencent Meeting Conclusion

No conclusion is recorded yet.

Allowed conclusions after real testing:

- `tab_audio_supported`: tab audio works and can remain the default path.
- `system_audio_only`: tab audio does not complete the MVP path, but system audio does.
- `unsupported`: neither tab audio nor system audio completes an effective meeting; this blocks Step 30 completion.

## Result Source

Structured source of truth: `tests/compatibility/step-30-compatibility-results.json`.

Validation command:

```powershell
pwsh -File scripts/validate-step30-compatibility.ps1
```
