$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$toolsRoot = Join-Path $projectRoot '.cache/mh-tools'
$env:CARGO_TARGET_DIR = Join-Path $projectRoot 'target'
$env:CARGO_HOME = Join-Path $toolsRoot 'cargo'
$env:RUSTUP_HOME = Join-Path $toolsRoot 'rustup'
$env:PUB_CACHE = Join-Path $toolsRoot 'pub-cache'
$env:VCPKG_ROOT = Join-Path $toolsRoot 'vcpkg'
$env:VCPKG_DEFAULT_HOST_TRIPLET = 'x64-windows-static'
$env:VCPKG_MAX_CONCURRENCY = '12'
$env:CARGO_BUILD_JOBS = '12'
$env:VCPKG_BINARY_SOURCES = "clear;files,$toolsRoot/vcpkg-binary-cache,readwrite"
$env:LIBCLANG_PATH = Join-Path $toolsRoot 'libclang/clang/native'
$env:PATH = "$env:CARGO_HOME/bin;$toolsRoot/flutter/bin;$env:PATH"
$env:MH_CMAKE_PATH = (Get-Command cmake.exe -ErrorAction Stop).Source

$vswhere = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio/Installer/vswhere.exe'
$vsPath = & $vswhere -version '[17,18)' -latest -products '*' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
if (-not $vsPath) { throw 'Visual Studio 2022 with Desktop C++ tools is required.' }
# Import the compiler environment only into this build process.
$devCmd = Join-Path $vsPath 'Common7/Tools/VsDevCmd.bat'
& $env:ComSpec /d /s /c "`"$devCmd`" -no_logo -arch=x64 -host_arch=x64 && set" | ForEach-Object {
    if ($_ -match '^([^=]+)=(.*)$') { [Environment]::SetEnvironmentVariable($matches[1], $matches[2], 'Process') }
}
if ($LASTEXITCODE -ne 0) { throw 'Failed to initialize the C++ build environment.' }
# VsDevCmd points VCPKG_ROOT at its own optional copy; use our pinned dependency set.
$env:VCPKG_ROOT = Join-Path $toolsRoot 'vcpkg'

# Apply to native libraries and the portable launcher in this process only.
$privacyEnvironment = & python "$PSScriptRoot/../build_privacy.py" environment
if ($LASTEXITCODE -ne 0) { throw 'Failed to prepare build path mapping.' }
$privacyEnvironment = $privacyEnvironment | ConvertFrom-Json
foreach ($property in $privacyEnvironment.PSObject.Properties) {
    [Environment]::SetEnvironmentVariable($property.Name, [string]$property.Value, 'Process')
}
