<#
.SYNOPSIS
  Creates a private GitHub repo and pushes this folder's code to it.
#>

function Read-Token {
  Write-Host "Enter your GitHub Personal Access Token (with repo scope):"
  $secure = Read-Host -AsSecureString
  return [Runtime.InteropServices.Marshal]::PtrToStringAuto(
           [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
         )
}

# Gather inputs
$username = Read-Host "GitHub username/org"
$repoName = Read-Host "New private repo name"
$token    = Read-Token

# Create private repo
$uri  = "https://api.github.com/user/repos"
$body = @{ name = $repoName; private = $true } | ConvertTo-Json
Write-Host "`nCreating repo '$repoName' under '$username'..."
$resp = Invoke-RestMethod -Method Post -Uri $uri `
  -Headers @{ Authorization = "Bearer $token"; "User-Agent" = "PowerShell" } `
  -Body $body

Write-Host "✅ Created: $($resp.html_url)`n"

# Initialize Git if needed
if (-not (Test-Path .git)) {
  Write-Host "Initializing local Git repository..."
  git init
} else {
  Write-Host "Git repo already exists."
}

# Commit all files
Write-Host "Staging and committing files..."
git add .
git commit -m "Initial commit"

# Set remote and push
$remote = "https://$token@github.com/$username/$repoName.git"
git remote remove origin -ErrorAction SilentlyContinue
git remote add origin $remote

Write-Host "Pushing to GitHub..."
git push -u origin main

Write-Host "`n🎉 Done! Visit $($resp.html_url) to verify your private repo."
