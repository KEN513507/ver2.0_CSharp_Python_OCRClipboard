param(
    [string]$Message = "",
    [switch]$IncludeUntracked,
    [string]$Branch = "main"
)

# Show current status so the caller can review what will happen.
git status

# Decide how to stage changes.
if ($IncludeUntracked) {
    Write-Host "Staging tracked and untracked changes (git add -A)..."
    git add -A | Out-Null
} else {
    Write-Host "Staging tracked changes only (git add -u)..."
    git add -u | Out-Null
}

# Detect whether anything ended up staged.
$staged = git status --short | Where-Object { $_ -match '^[AMDCR]' }
if (-not $staged) {
    Write-Host "Nothing staged; aborting commit."
    exit 0
}

# Ask for a message if none was provided.
if (-not $Message) {
    $Message = Read-Host "Commit message"
    if (-not $Message) {
        Write-Host "Commit message empty; aborting."
        exit 1
    }
}

Write-Host "Committing with message: $Message"
git commit -m $Message

Write-Host "Pushing to origin/$Branch..."
git push origin $Branch
