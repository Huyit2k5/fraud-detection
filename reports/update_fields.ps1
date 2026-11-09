# Cập nhật mục lục, danh mục hình/bảng và số thứ tự chú thích trong file Word bằng Microsoft Word
# (COM). python-docx không tự tính số trang được nên bước này cần Word cài trên máy.
# Dùng: powershell -ExecutionPolicy Bypass -File reports/update_fields.ps1 -Path reports/final_report.docx
param([Parameter(Mandatory = $true)][string]$Path)

$full = (Resolve-Path $Path).Path
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
try {
    $doc = $word.Documents.Open($full)
    # Cập nhật 2 lượt: lượt 1 đánh số chú thích (SEQ), lượt 2 tính lại số trang trong mục lục.
    for ($i = 0; $i -lt 2; $i++) {
        $doc.Fields.Update() | Out-Null
        foreach ($toc in $doc.TablesOfContents) { $toc.Update() | Out-Null }
        foreach ($tof in $doc.TablesOfFigures) { $tof.Update() | Out-Null }
    }
    $doc.Save()
    $doc.Close()
    Write-Output "[Word] Đã cập nhật mục lục và danh mục: $full"
}
finally {
    try { $word.Quit() } catch { }
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($word) | Out-Null
}
