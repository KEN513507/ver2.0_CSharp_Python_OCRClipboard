param(
    [string]$Message,
    [switch]$IncludeUntracked,
    [string]$Remote = "origin",
    [string]$Branch,
    [switch]$SkipPush
)

function Invoke-Git {
    param([string]$Command, [string[]]$Arguments = @())
    $process = Start-Process -FilePath "git" -ArgumentList @($Command) + $Arguments -NoNewWindow `
        -RedirectStandardOutput Temp:\git.out -RedirectStandardError Temp:\git.err -PassThru
    $process.WaitForExit()
    $stdout = if (Test-Path Temp:\git.out) { Get-Content Temp:\git.out } else { @() }
    $stderr = if (Test-Path Temp:\git.err) { Get-Content Temp:\git.err } else { @() }
    Remove-Item Temp:\git.out, Temp:\git.err -ErrorAction SilentlyContinue
    if ($stdout) { $stdout -join "`n" }
    if ($stderr) { Write-Error ($stderr -join "`n") }
    if ($process.ExitCode -ne 0) { throw "git $Command failed with exit code $($process.ExitCode)" }
}

function Get-RecentChanges {
    param([TimeSpan]$Window = (New-TimeSpan -Hours 1))
    $cutoff = (Get-Date).Subtract($Window)
    $recent = @()

    # Gather tracked modifications (M/A/D/R etc.)
    $tracked = git status --short --untracked-files=no
    foreach ($line in $tracked) {
        if (-not $line.Trim()) { continue }
        $status = $line.Substring(0,2).Trim()
        $path = $line.Substring(3).Trim('"')
        $fullPath = Join-Path (Get-Location) $path
        if (-not (Test-Path $fullPath -PathType Leaf)) { continue }
        $lastWrite = [System.IO.File]::GetLastWriteTime($fullPath)
        if ($lastWrite -ge $cutoff) {
            $recent += [PSCustomObject]@{
                Status    = $status
                Path      = $path
                LastWrite = $lastWrite
            }
        }
    }

    # Gather untracked files
    $untracked = git ls-files --others --exclude-standard
    foreach ($path in $untracked) {
        if (-not $path.Trim()) { continue }
        $fullPath = Join-Path (Get-Location) $path
        if (-not (Test-Path $fullPath -PathType Leaf)) { continue }
        $lastWrite = [System.IO.File]::GetLastWriteTime($fullPath)
        if ($lastWrite -ge $cutoff) {
            $recent += [PSCustomObject]@{
                Status    = "??"
                Path      = $path
                LastWrite = $lastWrite
            }
        }
    }

    return $recent | Sort-Object LastWrite -Descending
}

try {
    if (-not $Branch) {
        $Branch = git rev-parse --abbrev-ref HEAD
        if (-not $Branch) {
            throw "Unable to determine current branch. Specify -Branch explicitly."
        }
    }
    $Branch = $Branch.Trim()

    Write-Host "Using branch: $Branch"

    $recentChanges = Get-RecentChanges
    if ($recentChanges.Count -eq 0) {
        Write-Host "No files modified within the last hour."
    } else {
        Write-Host "Files modified within the last hour:"
        $recentChanges | Format-Table Status, Path, LastWrite -AutoSize
    }

    $answer = Read-Host "Push these changes to $Remote/$Branch ? [y/N]"
    if ($answer.ToLower() -ne "y") {
        Write-Host "User declined push. Exiting."
        exit 0
    }

    Write-Host "Showing git status:"
    git status

    if ($IncludeUntracked) {
        Write-Host "Staging tracked and untracked changes (git add -A)..."
        git add -A
    } else {
        Write-Host "Staging tracked changes only (git add -u)..."
        git add -u
    }

    git diff --cached --quiet
    if ($LASTEXITCODE -eq 0) {
        Write-Host "No staged changes detected; aborting."
        exit 0
    }

    if (-not $Message) {
        $Message = Read-Host "Commit message"
        if (-not $Message) {
            throw "Commit message cannot be empty."
        }
    }

    Write-Host "Committing with message: `$Message`..."
    git commit -m $Message

    if ($SkipPush) {
        Write-Host "SkipPush specified; skipping git push."
        exit 0
    }

    if ($Branch -in @("main", "master")) {
        $confirm = Read-Host "About to push to '$Branch'. Continue? [y/N]"
        if ($confirm.ToLower() -ne "y") {
            Write-Host "Push aborted by user."
            exit 0
        }
    }

    Write-Host "Pushing to $Remote/$Branch..."
    git push $Remote $Branch
}
catch {
    Write-Error $_.Exception.Message
    exit 1
}
