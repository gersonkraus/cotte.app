/**
 * Contrato leve: body de POST /ai/orcamento/confirmar gerado a partir da prévia.
 */
const assert = require('assert');
const fs = require('fs');
const path = require('path');

const { buildConfirmarOrcamentoPayload } = require('../../sistema/cotte-frontend/js/assistente-ia-payloads.js');

const snapshotPath = path.join(__dirname, '../fixtures/orcamento-confirmar-request.snapshot.json');
const expected = JSON.parse(fs.readFileSync(snapshotPath, 'utf8'));

const dadosPreview = {
  cliente_nome: 'Maria',
  servico: 'Instalação elétrica',
  valor: 350,
  desconto: 0,
  desconto_tipo: 'percentual',
  observacoes: 'Executar amanhã',
};

const built = buildConfirmarOrcamentoPayload(dadosPreview, null);

assert.deepStrictEqual(built, expected, 'Payload deve coincidir com o snapshot (contrato com o mock e2e)');

const responseSamplePath = path.join(__dirname, '../fixtures/orcamento-confirmar-response.sample.json');
const responseSample = JSON.parse(fs.readFileSync(responseSamplePath, 'utf8'));
assert.strictEqual(responseSample.sucesso, true);
assert.strictEqual(responseSample.tipo_resposta, 'orcamento_criado');
assert.strictEqual(responseSample.dados.numero, 'ORC-321-26');
assert.ok(responseSample.dados.id);

console.log('assistente-orcamento-confirmar-payload: ok');
