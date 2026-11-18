# opens a built .docx in word, updates every field (contents, lists, numbering), saves it and exports a pdf
import subprocess
import sys
from pathlib import Path

PS = r"""
$ErrorActionPreference = 'Stop'
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
try {
  $doc = $word.Documents.Open('{docx}')
  $doc.Fields.Update() | Out-Null
  foreach ($t in $doc.TablesOfContents) { $t.Update() | Out-Null }
  foreach ($t in $doc.TablesOfFigures) { $t.Update() | Out-Null }
  $doc.Fields.Update() | Out-Null
  foreach ($t in $doc.TablesOfContents) { $t.Update() | Out-Null }
  foreach ($t in $doc.TablesOfFigures) { $t.Update() | Out-Null }
  $doc.Save()
  $doc.ExportAsFixedFormat('{pdf}', 17)
  "pages: " + $doc.ComputeStatistics(2)
  $doc.Close()
} finally { $word.Quit() }
"""


# runs the word automation for one document
def finalize(docx: Path) -> None:
    pdf = docx.with_suffix(".pdf")
    script = PS.replace("{docx}", str(docx.resolve())).replace("{pdf}", str(pdf.resolve()))
    out = subprocess.run(["powershell", "-NoProfile", "-Command", script], capture_output=True, text=True)
    print(out.stdout.strip() or out.stderr.strip())


if __name__ == "__main__":
    finalize(Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / "Final_Report.docx")
