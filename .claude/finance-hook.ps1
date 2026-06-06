[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$raw = [Console]::In.ReadToEnd()
$json = $raw | ConvertFrom-Json
$p = $json.prompt
if (-not $p) { exit 0 }
$pattern = '股票|期貨|技術分析|K線|均線|RSI|MACD|KD|布林|選擇權|ETF|基金|外匯|債券|漲跌|漲停|跌停|多空|套利|避險|大盤|個股|台股|美股|外資|投信|自營|融資|融券|波段|停損|停利|籌碼|量價|殖利率|本益比|市值|IPO|除權|除息|配股|配息|空單|多單|做空|做多|當沖|隔日沖'
if ($p -match $pattern) {
    $ctx = '【系統提示】用戶訊息包含金融/股市相關字詞，請以 Financial Analyst（專業金融分析師）身份回應。回應應涵蓋：技術面分析、基本面評估、籌碼面觀察、風險提示，以及具體操作策略建議。'
    $out = [ordered]@{
        hookSpecificOutput = [ordered]@{
            hookEventName   = 'UserPromptSubmit'
            additionalContext = $ctx
        }
    }
    $out | ConvertTo-Json -Compress
}