param(
    [string]$InputPath = "C:\Users\chang\Downloads\sh16-native-isometric.dwg",
    [string]$ProjectRoot = "D:\codex\sh16_cad_graph"
)

$ErrorActionPreference = "Stop"

$sourceDir = Join-Path $ProjectRoot "data\source"
$interimDir = Join-Path $ProjectRoot "data\interim"
$toolRoot = Join-Path $ProjectRoot ".tools\libredwg-0.14"
$archive = Join-Path $ProjectRoot ".tools\libredwg-0.14-win64.zip"
$dwgRead = Join-Path $toolRoot "dwgread.exe"

New-Item -ItemType Directory -Force -Path $sourceDir, $interimDir, (Split-Path $archive) | Out-Null

if (-not (Test-Path -LiteralPath $dwgRead)) {
    if (-not (Test-Path -LiteralPath $archive)) {
        Invoke-WebRequest `
            -Uri "https://github.com/LibreDWG/libredwg/releases/download/0.14/libredwg-0.14-win64.zip" `
            -OutFile $archive
    }
    Expand-Archive -LiteralPath $archive -DestinationPath $toolRoot -Force
}

$sourceDwg = Join-Path $sourceDir "sh16-native-isometric.dwg"
Copy-Item -LiteralPath $InputPath -Destination $sourceDwg -Force

$jsonPath = Join-Path $interimDir "sh16-native-isometric.json"
$rawDxfPath = Join-Path $interimDir "sh16-native-isometric.dxf"
$fixedDxfPath = Join-Path $interimDir "sh16-native-isometric.fixed.dxf"

& $dwgRead -O JSON -o $jsonPath $sourceDwg
if ($LASTEXITCODE -ne 0) { throw "LibreDWG JSON conversion failed: $LASTEXITCODE" }

& $dwgRead -O DXF -o $rawDxfPath $sourceDwg
if ($LASTEXITCODE -ne 0) { throw "LibreDWG DXF conversion failed: $LASTEXITCODE" }

# LibreDWG 0.14 for Windows emits CRCRLF in this file. Normalize it and write
# UTF-8 without a BOM so ezdxf recognizes the ASCII DXF header.
$dxfText = [IO.File]::ReadAllText($rawDxfPath).Replace("`r`r`n", "`r`n")
[IO.File]::WriteAllText($fixedDxfPath, $dxfText, [Text.UTF8Encoding]::new($false))

Write-Output $fixedDxfPath

