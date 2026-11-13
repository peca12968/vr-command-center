import { createHash } from 'node:crypto';
import { readFile, writeFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const require = createRequire(new URL('../tests/browser/package.json', import.meta.url));
const { build } = require('esbuild');
const consoleDirectory = new URL('../src/VrCommand.Api/wwwroot/console/', import.meta.url);
const read = name => readFile(new URL(name, consoleDirectory), 'utf8');
const htmlNewlines = text => text.replace(/\r\n?/g, '\n');
const hash = text => "'sha256-" + createHash('sha256').update(text).digest('base64') + "'";

export async function packagePlayerReplay(output) {
  const [template, styles, license, bundle] = await Promise.all([
    read('player-replay.html'), read('console.css'), read('vendor/three/LICENSE'),
    build({
      entryPoints: [fileURLToPath(new URL('player-replay.js', consoleDirectory))],
      bundle: true,
      write: false,
      format: 'esm',
      platform: 'browser',
      target: 'es2022',
      minify: true,
      legalComments: 'inline',
      metafile: true,
    }),
  ]);
  const [outputFile] = bundle.outputFiles;
  const script = htmlNewlines(outputFile.text), css = htmlNewlines(styles);
  if (bundle.outputFiles.length !== 1 || Object.values(bundle.metafile.outputs).some(output => output.imports.length)
      || /<\/script/i.test(script) || /<\/style/i.test(css) || /-->|<\!/.test(license))
    throw new Error('The replay bundle requires embeddable code and no external modules.');

  const styleTag = '<link rel="stylesheet" href="./console.css">';
  const scriptTag = '<script type="module" src="./player-replay.js"></script>';
  if (!template.includes(styleTag) || !template.includes(scriptTag)) throw new Error('Player replay template changed.');
  const policy = `default-src 'none'; script-src ${hash(script)}; style-src ${hash(css)}; img-src data:; base-uri 'none'; form-action 'none'`;
  const html = template.replace(styleTag, () => `<meta http-equiv="Content-Security-Policy" content="${policy}">\n  <style>${css}</style>`)
    .replace(scriptTag, () => `<script type="module">${script}</script>`)
    .replace('</body>', () => `<!-- three.js license\n${license}-->\n</body>`);
  await writeFile(output, html, { encoding: 'utf8', flag: 'wx' });
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const output = process.argv[2];
  if (process.argv.length !== 3 || !output?.toLowerCase().endsWith('.html')) {
    console.error('Usage: node scripts/package-player-replay.mjs <new-player-replay.html>');
    process.exitCode = 2;
  } else {
    await packagePlayerReplay(output);
  }
}
