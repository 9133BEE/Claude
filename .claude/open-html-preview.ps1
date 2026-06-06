[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
try {
    $raw = [Console]::In.ReadToEnd()
    $json = $raw | ConvertFrom-Json
    $fp = $json.tool_input.file_path
    if ($fp -and ($fp -match 'ClaudeRepo') -and $fp.EndsWith('.html')) {
        Start-Process $fp
    }
} catch {}