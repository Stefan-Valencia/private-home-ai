import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import { initialState, transition } from "../src/setup-state.js";

test("the setup simulation reaches ready through the expected stages", () => {
  let state = initialState();
  assert.equal(state.stage, "welcome");

  state = transition(state, { type: "START_SETUP" });
  assert.equal(state.stage, "setup_network");
  assert.equal(state.accessPoint, "simulated");

  state = transition(state, { type: "OPEN_SETUP_PAGE" });
  assert.equal(state.stage, "identity");

  state = transition(state, { type: "CREATE_DEMO_IDENTITY" });
  assert.equal(state.stage, "pairing");
  assert.equal(state.demoDeviceId, "DEMO-LOCAL-001");

  state = transition(state, { type: "SIMULATE_PAIRING" });
  assert.equal(state.stage, "wifi");
  assert.equal(state.pairingAuthorized, true);

  state = transition(state, { type: "USE_TEST_NETWORK" });
  assert.equal(state.stage, "connecting");
  assert.equal(state.networkName, "Demo Home Network");

  state = transition(state, { type: "SIMULATE_NETWORK_CONNECTED" });
  assert.equal(state.stage, "ready");
  assert.equal(state.networkConnected, true);
  assert.equal(state.accessPoint, "closed");
});

test("the simulation rejects skipped or out-of-order steps", () => {
  const state = initialState();
  assert.throws(
    () => transition(state, { type: "SIMULATE_PAIRING" }),
    /not allowed from stage welcome/,
  );
  assert.throws(
    () => transition(state, { type: "USE_TEST_NETWORK" }),
    /not allowed from stage welcome/,
  );
});

test("every non-reset action is rejected when it is not valid for the current stage", () => {
  const actions = [
    "START_SETUP",
    "OPEN_SETUP_PAGE",
    "CREATE_DEMO_IDENTITY",
    "SIMULATE_PAIRING",
    "USE_TEST_NETWORK",
    "SIMULATE_NETWORK_CONNECTED",
    "SIMULATE_NETWORK_FAILURE",
  ];
  const allowed = {
    welcome: ["START_SETUP"],
    setup_network: ["OPEN_SETUP_PAGE"],
    identity: ["CREATE_DEMO_IDENTITY"],
    pairing: ["SIMULATE_PAIRING"],
    wifi: ["USE_TEST_NETWORK"],
    connecting: ["SIMULATE_NETWORK_CONNECTED", "SIMULATE_NETWORK_FAILURE"],
    ready: [],
  };
  const states = [initialState()];
  let state = initialState();
  for (const action of [
    "START_SETUP",
    "OPEN_SETUP_PAGE",
    "CREATE_DEMO_IDENTITY",
    "SIMULATE_PAIRING",
    "USE_TEST_NETWORK",
    "SIMULATE_NETWORK_CONNECTED",
  ]) {
    state = transition(state, { type: action });
    states.push(state);
  }

  for (const stageState of states) {
    for (const action of actions) {
      if (!allowed[stageState.stage].includes(action)) {
        assert.throws(() => transition(stageState, { type: action }));
      }
    }
  }
});

test("an unavailable demo network returns to selection and can be retried", () => {
  let state = initialState();
  for (const type of [
    "START_SETUP",
    "OPEN_SETUP_PAGE",
    "CREATE_DEMO_IDENTITY",
    "SIMULATE_PAIRING",
    "USE_TEST_NETWORK",
    "SIMULATE_NETWORK_FAILURE",
  ]) {
    state = transition(state, { type });
  }

  assert.equal(state.stage, "wifi");
  assert.equal(state.networkConnected, false);
  assert.equal(state.accessPoint, "simulated");
  assert.match(state.connectionError, /demo router is unavailable/i);
  assert.throws(
    () => transition(state, { type: "SIMULATE_NETWORK_CONNECTED" }),
    /not allowed from stage wifi/,
  );

  state = transition(state, { type: "USE_TEST_NETWORK" });
  assert.equal(state.stage, "connecting");
  assert.equal(state.connectionError, null);

  state = transition(state, { type: "SIMULATE_NETWORK_CONNECTED" });
  assert.equal(state.stage, "ready");
  assert.equal(state.networkConnected, true);
  assert.equal(state.accessPoint, "closed");
});

