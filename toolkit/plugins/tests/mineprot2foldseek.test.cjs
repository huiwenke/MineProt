// Run with: node --test toolkit/plugins/tests/mineprot2foldseek.test.cjs
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

function plugin(fetch) {
    const context = vm.createContext({
        document: { getElementsByClassName: () => [1], getElementsByName: () => [] },
        URLSearchParams, fetch
    });
    vm.runInContext(fs.readFileSync(path.join(__dirname, '../mineprot2foldseek.js'), 'utf8'), context);
    return context;
}

function atom(chain, { record = 'ATOM', residue = 'ALA', name = 'CA', element = 'C' } = {}) {
    const line = Array(80).fill(' ');
    function put(start, text) { [...text].forEach((c, i) => line[start + i] = c); }
    put(0, record.padEnd(6));
    put(12, name.padStart(4));
    put(17, residue);
    put(21, chain);
    put(76, element.padStart(2));
    return line.join('');
}

const context = plugin();
test('classifies monomers, homomers, blank chain IDs and CRLF', () => {
    assert.equal(context.foldseekProteinChainCount([atom('A'), atom('A')].join('\n')), 1);
    assert.equal(context.foldseekProteinChainCount([atom('A'), atom('B')].join('\r\n')), 2);
    assert.equal(context.foldseekProteinChainCount([atom(' '), atom('A')].join('\n')), 2);
});
test('counts chains within the first model, not models in an ensemble', () => {
    assert.equal(context.foldseekProteinChainCount(['MODEL        1', atom('A'), 'ENDMDL', 'MODEL        2', atom('B'), 'ENDMDL'].join('\n')), 1);
    assert.equal(context.foldseekProteinChainCount(['MODEL        1', atom('A'), atom('B'), 'ENDMDL', atom('C')].join('\n')), 2);
});
test('ignores nonprotein chains and calcium but recognizes modified amino acids', () => {
    const pdb = [atom('A'), atom('B', { name: 'P', residue: 'DA' }),
        atom('C', { record: 'HETATM', residue: 'CA', element: 'CA' }),
        atom('D', { record: 'HETATM', residue: 'LIG' })].join('\n');
    assert.equal(context.foldseekProteinChainCount(pdb), 1);
    assert.equal(context.foldseekProteinChainCount(pdb + '\n' + atom('E', { record: 'HETATM', residue: 'MSE' })), 2);
    assert.throws(() => context.foldseekProteinChainCount('<html>Error</html>'), /No protein/);
});
test('fetches current defaults and restricts multimer databases', async () => {
    const databases = [
        { path: 'mono', status: 'COMPLETE', default: true },
        { path: 'complex', status: 'COMPLETE', default: true, complex: true },
        ...['interface', 'motif', 'rna'].map(flag => ({ path: flag, status: 'COMPLETE', default: true, complex: true, [flag]: true })),
        { path: 'loading', status: 'RUNNING', default: true, complex: true },
        { path: 'optional', status: 'COMPLETE', complex: true }
    ];
    const ctx = plugin(async url => {
        assert.equal(url, 'https://foldseek.test/api/databases/all');
        return { ok: true, json: async () => ({ databases }) };
    });
    assert.deepEqual(Array.from(await ctx.foldseekDatabases('https://foldseek.test', false)), ['mono', 'complex']);
    assert.deepEqual(Array.from(await ctx.foldseekDatabases('https://foldseek.test', true)), ['complex']);
    const empty = plugin(async () => ({ ok: true, json: async () => ({ databases: [] }) }));
    await assert.rejects(empty.foldseekDatabases('', true), /No ready default multimer/);
});
test('submits form-compatible text, modes and repeated database fields', async () => {
    for (const multimer of [false, true]) {
        const ctx = plugin(async (url, options) => {
            assert.equal(url, 'https://foldseek.test/api/ticket');
            assert.equal(options.method, 'POST');
            assert.equal(options.headers.Accept, 'application/json');
            const body = options.body;
            assert.equal(body.get('q'), 'PDB & +\n');
            assert.equal(body.get('mode'), multimer ? 'complex-3diaa' : '3diaa');
            assert.deepEqual(body.getAll('database[]'), ['db1', 'db2']);
            assert.equal(body.get('email'), '');
            return { ok: true, json: async () => ({ id: 'job', status: 'PENDING' }) };
        });
        await ctx.submitFoldseek('https://foldseek.test', 'PDB & +', multimer, ['db1', 'db2']);
    }
});
test('routes accepted jobs and surfaces HTTP errors, limits and maintenance', async () => {
    for (const status of ['PENDING', 'RUNNING', 'COMPLETE']) {
        assert.equal(context.foldseekTicketURL('https://foldseek.test', { id: 'job', status }),
            'https://foldseek.test' + (status === 'COMPLETE' ? '/result/job/0' : '/queue/job'));
    }
    for (const status of ['RATELIMIT', 'MAINTENANCE', 'ERROR', 'UNKNOWN']) {
        assert.throws(() => context.foldseekTicketURL('', { id: 'job', status }));
    }
    assert.throws(() => context.foldseekTicketURL('', { status: 'PENDING' }), /no ticket ID/);
    const failed = plugin(async () => ({ ok: false, status: 400, json: async () => ({ error: 'Invalid database' }) }));
    await assert.rejects(failed.submitFoldseek('', 'PDB', false, []), /Invalid database/);
    const invalid = plugin(async () => ({ ok: false, status: 503, json: async () => { throw new Error(); } }));
    await assert.rejects(invalid.submitFoldseek('', 'PDB', false, []), /HTTP 503/);
});
