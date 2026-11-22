// Exercise the page's event handlers with Node's built-in test runner and a small DOM stub.
const assert = require("node:assert/strict");
const { webcrypto } = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");
const source = fs.readFileSync(path.join(__dirname, "../web/app.js"), "utf8");

function page(storage = new Map()) {
  const nodes = new Map();
  function element(selector) {
    if (!nodes.has(selector)) {
      nodes.set(selector, {
        textContent: "", addEventListener(type, fn) { this[type] = fn; }, setAttribute() {},
      });
    }
    return nodes.get(selector);
  }
  const scope = vm.createContext({
    document: { querySelector: element, querySelectorAll: () => [] },
    window: { isSecureContext: true }, crypto: webcrypto,
    localStorage: { getItem: k => storage.get(k), setItem: (k, v) => storage.set(k, v) },
    // Each test drives its own request. Leave the unrelated page bootstrap pending.
    fetch: () => new Promise(() => {}),
  });
  const run = code => vm.runInContext(code, scope);
  run(source);
  return { run, scope, element };
}

test("API sends the same browser UUID after a reload", async () => {
  const storage = new Map();
  const first = page(storage).run("state.visitorId");
  const { run, scope } = page(storage);
  let headers;
  scope.fetch = async (_, options) => {
    headers = options.headers;
    return { ok: true, json: async () => [] };
  };
  await run("api('/api/reminders')");
  assert.match(first, /^[0-9a-f-]{36}$/);
  assert.equal(headers["X-Visitor-Id"], first);
  assert.notEqual(page().run("state.visitorId"), first);
});

test("a refresh error leaves successful process cards visible", async () => {
  const { run, element } = page();
  run(`setLoading = () => {};
       api = async () => ({reminder: {id: 7}});
       renderResult = () => { $("#peh-body").textContent = "Saved"; $("#base-body").textContent = "Asked"; };
       loadReminders = async () => { throw Error("offline"); };`);
  const result = await run('process({append() {}}, {label: "test"})');
  assert.equal(result.reminder.id, 7);
  assert.equal(element("#peh-body").textContent, "Saved");
  assert.equal(element("#base-body").textContent, "Asked");
  assert.match(element("#reminder-note").textContent, /couldn't refresh reminders/i);
});

test("guide retries a failed step and reports the actual comparison card", async () => {
  const { run, element } = page();
  run("resetDemo = async () => {}; setBook = () => {}; runText = async () => null;");
  await element("#guide-next").click();
  assert.equal(run("stepIndex"), -1);
  assert.match(element("#guide-next").textContent, /Retry/);
  element("#peh-body .decision").textContent = "Asked which doctor.";
  for (const [index, message] of ["Asked for more context.", "Comparison is off.", "Strong AI unavailable."].entries()) {
    element("#base-body .decision").textContent = index === 0 ? message : "";
    element("#base-body").textContent = message;
    run(`runText = async () => ({pending: {candidates: [{name: "Dr. Subramanian"}]}}); answer = async () => ({})`);
    await element("#guide-next").click();
    assert.equal(run("stepIndex"), index);
    assert.ok(element("#guide-text").textContent.includes(message));
    assert.ok(element("#guide-text").textContent.includes("Asked which doctor."));
  }
});

for (const failure of ["construct", "start"]) {
  test(`recorder ${failure} failure releases the acquired microphone`, async () => {
    const { scope, element, run } = page();
    let stopped = 0;
    scope.navigator = { mediaDevices: { getUserMedia: async () => ({
      getTracks: () => [{ stop() { stopped++; } }],
    }) } };
    scope.window.MediaRecorder = scope.MediaRecorder = class {
      static isTypeSupported() { return true; }
      constructor() { if (failure === "construct") throw Error("unsupported"); }
      start() { throw Error("could not start"); }
    };
    await element("#mic").click();
    assert.equal(stopped, 1);
    assert.equal(run("recorder"), null);
    assert.match(element("#banner-text").textContent, /Microphone not available/);
  });
}