test("reset clears setup state", () => {
  let state = transition(initialState(), { type: "START_SETUP" });
  state = transition(state, { type: "OPEN_SETUP_PAGE" });
  state = transition(state, { type: "CREATE_DEMO_IDENTITY" });
  state = transition(state, { type: "SIMULATE_PAIRING" });
  state = transition(state, { type: "USE_TEST_NETWORK" });
  state = transition(state, { type: "SIMULATE_NETWORK_CONNECTED" });

  const reset = transition(state, { type: "RESET" });
  assert.deepEqual(reset, initialState());
});

test("reset works from partial setup stages", () => {
  const prefixes = [
    ["START_SETUP"],
    ["START_SETUP", "OPEN_SETUP_PAGE"],
    ["START_SETUP", "OPEN_SETUP_PAGE", "CREATE_DEMO_IDENTITY"],
    ["START_SETUP", "OPEN_SETUP_PAGE", "CREATE_DEMO_IDENTITY", "SIMULATE_PAIRING"],
  ];

  for (const prefix of prefixes) {
    const partial = prefix.reduce((state, type) => transition(state, { type }), initialState());
    const reset = transition(partial, { type: "RESET" });
    assert.deepEqual(reset, initialState());
  }
});

test("the prototype state contains no Wi-Fi password or private key", () => {
  let state = transition(initialState(), { type: "START_SETUP" });
  state = transition(state, { type: "OPEN_SETUP_PAGE" });
  state = transition(state, { type: "CREATE_DEMO_IDENTITY" });
  state = transition(state, { type: "SIMULATE_PAIRING" });
  state = transition(state, { type: "USE_TEST_NETWORK" });

  assert.equal("password" in state, false);
  assert.equal("privateKey" in state, false);
  assert.equal("credentials" in state, false);
});

test("the onboarding UI does not collect credentials or allow outbound connections", async () => {
  const [html, app, styles] = await Promise.all([
    readFile(new URL("../index.html", import.meta.url), "utf8"),
    readFile(new URL("../src/app.js", import.meta.url), "utf8"),
    readFile(new URL("../src/styles.css", import.meta.url), "utf8"),
  ]);

  assert.doesNotMatch(html, /type=["']password["']/i);
  assert.doesNotMatch(html, /https?:\/\//i);
  assert.doesNotMatch(app, /\b(fetch|XMLHttpRequest|WebSocket|EventSource)\b/);
  assert.doesNotMatch(app, /type\s*=\s*["']password["']/i);
  assert.match(app, /setAttribute\(["']role["'],\s*["']alert["']\)/);
  assert.match(html, /connect-src\s+'none'/i);
  assert.doesNotMatch(styles, /url\(\s*["']?https?:/i);
});


test("every active setup stage shows an announced reset control", async () => {
  const app = await readFile(new URL("../src/app.js", import.meta.url), "utf8");
  const resetControl = app.match(/function renderSetupResetControl\(\) \{[\s\S]*?\n\}/)?.[0];

  assert.ok(resetControl, "The reset control renderer should exist.");
  assert.match(resetControl, /if \(state\.stage === "welcome"\) return null;/);
  assert.match(resetControl, /state = transition\(state, \{ type: "RESET" \}\);/);
  assert.match(resetControl, /["']Reset setup simulation["']/);
  assert.match(resetControl, /undefined,\s*\(\) => "page-heading"/);
  assert.match(app, /focusControl\(getNextFocusKey \? getNextFocusKey\(\) : "page-heading"\)/);
  assert.match(app, /if \(getAnnouncement\) announce\(getAnnouncement\(\)\);/);
  assert.match(app, /Setup simulation reset\. No real Wi-Fi or device changes were made\./);
  assert.match(app, /const stage = renderStage\(\);[\s\S]*?const resetControl = renderSetupResetControl\(\);[\s\S]*?if \(resetControl\) stage\.append\(resetControl\);/);
  assert.doesNotMatch(app, /Run setup again/);
});

