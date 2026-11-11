[CmdletBinding()]
param([ValidateSet('native','ui','all')][string]$Stage = 'all', [string]$ControllerProfile)
. "$PSScriptRoot/windows-env.ps1"
$sourceRoot = $projectRoot
Remove-Item Env:MH_CONTROLLER_PROFILE -ErrorAction SilentlyContinue
if ($ControllerProfile) {
    & python "$PSScriptRoot/controller-profile.py" validate $ControllerProfile
    if ($LASTEXITCODE -ne 0) { throw 'Invalid controller profile.' }
    $env:MH_CONTROLLER_PROFILE = Get-Content -LiteralPath $ControllerProfile -Raw
}
function Assert-Build { if ($LASTEXITCODE -ne 0) { throw "MH $Stage build failed." } }
Push-Location $sourceRoot
try {
    if ($Stage -in @('native','all')) {
        if (-not (Test-Path "$env:VCPKG_ROOT/installed/x64-windows-static/include/libavcodec/avcodec.h")) {
            throw 'Run prepare-native.ps1 successfully before building the client.'
        }
        $features = & python build.py --portable --flutter --skip-portable-pack --hwcodec --vram --print-features
        Assert-Build
        & cargo build --locked --release --manifest-path libs/virtual_display/dylib/Cargo.toml
        Assert-Build
        & cargo build --locked --features $features --lib --release
        Assert-Build
    }
    if ($Stage -in @('ui','all')) {
        Push-Location flutter
        try {
            $controllerFlag = if ($ControllerProfile) { 'true' } else { 'false' }
            & flutter build windows --release --dart-define=MH_WINDOWS=true "--dart-define=MH_CONTROLLER=$controllerFlag"
            Assert-Build
        } finally { Pop-Location }
        Copy-Item target/release/deps/dylib_virtual_display.dll flutter/build/windows/x64/runner/Release/ -Force
    }
} finally { Pop-Location }
