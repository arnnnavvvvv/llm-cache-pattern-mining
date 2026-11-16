# exports every slide of a .pptx to png (and the deck to pdf) through powerpoint, for checking the layout
import subprocess
import sys
from pathlib import Path

PS = r"""
$ErrorActionPreference = 'Stop'
$app = New-Object -ComObject PowerPoint.Application
$pres = $app.Presentations.Open('{pptx}', $true, $false, $false)
try {
  New-Item -ItemType Directory -Force '{out}' | Out-Null
  $i = 1
  foreach ($s in $pres.Slides) { $s.Export(('{out}\slide{0:D2}.png' -f $i), 'PNG', {w}, {h}); $i++ }
  $pres.SaveAs('{pdf}', 32)
  "slides: " + $pres.Slides.Count
} finally { $pres.Close() }
"""


# runs the export for one deck into a folder of pngs next to a pdf copy
def export(pptx: Path, out: Path, w: int = 1600, h: int = 900) -> None:
    script = (PS.replace("{pptx}", str(pptx.resolve())).replace("{out}", str(out.resolve()))
              .replace("{pdf}", str(pptx.with_suffix(".pdf").resolve())).replace("{w}", str(w)).replace("{h}", str(h)))
    res = subprocess.run(["powershell", "-NoProfile", "-Command", script], capture_output=True, text=True)
    print(res.stdout.strip() or res.stderr.strip())


if __name__ == "__main__":
    args = sys.argv[1:]
    export(Path(args[0]), Path(args[1]), *(int(a) for a in args[2:4]))
