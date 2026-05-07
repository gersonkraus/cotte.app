const assert = require('assert');
const fs = require('fs');
const path = require('path');

const htmlPath = path.join(__dirname, '../../sistema/cotte-frontend/tenant-comercial.html');
const html = fs.readFileSync(htmlPath, 'utf8');

const scripts = Array.from(html.matchAll(/<script\s+src="([^"]+)"\s*>/g)).map(function(match) {
  return match[1];
});

const legacyIndex = scripts.findIndex(function(src) {
  return /js\/tenant-comercial\.js\?v=/.test(src);
});
const pipelineIndex = scripts.findIndex(function(src) {
  return /js\/tenant-comercial-pipeline\.js\?v=/.test(src);
});

assert.notStrictEqual(legacyIndex, -1, 'tenant-comercial.js deve estar presente');
assert.notStrictEqual(pipelineIndex, -1, 'tenant-comercial-pipeline.js deve estar presente');
assert.ok(
  pipelineIndex > legacyIndex,
  'tenant-comercial-pipeline.js deve ser carregado depois de tenant-comercial.js para sobrescrever o Kanban legado'
);

console.log('tenant-comercial-pipeline-script-order: ok');
