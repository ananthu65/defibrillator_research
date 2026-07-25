param(
    [Parameter(Mandatory = $false)]
    [ValidateSet(
        "prepare",
        "smoke",
        "batch-probe",
        "full-one-epoch",
        "preliminary"
    )]
    [string]$Mode = "smoke"
)

$ErrorActionPreference = "Stop"
$repositoryRoot = [System.IO.Path]::GetFullPath(
    (Join-Path $PSScriptRoot "..")
)
$logDirectory = Join-Path $repositoryRoot "logs\phase5"
New-Item -ItemType Directory -Force -Path $logDirectory | Out-Null

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$logPath = Join-Path $logDirectory "${timestamp}_${Mode}_powershell.txt"
$consoleLogPath = Join-Path $logDirectory "${timestamp}_${Mode}_console.txt"
$python = Join-Path $repositoryRoot ".venv\Scripts\python.exe"

Set-Location -LiteralPath $repositoryRoot
Start-Transcript -LiteralPath $logPath -Force

try {
    Write-Host "Phase 5 mode: $Mode"
    Write-Host "Repository: $repositoryRoot"
    Write-Host "PowerShell transcript: $logPath"
    Write-Host "Python console log: $consoleLogPath"
    Write-Host "Started: $((Get-Date).ToString('o'))"

    Write-Host ""
    Write-Host "GPU before command:"
    & nvidia-smi

    if ($Mode -eq "prepare") {
        $arguments = @(
            "scripts\create_phase5_training_view.py",
            "--dataset", "datasets\phase4_yolo",
            "--output", "datasets\phase4_yolo\phase5",
            "--report", "reports\phase5\training_view.json",
            "--quarantine-task", "P50_T",
            "--smoke-images-per-task", "6"
        )
    }
    elseif ($Mode -eq "smoke") {
        $arguments = @(
            "scripts\train_yolo_local.py",
            "--config", "configs\phase5\yolov8n_smoke.json"
        )
    }
    elseif ($Mode -eq "batch-probe") {
        $arguments = @(
            "scripts\train_yolo_local.py",
            "--config", "configs\phase5\yolov8n_batch8_probe.json"
        )
    }
    elseif ($Mode -eq "full-one-epoch") {
        $arguments = @(
            "scripts\train_yolo_local.py",
            "--config", "configs\phase5\yolov8n_full_one_epoch.json"
        )
    }
    else {
        $arguments = @(
            "scripts\train_yolo_local.py",
            "--config", "configs\phase5\yolov8n_preliminary.json"
        )
    }

    Write-Host ""
    Write-Host "Executing:"
    Write-Host "$python $($arguments -join ' ')"
    & $python @arguments 2>&1 | Tee-Object -FilePath $consoleLogPath
    $pythonExitCode = $LASTEXITCODE
    if ($pythonExitCode -ne 0) {
        throw "Phase 5 command failed with exit code $pythonExitCode."
    }

    Write-Host ""
    Write-Host "GPU after command:"
    & nvidia-smi
    Write-Host "Completed: $((Get-Date).ToString('o'))"
}
finally {
    Stop-Transcript
    Write-Host "PowerShell transcript saved to: $logPath"
    Write-Host "Python console log saved to: $consoleLogPath"
}
