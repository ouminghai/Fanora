import fs from 'node:fs/promises';
import path from 'node:path';
import { spawn } from 'node:child_process';

const root = path.resolve(process.cwd(), 'presentation/Fanora');
const manifest = JSON.parse(await fs.readFile(path.join(root, 'slides-manifest.json'), 'utf8'));
const renderedDir = path.join(root, 'rendered');
const chrome = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';

await fs.mkdir(renderedDir, { recursive: true });
for (const existing of await fs.readdir(renderedDir)) {
  if (/^\d\d-.*\.png$/.test(existing)) await fs.unlink(path.join(renderedDir, existing));
}

function runChrome(args) {
  return new Promise((resolve, reject) => {
    const child = spawn(chrome, args, { stdio: ['ignore', 'pipe', 'pipe'] });
    let stderr = '';
    child.stderr.on('data', chunk => { stderr += chunk.toString(); });
    child.on('error', reject);
    child.on('close', code => {
      if (code === 0) resolve();
      else reject(new Error(stderr || `Chrome exited with code ${code}`));
    });
  });
}

for (const item of manifest) {
  const input = path.join(root, 'slides', item.file);
  const output = path.join(renderedDir, item.file.replace('.html', '.png'));
  await runChrome([
    '--headless=new',
    '--disable-gpu',
    '--hide-scrollbars',
    '--no-first-run',
    '--no-default-browser-check',
    '--window-size=1920,1080',
    '--force-device-scale-factor=1',
    '--run-all-compositor-stages-before-draw',
    '--virtual-time-budget=2500',
    `--screenshot=${output}`,
    `file://${input}`,
  ]);
}

console.log(`Rendered ${manifest.length} slides.`);
