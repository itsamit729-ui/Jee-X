"""Export the existing JE monogram for browsers and search engines (requires Pillow)."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

root = Path(__file__).resolve().parents[1] / 'frontend/public'
image = Image.new('RGB', (512, 512), '#BA431F')
draw = ImageDraw.Draw(image)
font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 285)
box = draw.textbbox((0, 0), 'JE', font=font)
draw.text(((512 - (box[2] - box[0])) / 2 - box[0], (512 - (box[3] - box[1])) / 2 - box[1]), 'JE', font=font, fill='white')
image.resize((96, 96), Image.Resampling.LANCZOS).save(root / 'favicon.png')
image.resize((180, 180), Image.Resampling.LANCZOS).save(root / 'apple-touch-icon.png')
image.save(root / 'favicon.ico', sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])
