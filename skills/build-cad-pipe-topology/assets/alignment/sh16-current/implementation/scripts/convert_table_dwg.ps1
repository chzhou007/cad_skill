param(
    [string]$InputPath = "C:\Users\chang\Downloads\sh16-native-table.dwg",
    [string]$ProjectRoot = "D:\codex\sh16_cad_graph"
)

$ErrorActionPreference = "Stop"

$sourceDir = Join-Path $ProjectRoot "data\table\source"
$interimDir = Join-Path $ProjectRoot "data\table\interim"
$dwgRead = Join-Path $ProjectRoot ".tools\libredwg-0.14\dwgread.exe"

New-Item -ItemType Directory -Force -Path $sourceDir, $interimDir | Out-Null

if (-not (Test-Path -LiteralPath $dwgRead)) {
    throw "LibreDWG converter not found: $dwgRead"
}

$sourceDwg = Join-Path $sourceDir "sh16-native-table.dwg"
$jsonPath = Join-Path $interimDir "sh16-native-table.json"
$rawDxfPath = Join-Path $interimDir "sh16-native-table.dxf"
$fixedDxfPath = Join-Path $interimDir "sh16-native-table.fixed.dxf"

Copy-Item -LiteralPath $InputPath -Destination $sourceDwg -Force

& $dwgRead -O JSON -o $jsonPath $sourceDwg
if ($LASTEXITCODE -ne 0) { throw "LibreDWG JSON conversion failed: $LASTEXITCODE" }

& $dwgRead -O DXF -o $rawDxfPath $sourceDwg
if ($LASTEXITCODE -ne 0) { throw "LibreDWG DXF conversion failed: $LASTEXITCODE" }

$dxfText = [IO.File]::ReadAllText($rawDxfPath).Replace("`r`r`n", "`r`n")
[IO.File]::WriteAllText($fixedDxfPath, $dxfText, [Text.UTF8Encoding]::new($false))

Write-Output $fixedDxfPath
