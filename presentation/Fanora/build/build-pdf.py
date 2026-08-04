from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

root = Path.cwd() / "presentation" / "Fanora"
slides = sorted((root / "rendered").glob("[0-9][0-9]-*.png"))
output = root / "Fanora_展示文稿_方向A.pdf"

c = canvas.Canvas(str(output), pagesize=(1920, 1080))
for slide in slides:
    c.drawImage(ImageReader(str(slide)), 0, 0, width=1920, height=1080, preserveAspectRatio=True, mask='auto')
    c.showPage()
c.save()
print(output)
