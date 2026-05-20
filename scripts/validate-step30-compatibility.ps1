param(
    [string]$ResultsPath = "tests/compatibility/step-30-compatibility-results.json"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RequiredRows = @(
    @{ source_platform = "google_meet"; browser = "chrome"; capture_mode = "tab_audio" },
    @{ source_platform = "google_meet"; browser = "edge"; capture_mode = "tab_audio" },
    @{ source_platform = "teams_web"; browser = "chrome"; capture_mode = "tab_audio" },
    @{ source_platform = "teams_web"; browser = "edge"; capture_mode = "tab_audio" },
    @{ source_platform = "zoom_web"; browser = "chrome"; capture_mode = "tab_audio" },
    @{ source_platform = "zoom_web"; browser = "edge"; capture_mode = "tab_audio" },
    @{ source_platform = "tencent_meeting_web"; browser = "chrome"; capture_mode = "tab_audio" },
    @{ source_platform = "tencent_meeting_web"; browser = "chrome"; capture_mode = "system_audio" },
    @{ source_platform = "tencent_meeting_web"; browser = "edge"; capture_mode = "tab_audio" },
    @{ source_platform = "tencent_meeting_web"; browser = "edge"; capture_mode = "system_audio" }
)

$ResultFields = @(
    "source_platform",
    "browser",
    "browser_version",
    "os",
    "capture_mode",
    "permission_result",
    "audio_detected",
    "first_asr_interim_ms",
    "final_segment_count",
    "failure_code",
    "tested_at",
    "backend_environment",
    "provider_status",
    "notes"
)

$AllowedPlatforms = @("google_meet", "teams_web", "zoom_web", "tencent_meeting_web")
$AllowedBrowsers = @("chrome", "edge")
$AllowedCaptureModes = @("tab_audio", "system_audio")
$AllowedPermissionResults = @("granted", "denied", "no_audio", "unsupported", "failed")
$AllowedTencentConclusions = @("tab_audio_supported", "system_audio_only", "unsupported")

function Add-ValidationError {
    param(
        [System.Collections.Generic.List[string]]$Errors,
        [string]$Message
    )

    $Errors.Add($Message)
}

function Has-Property {
    param(
        [object]$Object,
        [string]$Name
    )

    return $null -ne $Object.PSObject.Properties[$Name]
}

function Get-PropertyValue {
    param(
        [object]$Object,
        [string]$Name
    )

    if (Has-Property $Object $Name) {
        return $Object.PSObject.Properties[$Name].Value
    }
    return $null
}

function Is-Blank {
    param([object]$Value)

    if ($null -eq $Value) {
        return $true
    }
    if ($Value -is [string]) {
        return [string]::IsNullOrWhiteSpace($Value)
    }
    return $false
}

function Is-SuccessfulResult {
    param([object]$Result)

    $PermissionResult = Get-PropertyValue $Result "permission_result"
    $AudioDetected = Get-PropertyValue $Result "audio_detected"
    $FirstAsrInterimMs = Get-PropertyValue $Result "first_asr_interim_ms"
    $FinalSegmentCount = Get-PropertyValue $Result "final_segment_count"
    $BackendEnvironment = Get-PropertyValue $Result "backend_environment"
    $ProviderStatus = Get-PropertyValue $Result "provider_status"

    if ($PermissionResult -ne "granted") {
        return $false
    }
    if ($AudioDetected -ne $true) {
        return $false
    }
    if ($FirstAsrInterimMs -isnot [int] -and $FirstAsrInterimMs -isnot [long]) {
        return $false
    }
    if ($FirstAsrInterimMs -le 0) {
        return $false
    }
    if ($FinalSegmentCount -isnot [int] -and $FinalSegmentCount -isnot [long]) {
        return $false
    }
    if ($FinalSegmentCount -lt 1) {
        return $false
    }
    if ($BackendEnvironment -ne "real_qwen_https_wss") {
        return $false
    }
    if ($null -eq $ProviderStatus -or -not (Has-Property $ProviderStatus "qwen_realtime_asr")) {
        return $false
    }
    return $ProviderStatus.qwen_realtime_asr -eq "enabled"
}

if (-not (Test-Path -LiteralPath $ResultsPath)) {
    Write-Error "Compatibility results file not found: $ResultsPath"
}

$Errors = [System.Collections.Generic.List[string]]::new()
$Payload = Get-Content -Raw -Encoding UTF8 -LiteralPath $ResultsPath | ConvertFrom-Json

if (-not (Has-Property $Payload "results")) {
    Add-ValidationError $Errors "Missing top-level 'results' array."
} elseif ($Payload.results.Count -eq 0) {
    Add-ValidationError $Errors "No compatibility results recorded. Step 30 requires real manual test rows."
}

if ((Has-Property $Payload "status") -and $Payload.status -ne "completed") {
    Add-ValidationError $Errors "Top-level status is '$($Payload.status)', not 'completed'."
}

if (-not (Has-Property $Payload "tencent_meeting_conclusion") -or (Is-Blank $Payload.tencent_meeting_conclusion)) {
    Add-ValidationError $Errors "Missing tencent_meeting_conclusion."
} elseif ($Payload.tencent_meeting_conclusion -notin $AllowedTencentConclusions) {
    Add-ValidationError $Errors "Invalid tencent_meeting_conclusion '$($Payload.tencent_meeting_conclusion)'."
}

$Results = @()
if ((Has-Property $Payload "results") -and $Payload.results.Count -gt 0) {
    $Results = @($Payload.results)
}

for ($Index = 0; $Index -lt $Results.Count; $Index += 1) {
    $Result = $Results[$Index]
    $RowLabel = "results[$Index]"

    foreach ($Field in $ResultFields) {
        if (-not (Has-Property $Result $Field)) {
            Add-ValidationError $Errors "$RowLabel is missing required field '$Field'."
        }
    }

    $SourcePlatform = Get-PropertyValue $Result "source_platform"
    $Browser = Get-PropertyValue $Result "browser"
    $BrowserVersion = Get-PropertyValue $Result "browser_version"
    $Os = Get-PropertyValue $Result "os"
    $CaptureMode = Get-PropertyValue $Result "capture_mode"
    $PermissionResult = Get-PropertyValue $Result "permission_result"
    $AudioDetected = Get-PropertyValue $Result "audio_detected"
    $FailureCode = Get-PropertyValue $Result "failure_code"
    $TestedAt = Get-PropertyValue $Result "tested_at"
    $BackendEnvironment = Get-PropertyValue $Result "backend_environment"
    $ProviderStatus = Get-PropertyValue $Result "provider_status"

    if ($SourcePlatform -notin $AllowedPlatforms) {
        Add-ValidationError $Errors "$RowLabel has invalid source_platform '$SourcePlatform'."
    }
    if ($Browser -notin $AllowedBrowsers) {
        Add-ValidationError $Errors "$RowLabel has invalid browser '$Browser'."
    }
    if ($CaptureMode -notin $AllowedCaptureModes) {
        Add-ValidationError $Errors "$RowLabel has invalid capture_mode '$CaptureMode'."
    }
    if ($PermissionResult -notin $AllowedPermissionResults) {
        Add-ValidationError $Errors "$RowLabel has invalid permission_result '$PermissionResult'."
    }
    if ((Is-Blank $BrowserVersion) -or $BrowserVersion -eq "unknown") {
        Add-ValidationError $Errors "$RowLabel must include a concrete browser_version."
    }
    if ((Is-Blank $Os) -or $Os -eq "unknown") {
        Add-ValidationError $Errors "$RowLabel must include a concrete os value."
    }
    if (Is-Blank $TestedAt) {
        Add-ValidationError $Errors "$RowLabel must include tested_at."
    }
    if ($BackendEnvironment -ne "real_qwen_https_wss") {
        Add-ValidationError $Errors "$RowLabel must use backend_environment 'real_qwen_https_wss'."
    }
    if ($null -eq $ProviderStatus -or -not (Has-Property $ProviderStatus "qwen_realtime_asr") -or $ProviderStatus.qwen_realtime_asr -ne "enabled") {
        Add-ValidationError $Errors "$RowLabel must prove provider_status.qwen_realtime_asr is enabled."
    }
    if (($PermissionResult -ne "granted" -or $AudioDetected -ne $true) -and (Is-Blank $FailureCode)) {
        Add-ValidationError $Errors "$RowLabel must include failure_code for non-successful captures."
    }
    if ($PermissionResult -eq "not_run" -or $FailureCode -eq "not_run") {
        Add-ValidationError $Errors "$RowLabel contains forbidden not_run marker."
    }
}

foreach ($Required in $RequiredRows) {
    $Matches = @(
        $Results | Where-Object {
            (Get-PropertyValue $_ "source_platform") -eq $Required.source_platform -and
            (Get-PropertyValue $_ "browser") -eq $Required.browser -and
            (Get-PropertyValue $_ "capture_mode") -eq $Required.capture_mode
        }
    )
    if ($Matches.Count -eq 0) {
        Add-ValidationError $Errors ("Missing required row: {0}/{1}/{2}" -f $Required.source_platform, $Required.browser, $Required.capture_mode)
    }
}

foreach ($Platform in @("google_meet", "teams_web", "zoom_web")) {
    $TabRows = @(
        $Results | Where-Object {
            (Get-PropertyValue $_ "source_platform") -eq $Platform -and
            (Get-PropertyValue $_ "capture_mode") -eq "tab_audio"
        }
    )
    $SuccessfulTabRows = @($TabRows | Where-Object { Is-SuccessfulResult $_ })
    if ($SuccessfulTabRows.Count -lt 1) {
        Add-ValidationError $Errors "$Platform requires at least one successful tab_audio result across Chrome/Edge."
    }
}

$TencentRows = @($Results | Where-Object { (Get-PropertyValue $_ "source_platform") -eq "tencent_meeting_web" })
$TencentTabSuccesses = @($TencentRows | Where-Object { (Get-PropertyValue $_ "capture_mode") -eq "tab_audio" -and (Is-SuccessfulResult $_) })
$TencentSystemSuccesses = @($TencentRows | Where-Object { (Get-PropertyValue $_ "capture_mode") -eq "system_audio" -and (Is-SuccessfulResult $_) })

if ((Has-Property $Payload "tencent_meeting_conclusion") -and -not (Is-Blank $Payload.tencent_meeting_conclusion)) {
    switch ($Payload.tencent_meeting_conclusion) {
        "tab_audio_supported" {
            if ($TencentTabSuccesses.Count -lt 1) {
                Add-ValidationError $Errors "Tencent conclusion tab_audio_supported requires at least one successful tab_audio row."
            }
        }
        "system_audio_only" {
            if ($TencentTabSuccesses.Count -gt 0) {
                Add-ValidationError $Errors "Tencent conclusion system_audio_only conflicts with a successful tab_audio row."
            }
            if ($TencentSystemSuccesses.Count -lt 1) {
                Add-ValidationError $Errors "Tencent conclusion system_audio_only requires at least one successful system_audio row."
            }
        }
        "unsupported" {
            Add-ValidationError $Errors "Tencent conclusion unsupported blocks Step 30 completion."
        }
    }
}

if ($Errors.Count -gt 0) {
    Write-Host "Step 30 compatibility validation failed:" -ForegroundColor Red
    foreach ($ErrorItem in $Errors) {
        Write-Host "- $ErrorItem" -ForegroundColor Red
    }
    exit 1
}

Write-Host "Step 30 compatibility validation passed." -ForegroundColor Green
