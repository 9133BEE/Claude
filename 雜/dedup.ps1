$file = "c:\Users\Authma\Desktop\Claude\受眾資料庫網頁\snazzy.html"
$content = [System.IO.File]::ReadAllText($file, [System.Text.Encoding]::UTF8)

$lines = $content -split "`n"
$dIdx = -1
for ($i = 0; $i -lt $lines.Count; $i++) {
    if ($lines[$i].StartsWith("const D=[")) { $dIdx = $i; break }
}
Write-Host "D array on line: $($dIdx+1)"

$dLine = $lines[$dIdx]
$dStr = $dLine.Substring("const D=".Length).TrimEnd(";")
$D = $dStr | ConvertFrom-Json
Write-Host "Total entries: $($D.Count)"

$seen = @{}
$deduped = [System.Collections.Generic.List[object]]::new()
foreach ($d in $D) {
    if (-not $seen.ContainsKey($d.cp)) {
        $seen[$d.cp] = $true
        $deduped.Add($d)
    }
}
Write-Host "After dedup: $($deduped.Count)"
Write-Host "Removed: $($D.Count - $deduped.Count)"

$newDStr = "const D=" + ($deduped | ConvertTo-Json -Compress -Depth 5) + ";"
$lines[$dIdx] = $newDStr

$newContent = $lines -join "`n"
[System.IO.File]::WriteAllText($file, $newContent, [System.Text.Encoding]::UTF8)
Write-Host "Done!"
