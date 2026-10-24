import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import {
  attemptPairingSimulationAction,
  expirePairingWindow,
  focusKeyAfterPairingAction,
  focusKeyAfterWindowExpiry,
  initialPairingSimulationState,
  SIMULATED_WINDOW_DURATION_MS,
  transitionPairingSimulation,
} from "../src/pairing-simulation.js";

test("the pairing simulation starts closed and contains no credentials", () => {
  const state = initialPairingSimulationState();

  assert.equal(state.windowStatus, "closed");
  assert.deepEqual(state.devices, []);
  assert.equal("privateKey" in state, false);
  assert.equal("credentials" in state, false);
  assert.match(state.statusMessage, /simulation only/i);
});

test("one open demo window enrolls exactly one synthetic device", () => {
  const opened = transitionPairingSimulation(initialPairingSimulationState(), { type: "OPEN_WINDOW" }, 1_000);
  assert.equal(opened.windowStatus, "open");
  assert.equal(opened.windowExpiresAt, 1_000 + SIMULATED_WINDOW_DURATION_MS);

  const enrolled = transitionPairingSimulation(opened, { type: "ADD_DEMO_DEVICE" }, 2_000);
  assert.equal(enrolled.windowStatus, "used");
  assert.equal(enrolled.windowExpiresAt, null);
  assert.deepEqual(enrolled.devices, [{ id: "SIM-001", label: "Demo device 1", status: "demo-active" }]);
  assert.match(enrolled.statusMessage, /not authenticated/i);
  assert.throws(
    () => transitionPairingSimulation(enrolled, { type: "ADD_DEMO_DEVICE" }, 3_000),
    /already been used/i,
  );
});

test("an expired demo window rejects enrollment and adds nothing", () => {
  const opened = transitionPairingSimulation(initialPairingSimulationState(), { type: "OPEN_WINDOW" }, 1_000);
  const beforeExpiry = expirePairingWindow(opened, opened.windowExpiresAt - 1);
  assert.equal(beforeExpiry, opened);

  const expired = expirePairingWindow(opened, opened.windowExpiresAt);
  assert.equal(expired.windowStatus, "expired");
  assert.deepEqual(expired.devices, []);
  assert.match(expired.statusMessage, /no demo device was added/i);
  assert.throws(
    () => transitionPairingSimulation(opened, { type: "ADD_DEMO_DEVICE" }, opened.windowExpiresAt),
    /expired\. Open a new one to try again/i,
  );
});

test("an enrollment at the exact deadline keeps the expired state when it is rejected", () => {
  const opened = transitionPairingSimulation(initialPairingSimulationState(), { type: "OPEN_WINDOW" }, 1_000);
  const result = attemptPairingSimulationAction(
    opened,
    { type: "ADD_DEMO_DEVICE" },
    opened.windowExpiresAt,
  );

  assert.equal(result.state.windowStatus, "expired");
  assert.deepEqual(result.state.devices, []);
  assert.match(result.error.message, /expired\. Open a new one to try again/i);
  assert.doesNotMatch(result.error.message, /ADD_DEMO_DEVICE/);
});

test("a delayed expiry callback cannot close a newer demo window", () => {
  const first = transitionPairingSimulation(initialPairingSimulationState(), { type: "OPEN_WINDOW" }, 1_000);
  const expired = transitionPairingSimulation(first, { type: "SIMULATE_EXPIRY" }, 2_000);
  const second = transitionPairingSimulation(expired, { type: "OPEN_WINDOW" }, 3_000);

  const staleTimer = expirePairingWindow(second, 70_000, first.windowExpiresAt);
  assert.equal(staleTimer, second);
  assert.equal(staleTimer.windowStatus, "open");
});

test("removed demo entries stay visibly removed and a later demo gets a new id", () => {
  let state = transitionPairingSimulation(initialPairingSimulationState(), { type: "OPEN_WINDOW" }, 1_000);
  state = transitionPairingSimulation(state, { type: "ADD_DEMO_DEVICE" }, 2_000);
  state = transitionPairingSimulation(state, { type: "REMOVE_DEMO_DEVICE", deviceId: "SIM-001" }, 3_000);
  assert.equal(state.devices[0].status, "demo-removed");
  assert.match(state.statusMessage, /no credential was revoked/i);
  assert.throws(
    () => transitionPairingSimulation(state, { type: "REMOVE_DEMO_DEVICE", deviceId: "SIM-001" }, 4_000),
    /no longer available/i,
  );

  state = transitionPairingSimulation(state, { type: "OPEN_WINDOW" }, 5_000);
  state = transitionPairingSimulation(state, { type: "ADD_DEMO_DEVICE" }, 6_000);
  assert.deepEqual(state.devices.map((item) => item.id), ["SIM-001", "SIM-002"]);
});

