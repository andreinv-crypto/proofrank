param(
    [Parameter(Mandatory = $true)]
    [string]$Manifest,

    [Parameter(Mandatory = $true)]
    [string]$OutputDir,

    [string]$Voice = "Microsoft Zira Desktop",

    [ValidateRange(-10, 10)]
    [int]$Rate = -2
)

$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Speech

$manifestPath = (Resolve-Path -LiteralPath $Manifest).Path
$outputPath = [System.IO.Path]::GetFullPath($OutputDir)
[System.IO.Directory]::CreateDirectory($outputPath) | Out-Null
$segments = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json

$synth = [System.Speech.Synthesis.SpeechSynthesizer]::new()
try {
    $installedVoices = @($synth.GetInstalledVoices() | ForEach-Object { $_.VoiceInfo.Name })
    if ($installedVoices -notcontains $Voice) {
        $englishVoice = $synth.GetInstalledVoices() |
            Where-Object { $_.VoiceInfo.Culture.Name -like "en-*" } |
            Select-Object -First 1
        if ($null -eq $englishVoice) {
            throw "No installed English speech-synthesis voice is available."
        }
        $Voice = $englishVoice.VoiceInfo.Name
    }

    $synth.SelectVoice($Voice)
    $synth.Rate = $Rate
    $synth.Volume = 100

    foreach ($segment in $segments) {
        $destination = Join-Path $outputPath ($segment.id + ".wav")
        $synth.SetOutputToWaveFile($destination)
        $synth.Speak([string]$segment.text)
        $synth.SetOutputToNull()
    }
}
finally {
    $synth.Dispose()
}

[ordered]@{
    status = "ok"
    voice = $Voice
    rate = $Rate
    segments = @($segments).Count
    output_dir = $outputPath
} | ConvertTo-Json
