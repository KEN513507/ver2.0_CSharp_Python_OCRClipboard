param(
    [string]$Message,
    [switch]$IncludeUntracked,
    [string]$Remote = "origin",
    [string]$Branch,
    [switch]$SkipPush
)

function Invoke-Git {
    param([string]$Command, [string[]]$Arguments = @())
    $process = Start-Process -FilePath "git" -ArgumentList @($Command) + $Arguments -NoNewWindow -RedirectStandardOutput Temp:\git.out -RedirectStandardError Temp:\git.err -PassThru
    $process.WaitForExit()
    $stdout = Get-Content Temp:\git.out
    $stderr = Get-Content Temp:\git.err
    Remove-Item Temp:\git.out, Temp:\git.err -ErrorAction SilentlyContinue
    if ($stdout) { $stdout -join "`n" }
    if ($stderr) { Write-Error ($stderr -join "`n") }
    if ($process.ExitCode -ne 0) { throw "git $Command failed with exit code $($process.ExitCode)" }
}

try {
    # Resolve current branch if not provided.
    if (-not $Branch) {
        $Branch = git rev-parse --abbrev-ref HEAD
        if (-not $Branch) {
            throw "Unable to determine current branch. Specify -Branch explicitly."
        }
    }
    $Branch = $Branch.Trim()

    Write-Host "Using branch: $Branch"
    Write-Host "Showing git status:"
    git status

    # Stage changes.
    if ($IncludeUntracked) {
        Write-Host "Staging tracked and untracked changes (git add -A)..."
        git add -A
    } else {
        Write-Host "Staging tracked changes only (git add -u)..."
        git add -u
    }

    # Check if anything is staged.
    git diff --cached --quiet
    if ($LASTEXITCODE -eq 0) {
        Write-Host "No staged changes detected; aborting."
        exit 0
    }

    # Prompt for commit message if necessary.
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

    # Warn if pushing to main/master directly.
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