test("reset clears all in-memory demo devices and pairing state", () => {
  let state = transitionPairingSimulation(initialPairingSimulationState(), { type: "OPEN_WINDOW" }, 1_000);
  state = transitionPairingSimulation(state, { type: "ADD_DEMO_DEVICE" }, 2_000);
  state = transitionPairingSimulation(state, { type: "RESET_SIMULATION" }, 3_000);

  assert.deepEqual(state, initialPairingSimulationState());
});

test("expiry moves focus to retry only when the focused control disappears", () => {
  assert.equal(focusKeyAfterWindowExpiry("ADD_DEMO_DEVICE", true), "OPEN_WINDOW");
  assert.equal(focusKeyAfterWindowExpiry("SIMULATE_EXPIRY", true), "OPEN_WINDOW");
  assert.equal(focusKeyAfterWindowExpiry("RESET_SIMULATION", true), "RESET_SIMULATION");
  assert.equal(focusKeyAfterWindowExpiry("REMOVE_DEMO_DEVICE:SIM-001", true), "REMOVE_DEMO_DEVICE:SIM-001");
  assert.equal(focusKeyAfterWindowExpiry("BACK_TO_SETUP", true), "BACK_TO_SETUP");
  assert.equal(focusKeyAfterWindowExpiry("page-heading", true), "page-heading");
  assert.equal(focusKeyAfterWindowExpiry(undefined, true), "page-heading");
  assert.equal(focusKeyAfterWindowExpiry("RESET_SIMULATION", false), null);
});

test("pairing actions focus the next step when the current control disappears", () => {
  assert.equal(focusKeyAfterPairingAction("OPEN_WINDOW", "open"), "ADD_DEMO_DEVICE");
  assert.equal(focusKeyAfterPairingAction("ADD_DEMO_DEVICE", "used"), "OPEN_WINDOW");
  assert.equal(focusKeyAfterPairingAction("ADD_DEMO_DEVICE", "expired"), "OPEN_WINDOW");
  assert.equal(focusKeyAfterPairingAction("SIMULATE_EXPIRY", "expired"), "OPEN_WINDOW");
  assert.equal(focusKeyAfterPairingAction("RESET_SIMULATION", "closed"), "RESET_SIMULATION");
  assert.equal(focusKeyAfterPairingAction("REMOVE_DEMO_DEVICE", "used"), "device-list-heading");
});

test("the pairing screen keeps simulation and accessibility boundaries visible", async () => {
  const app = await readFile(new URL("../src/app.js", import.meta.url), "utf8");
  const index = await readFile(new URL("../index.html", import.meta.url), "utf8");
  const pairing = await readFile(new URL("../src/pairing-simulation.js", import.meta.url), "utf8");
  const styles = await readFile(new URL("../src/styles.css", import.meta.url), "utf8");

  assert.match(app, /SIMULATION ONLY/);
  assert.match(index, /id="app-announcements"[^>]*aria-live="polite"/);
  assert.match(app, /function announce\(/);
  assert.match(app, /role\", \"alert/);
  assert.match(app, /focusKeyAfterPairingAction/);
  assert.match(app, /focusKeyAfterWindowExpiry/);
  assert.match(app, /data-focus-key/);
  assert.match(app, /const devicesHeading = element\("h2", "device-section-title", "Demo devices"\);[\s\S]*?devicesHeading\.tabIndex = -1;[\s\S]*?devicesHeading\.dataset\.focusKey = "device-list-heading";[\s\S]*?devices\.append\(devicesHeading\);/);
  assert.match(styles, /\.button:focus-visible\s*\{\s*outline: 3px solid #176b4b;/);
  assert.doesNotMatch(app + pairing, /\b(localStorage|sessionStorage|indexedDB|document\.cookie|fetch\s*\()/i);
  assert.match(index, /no appliance Wi-Fi setup, external services, or credentials are used/i);
  assert.match(index, /connect-src\s+'none'/i);
});
