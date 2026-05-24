$ErrorActionPreference = 'Stop'
$StagingDir = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$envFile = Join-Path $StagingDir 'staging.env'
Get-Content $envFile | ForEach-Object {
    if ($_ -match '^\s*#' -or $_ -notmatch '=') { return }
    $n, $v = $_ -split '=', 2
    Set-Item -Path "Env:$n" -Value $v.Trim()
}

if ($env:VPS_IP -eq '0.0.0.0' -or $env:PROVISION_STATUS -eq 'PROVISION_PENDING') {
    throw "staging not provisioned (VPS_IP=$($env:VPS_IP)). Run provision-hetzner.ps1 with HCLOUD_TOKEN."
}

$key = if ($env:HALFAPP_SSH_KEY) { $env:HALFAPP_SSH_KEY -replace '%USERPROFILE%', $env:USERPROFILE } else { "$env:USERPROFILE\.ssh\halfapp_staging_ed25519" }
$target = "$($env:VPS_USER)@$($env:VPS_IP)"
Write-Host "SSH -> $target"
ssh -i $key -o BatchMode=yes -o ConnectTimeout=15 $target 'docker ps && echo STAGING_ACCEPTANCE_OK'
