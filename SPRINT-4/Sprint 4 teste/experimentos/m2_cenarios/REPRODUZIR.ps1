param([string]$Saida = ('reproducao_' + (Get-Date -Format 'yyyyMMdd_HHmmss')))
$ErrorActionPreference = 'Stop'
$pythonExperimento = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonExperimento)) {
    & uv venv --python 3.12 (Join-Path $PSScriptRoot '.venv')
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao criar ambiente Python local.' }
    & uv pip sync --python $pythonExperimento (Join-Path $PSScriptRoot 'requirements.lock')
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao instalar dependências fixadas.' }
}
& $pythonExperimento -B (Join-Path $PSScriptRoot 'executar.py') --saida $Saida
if ($LASTEXITCODE -ne 0) { throw 'A execução falhou; consultar a saída preservada.' }
& $pythonExperimento -B (Join-Path $PSScriptRoot 'relatar.py') --saida $Saida
if ($LASTEXITCODE -ne 0) { throw 'Falha ao gerar relatório.' }
& $pythonExperimento -B (Join-Path $PSScriptRoot 'auditar_resultados.py') --saida $Saida
if ($LASTEXITCODE -ne 0) { throw 'Falha na auditoria final.' }
Write-Host ('Concluído em: ' + (Join-Path $PSScriptRoot $Saida))
