const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const html = fs.readFileSync(path.join(__dirname, '../smb/templates/pocket.html'), 'utf8');

function page(data) {
  const elements = {};
  const context = {
    data,
    api: async () => context.data,
    $: id => elements[id] ??= { style: {} },
    labels: { copying: '正在备份', paused: '备份已暂停', done: '备份已完成' },
  };
  vm.createContext(context);
  vm.runInContext(html.match(/async function loadStatus\(\)\{[^\n]+/)[0], context);
  vm.runInContext(html.match(/function statusIcon\(s\)\{[^\n]+/)[0], context);
  return { context, elements };
}

for (const [status, copied, skipped, expected] of [
  ['copying', 24, 0, '30%'],
  ['copying', 24, 16, '50%'],
  ['paused', 40, 0, '50%'],
  ['done', 80, 0, '100%'],
]) {
  test(`${status}: ${copied} copied + ${skipped} skipped must show ${expected}`, async () => {
    const { context, elements } = page({ status, progress: {
      total_files: 80, copied_files: copied, skipped_files: skipped,
      phase_progress: 100, current_speed: 1.5,
    } });
    await context.loadStatus();
    assert.ok(elements.progressText.textContent.startsWith(expected));
    assert.equal(elements.progressBar.style.width, expected);
    assert.equal(elements.speed.textContent, '1.5');
  });
}

test('history accepts desktop completed as well as done', () => {
  const { context } = page({});
  for (const status of ['done', 'completed']) assert.equal(context.statusIcon(status), '已完成');
  assert.equal(context.statusIcon('running'), '进行中');
  assert.equal(context.statusIcon('cancelled'), '已取消');
});
