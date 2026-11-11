[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$Version, [string]$ControllerProfile)
. "$PSScriptRoot/windows-env.ps1"
$env:MH_PACKAGE_VERSION = $Version
Remove-Item Env:MH_CONTROLLER_PROFILE_PATH -ErrorAction SilentlyContinue
if ($ControllerProfile) {
    & python "$PSScriptRoot/controller-profile.py" validate $ControllerProfile
    if ($LASTEXITCODE -ne 0) { throw 'Invalid controller profile.' }
    $env:MH_CONTROLLER_PROFILE_PATH = (Resolve-Path -LiteralPath $ControllerProfile).Path
}
$sourceRoot = $projectRoot
$dist = & python "$PSScriptRoot/package-windows.py" stage
if ($LASTEXITCODE -ne 0) { throw 'Failed to stage MH package.' }
Push-Location (Join-Path $sourceRoot 'libs/portable')
try {
    & python generate.py --folder $dist --output . --executable MH.exe --level 5
    if ($LASTEXITCODE -ne 0) { throw 'Failed to build MH portable executable.' }
} finally { Pop-Location }
& python "$PSScriptRoot/package-windows.py" finalize
if ($LASTEXITCODE -ne 0) { throw 'Failed to finalize MH package.' }
