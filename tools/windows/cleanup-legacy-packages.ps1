[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$VerifiedRelease, [switch]$Apply)
$ErrorActionPreference = 'Stop'
$root = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$releaseRoot = Join-Path $root 'release/windows'
$current = (Resolve-Path -LiteralPath $VerifiedRelease).Path
if (-not $current.StartsWith($releaseRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Verified release must be under release/windows.'
}
$buildRecord = Join-Path (Join-Path $root '.local/windows-builds') ([IO.Path]::GetRelativePath($releaseRoot, $current))
$checksums = @(Get-ChildItem -LiteralPath $buildRecord -Filter '*-sha256.json' -File)
if ($checksums.Count -ne 1) { throw 'Expected one verified release checksum manifest.' }
$entries = Get-Content -LiteralPath $checksums[0].FullName -Raw | ConvertFrom-Json
foreach ($entry in $entries.PSObject.Properties) {
    if ([IO.Path]::GetFileName($entry.Name) -ne $entry.Name) { throw 'Invalid checksum filename.' }
    $file = Join-Path $buildRecord $entry.Name
    if ((Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLowerInvariant() -ne $entry.Value) {
        throw 'New release checksum mismatch; legacy packages retained.'
    }
}
if (@($entries.PSObject.Properties | Where-Object { $_.Name -like '*.exe' }).Count -ne 1 -or
    @($entries.PSObject.Properties | Where-Object { $_.Name -like '*-source.zip' }).Count -ne 1) {
    throw 'New portable program and corresponding source are required.'
}
$legacyRoot = Join-Path $root 'dist'
$names = @('1.5.1-mh.1', '1.5.1-mh.2-controller-test', '1.5.1-mh.3-controller-test',
           '1.5.1-mh.4-controller-test', '1.5.1-mh.5-controller-test')
$targets = @()
foreach ($name in $names) {
    $candidate = Join-Path $legacyRoot $name
    if (-not (Test-Path -LiteralPath $candidate)) { continue }
    $resolved = (Resolve-Path -LiteralPath $candidate).Path
    if ($resolved -ne [IO.Path]::GetFullPath($candidate) -or
        -not $resolved.StartsWith($legacyRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
        throw 'Legacy path escaped the expected directory.'
    }
    $items = @((Get-Item -LiteralPath $legacyRoot), (Get-Item -LiteralPath $resolved)) + @(Get-ChildItem -LiteralPath $resolved -Recurse -Force)
    if ($items | Where-Object { $_.Attributes -band [IO.FileAttributes]::ReparsePoint }) {
        throw 'Legacy output contains a link; refusing recursive deletion.'
    }
    $files = @($items | Where-Object { -not $_.PSIsContainer })
    $targets += [PSCustomObject]@{ Path=$resolved; Files=$files.Count; Bytes=($files | Measure-Object Length -Sum).Sum }
}
$record = [PSCustomObject]@{ VerifiedRelease=$current; Applied=[bool]$Apply; Targets=$targets }
$record | ConvertTo-Json -Depth 5
if ($Apply) {
    $local = Join-Path $root '.local/release-preparation'
    New-Item -ItemType Directory -Force -Path $local | Out-Null
    $record | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $local 'legacy-cleanup.json') -Encoding utf8
    foreach ($target in $targets) { Remove-Item -LiteralPath $target.Path -Recurse -Force }
    foreach ($target in $targets) {
        if (Test-Path -LiteralPath $target.Path) { throw 'Legacy cleanup incomplete.' }
    }
}
