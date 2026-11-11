[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$toolsRoot = Join-Path $projectRoot '.cache/mh-tools'
$env:VCPKG_ROOT = Join-Path $toolsRoot 'vcpkg'
$env:VCPKG_DEFAULT_HOST_TRIPLET = 'x64-windows-static'
$env:VCPKG_MAX_CONCURRENCY = '12'
$cache = Join-Path $toolsRoot 'vcpkg-binary-cache'
New-Item -ItemType Directory -Force $cache | Out-Null
$env:VCPKG_BINARY_SOURCES = "clear;files,$cache,readwrite"
Push-Location $projectRoot
try {
    & "$env:VCPKG_ROOT/vcpkg.exe" install --triplet x64-windows-static --x-manifest-root=. "--x-install-root=$env:VCPKG_ROOT/installed"
    if ($LASTEXITCODE -ne 0) { throw 'Native dependency build failed.' }
} finally { Pop-Location }
