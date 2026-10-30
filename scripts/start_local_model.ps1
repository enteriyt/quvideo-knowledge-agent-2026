param(
    [Parameter(Mandatory=$true)][string]$LlamaServer,
    [Parameter(Mandatory=$true)][string]$ModelPath,
    [int]$Port = 8089
)
$ErrorActionPreference = 'Stop'
$serverAbsolute = (Resolve-Path -LiteralPath $LlamaServer).Path
$modelAbsolute = (Resolve-Path -LiteralPath $ModelPath).Path
$expectedHash = '061b54daade076b5d3362dac252678d17da8c68f07560be70818cace6590cb1a'
if ((Get-FileHash -LiteralPath $modelAbsolute -Algorithm SHA256).Hash.ToLower() -ne $expectedHash) {
    throw 'Expected official Qwen3-1.7B-Q8_0.gguf SHA-256; model differs.'
}
$localState = Join-Path $PSScriptRoot '../.local-model'
New-Item -ItemType Directory -Path $localState -Force | Out-Null
$modelService = Start-Process -FilePath $serverAbsolute -ArgumentList @(
    '-m',('"'+$modelAbsolute+'"'),'--host','127.0.0.1','--port',$Port,
    '-c','8192','-t','8','-np','1','--reasoning','off','--alias','qwen3-1.7b'
) -WindowStyle Hidden -RedirectStandardOutput (Join-Path $localState 'server.stdout.log') `
  -RedirectStandardError (Join-Path $localState 'server.stderr.log') -PassThru
$modelService.Id | Set-Content (Join-Path $localState 'server.pid')
Write-Output ('Local model process: '+$modelService.Id)
Write-Output ('MODEL_BASE_URL=http://127.0.0.1:'+$Port+'/v1; MODEL_NAME=qwen3-1.7b')
Write-Output 'Wait for the server log to report readiness before evaluating.'
