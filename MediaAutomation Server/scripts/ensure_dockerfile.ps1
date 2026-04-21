param(
  [Parameter(Mandatory=$false)]
  [string]$DockerfilePath = (Join-Path (Get-Location) 'Dockerfile')
)

if (-not (Test-Path -LiteralPath $DockerfilePath)) {
    Write-Error "Dockerfile nao encontrado em $DockerfilePath"
    exit 1
}

$content = Get-Content -Raw -LiteralPath $DockerfilePath

$needle = 'COPY app/requirements.txt /app/requirements.txt'
$insertLines = @(
    'COPY app/requirements.txt /app/requirements.txt'
    'RUN python -m pip install --upgrade pip setuptools wheel'
    'RUN pip install --no-cache-dir -r /app/requirements.txt'
) -join "`r`n"

# Se já existe o comando de upgrade do pip, nada a fazer
if ($content -match 'python -m pip install --upgrade pip setuptools wheel') {
    Write-Host "Trecho ja presente no Dockerfile. Nada a fazer para $DockerfilePath"
    exit 0
}

if ($content -notmatch [regex]::Escape($needle)) {
    Write-Error "Linha '$needle' nao encontrada no Dockerfile $DockerfilePath. Nao foi inserido."
    exit 2
}

# Insere o bloco imediatamente após a primeira ocorrência do needle
$index = $content.IndexOf($needle)
if ($index -lt 0) {
    Write-Error "Nao foi possivel localizar a linha para insercao em $DockerfilePath."
    exit 3
}
$before = $content.Substring(0, $index)
$after = $content.Substring($index + $needle.Length)
$final = $before + $insertLines + $after

# Grava o Dockerfile com encoding UTF8 (sem BOM) e CRLF
Set-Content -LiteralPath $DockerfilePath -Value $final -Encoding UTF8

Write-Host "Trecho inserido no Dockerfile com sucesso: $DockerfilePath"
exit 0
