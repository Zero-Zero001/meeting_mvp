param(
    [string]$OutputDir = "D:\meeting_mvp_secrets\qwen_asr_smoke_audio"
)

$ErrorActionPreference = "Stop"

$sampleUrl = "https://storage.googleapis.com/cloud-samples-data/speech/brooklyn_bridge.raw"
$outputPath = Resolve-Path -LiteralPath (New-Item -ItemType Directory -Force -Path $OutputDir)
$rawPath = Join-Path $outputPath "brooklyn_bridge.raw"

Invoke-WebRequest -Uri $sampleUrl -OutFile $rawPath

$sourceBytes = [System.IO.File]::ReadAllBytes($rawPath)
$bytesPerSecond = 32000

function New-LoopedRawFile {
    param(
        [string]$Path,
        [int]$Seconds
    )

    $requiredBytes = $Seconds * $bytesPerSecond
    $buffer = New-Object byte[] $requiredBytes
    $offset = 0
    while ($offset -lt $requiredBytes) {
        $copyLength = [Math]::Min($sourceBytes.Length, $requiredBytes - $offset)
        [Array]::Copy($sourceBytes, 0, $buffer, $offset, $copyLength)
        $offset += $copyLength
    }
    [System.IO.File]::WriteAllBytes($Path, $buffer)
}

$raw30s = Join-Path $outputPath "brooklyn_bridge_30s.raw"
$raw3m = Join-Path $outputPath "brooklyn_bridge_3m.raw"
$raw10m = Join-Path $outputPath "brooklyn_bridge_10m.raw"
New-LoopedRawFile -Path $raw30s -Seconds 30
New-LoopedRawFile -Path $raw3m -Seconds 180
New-LoopedRawFile -Path $raw10m -Seconds 600

$manifestPath = Join-Path $outputPath "qwen-asr-smoke-manifest.json"
$manifest = @{
    cases = @{
        latency = @{
            path = $rawPath
            expected_terms = @("Brooklyn Bridge")
            max_term_errors = 0
            require_punctuation = $true
        }
        stability_30s = @{
            path = $raw30s
            duration_seconds = 30
        }
        stability_3m = @{
            path = $raw3m
            duration_seconds = 180
        }
        stability_10m = @{
            path = $raw10m
            duration_seconds = 600
        }
        terms = @{
            path = $rawPath
            expected_terms = @("Brooklyn Bridge")
            max_term_errors = 0
            require_punctuation = $true
        }
    }
}

$manifest | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $manifestPath -Encoding UTF8

Write-Host "Downloaded: $rawPath"
Write-Host "Manifest: $manifestPath"
Write-Host "Set QWEN_ASR_SMOKE_MANIFEST to this manifest path when running gated smoke tests."
