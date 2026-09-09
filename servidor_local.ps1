param([int]$Port = 8085)

$listener = New-Object System.Net.HttpListener
$listener.Prefixes.Add("http://127.0.0.1:$Port/")
$listener.Prefixes.Add("http://localhost:$Port/")

try {
    $listener.Start()
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host "   RELATÓRIO EXECUTIVO ILHA ECO — SERVIDOR WEB LOCAL" -ForegroundColor White
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host "   URL Ativa: http://localhost:$Port" -ForegroundColor Green
    Write-Host "   Pressione Ctrl+C para encerrar o servidor." -ForegroundColor Yellow
    Write-Host "============================================================" -ForegroundColor Cyan
} catch {
    Write-Host "Erro ao iniciar o servidor na porta ${Port}. Detalhes: $_" -ForegroundColor Red
    exit 1
}

$filePath = Join-Path $PSScriptRoot "relatorio_trimestral_ilhaeco.html"

while ($listener.IsListening) {
    try {
        $context = $listener.GetContext()
        $request = $context.Request
        $response = $context.Response

        if (Test-Path $filePath) {
            $contentBytes = [System.IO.File]::ReadAllBytes($filePath)
            $response.ContentType = "text/html; charset=utf-8"
            $response.ContentLength64 = $contentBytes.Length
            $response.StatusCode = 200
            $response.OutputStream.Write($contentBytes, 0, $contentBytes.Length)
        } else {
            $response.StatusCode = 404
            $errBytes = [System.Text.Encoding]::UTF8.GetBytes("Arquivo de relatório não encontrado.")
            $response.OutputStream.Write($errBytes, 0, $errBytes.Length)
        }
        $response.OutputStream.Close()
    } catch {
        # Continua escutando requisições
    }
}
