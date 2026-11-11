[CmdletBinding()]
param([ValidateSet('rust','flutter','vcpkg','clang')][string]$Component)
$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$toolsRoot = Join-Path $projectRoot '.cache/mh-tools'
New-Item -ItemType Directory -Force -Path $toolsRoot | Out-Null
function Assert-Exit { if ($LASTEXITCODE -ne 0) { throw "Tool preparation failed ($Component)." } }
switch ($Component) {
    'rust' {
        $env:CARGO_HOME = Join-Path $toolsRoot 'cargo'
        $env:RUSTUP_HOME = Join-Path $toolsRoot 'rustup'
        $installer = Join-Path $toolsRoot 'rustup-init.exe'
        if (-not (Test-Path -LiteralPath $installer)) {
            & curl.exe --fail --location --retry 3 'https://static.rust-lang.org/rustup/dist/x86_64-pc-windows-msvc/rustup-init.exe' -o $installer
            Assert-Exit
        }
        & $installer -y --no-modify-path --profile minimal --default-toolchain 1.75.0
        Assert-Exit
        & (Join-Path $env:CARGO_HOME 'bin/rustup.exe') component add rustfmt --toolchain 1.75.0
        Assert-Exit
    }
    'flutter' {
        $flutterRoot = Join-Path $toolsRoot 'flutter'
        if (-not (Test-Path -LiteralPath $flutterRoot)) {
            & git clone --depth 1 --branch 3.24.5 https://github.com/flutter/flutter.git $flutterRoot
            Assert-Exit
        }
        $env:PUB_CACHE = Join-Path $toolsRoot 'pub-cache'
        & (Join-Path $flutterRoot 'bin/flutter.bat') config --no-analytics
        Assert-Exit
        & (Join-Path $flutterRoot 'bin/flutter.bat') precache --windows --no-android --no-ios --no-linux --no-macos --no-web
        Assert-Exit
    }
    'vcpkg' {
        $vcpkgRoot = Join-Path $toolsRoot 'vcpkg'
        if (-not (Test-Path -LiteralPath $vcpkgRoot)) {
            New-Item -ItemType Directory -Path $vcpkgRoot | Out-Null
            & git -C $vcpkgRoot init
            Assert-Exit
            & git -C $vcpkgRoot remote add origin https://github.com/microsoft/vcpkg.git
            Assert-Exit
        }
        & git -C $vcpkgRoot fetch origin 9e593bb18ea69cc5095e012465dcd675a822ed0d
        Assert-Exit
        if ((& git -C $vcpkgRoot rev-parse --is-shallow-repository) -eq 'true') {
            & git -C $vcpkgRoot fetch --unshallow origin 9e593bb18ea69cc5095e012465dcd675a822ed0d
            Assert-Exit
        }
        & git -C $vcpkgRoot checkout --detach FETCH_HEAD
        Assert-Exit
        & (Join-Path $vcpkgRoot 'bootstrap-vcpkg.bat') -disableMetrics
        Assert-Exit
    }
    'clang' {
        & python -m pip install --disable-pip-version-check --target (Join-Path $toolsRoot 'libclang') 'libclang==15.0.6.1'
        Assert-Exit
    }
}
