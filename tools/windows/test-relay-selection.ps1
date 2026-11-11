[CmdletBinding()]
param()
. "$PSScriptRoot/windows-env.ps1"
$testRoot = Join-Path $projectRoot '.local/client-tests/relay-selection'
New-Item -ItemType Directory -Force -Path $testRoot | Out-Null
$modulePath = Join-Path $projectRoot 'src/mh/relay.rs'
$harness = Join-Path $testRoot 'harness.rs'
Set-Content -LiteralPath $harness -Value ('#[path = r"' + $modulePath + '"] mod mh_relay;') -Encoding utf8
$binary = Join-Path $testRoot 'relay-selection-tests.exe'
& rustc --edition=2021 --test $harness -o $binary
if ($LASTEXITCODE -ne 0) { throw 'Relay selection test compilation failed.' }
& $binary
if ($LASTEXITCODE -ne 0) { throw 'Relay selection regression tests failed.' }
