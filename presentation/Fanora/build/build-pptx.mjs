import fs from 'node:fs/promises';
import path from 'node:path';
import { Presentation, PresentationFile } from '@oai/artifact-tool';

const root = path.resolve(process.cwd(), 'presentation/Fanora');
const manifest = JSON.parse(await fs.readFile(path.join(root, 'slides-manifest.json'), 'utf8'));
const presentation = Presentation.create({ slideSize: { width: 1920, height: 1080 } });

for (let i = 0; i < manifest.length; i += 1) {
  const item = manifest[i];
  const pngName = item.file.replace('.html', '.png');
  const pngPath = path.join(root, 'rendered', pngName);
  const bytes = await fs.readFile(pngPath);
  const imageBytes = bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength);
  const slide = presentation.slides.add();
  slide.background.fill = '#21112F';
  slide.images.add({
    blob: imageBytes,
    contentType: 'image/png',
    alt: `Fanora presentation slide ${i + 1}: ${item.label}`,
    fit: 'cover',
    position: { left: 0, top: 0, width: 1920, height: 1080 },
  });
  slide.speakerNotes.textFrame.setText(
    `[Sources]\n- User-provided outline: docs/ppt/Fanora_展示文稿题纲.md\n- Product UI and brand assets: local Fanora repository\n${i === 18 ? '- Monad network reference: https://docs.monad.xyz/developer-essentials/network-information\n' : ''}[/Sources]`
  );
}

const out = path.join(root, 'Fanora_展示文稿_方向A.pptx');
const pptx = await PresentationFile.exportPptx(presentation);
await pptx.save(out);
console.log(out);
