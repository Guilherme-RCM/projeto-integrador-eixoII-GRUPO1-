# MySQL 8.4 portátil (sem instalação, sem administrador) para desenvolvimento local.
#
# Uso:
#   .\scripts\mysql_portatil.ps1 -Acao iniciar     # sobe o servidor em 127.0.0.1:3306
#   .\scripts\mysql_portatil.ps1 -Acao parar
#
# Pré-requisito (uma vez): baixar e descompactar o ZIP oficial
#   https://dev.mysql.com/downloads/mysql/  (Windows, ZIP Archive, 8.4 LTS)
# em $Base e inicializar com:
#   & "$Base\bin\mysqld.exe" --defaults-file="$Ini" --initialize-insecure --console
# Depois, definir senha de root e criar o usuário da aplicação (ver README).

param(
    [Parameter(Mandatory = $true)][ValidateSet('iniciar', 'parar')][string]$Acao,
    [string]$Base = "$env:USERPROFILE\tools\mysql-8.4.11-winx64",
    [string]$Ini = "$env:USERPROFILE\tools\my.ini"
)

if (-not (Test-Path "$Base\bin\mysqld.exe")) {
    Write-Error "MySQL não encontrado em $Base"
    exit 1
}

if ($Acao -eq 'iniciar') {
    Start-Process -FilePath "$Base\bin\mysqld.exe" -ArgumentList "--defaults-file=`"$Ini`"" -WindowStyle Hidden
    Write-Output "MySQL iniciado (127.0.0.1:3306)."
} else {
    # Encerramento limpo exige credencial; sem ela, encerra o processo.
    $proc = Get-Process mysqld -ErrorAction SilentlyContinue
    if ($proc) { $proc | Stop-Process; Write-Output "MySQL parado." } else { Write-Output "MySQL não estava em execução." }
}
