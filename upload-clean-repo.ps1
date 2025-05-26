param([string]$RemoteUrl)

# 1) Overwrite .gitignore
@"
venv/
.venv/
__pycache__/
*.py[cod]
"@ | Out-File -Encoding UTF8 .gitignore
Write-Host "✔️ .gitignore updated."

# 2) Remove old history
if (Test-Path .git) {
  Write-Host "🗑 Removing existing .git..."
  Remove-Item -Recurse -Force .git
} else {
  Write-Host "ℹ️ No existing .git."
}

# 3) Init & commit
Write-Host "⚙️ Initializing repo..."
git init
git add .
git commit -m "Clean import: Phase1 bot code"

# 4) Add remote & push
Write-Host "🔗 Adding remote $RemoteUrl"
git remote add origin $RemoteUrl
Write-Host "🚀 Pushing..."
git push --force -u origin master

Write-Host "🎉 Uploaded clean repo to $RemoteUrl"
