import { initialState, steps, transition } from "./setup-state.js";
import {
  attemptPairingSimulationAction,
  expirePairingWindow,
  focusKeyAfterPairingAction,
  focusKeyAfterWindowExpiry,
  initialPairingSimulationState,
} from "./pairing-simulation.js";

const root = document.querySelector("#app");
const announcer = document.querySelector("#app-announcements");
let state = initialState();
let activeView = "setup";
let pairingState = initialPairingSimulationState();
let pairingError = null;
let pairingExpiryTimer = null;

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function announce(message) {
  if (!announcer || !message) return;
  announcer.textContent = "";
  requestAnimationFrame(() => {
    announcer.textContent = message;
  });
}

function focusControl(focusKey) {
  if (!focusKey) return;
  const target = Array.from(root.querySelectorAll("[data-focus-key]"))
    .find((item) => item.dataset.focusKey === focusKey);
  (target || root.querySelector("h1"))?.focus();
}

function actionButton(label, onClick, secondary, getAnnouncement, focusKey, getNextFocusKey) {
  const control = element("button", secondary ? "button button-secondary" : "button button-primary", label);
  control.type = "button";
  if (focusKey) control.dataset.focusKey = focusKey;
  control.addEventListener("click", () => {
    onClick();
    render();
    focusControl(getNextFocusKey ? getNextFocusKey() : "page-heading");
    if (getAnnouncement) announce(getAnnouncement());
  });
  return control;
}

function button(label, action, secondary) {
  return actionButton(label, () => {
    state = transition(state, { type: action });
  }, secondary);
}

function schedulePairingExpiry() {
  clearTimeout(pairingExpiryTimer);
  pairingExpiryTimer = null;
  if (pairingState.windowStatus !== "open") return;

  const expectedExpiresAt = pairingState.windowExpiresAt;
  pairingExpiryTimer = setTimeout(() => {
    const next = expirePairingWindow(pairingState, Date.now(), expectedExpiresAt);
    if (next === pairingState) return;
    const focusKey = focusKeyAfterWindowExpiry(
      document.activeElement?.dataset?.focusKey,
      root.contains(document.activeElement),
    );
    pairingState = next;
    pairingError = null;
    if (activeView === "pairing") {
      render();
      announce(pairingState.statusMessage);
      focusControl(focusKey);
    }
  }, Math.max(0, expectedExpiresAt - Date.now()));
}

function pairingButton(label, action, secondary, deviceId) {
  const control = actionButton(label, () => {
    const result = attemptPairingSimulationAction(
      pairingState,
      { type: action, deviceId },
      Date.now(),
    );
    pairingState = result.state;
    pairingError = result.error instanceof Error ? result.error.message : null;
    schedulePairingExpiry();
  }, secondary, () => pairingError ? "" : pairingState.statusMessage,
  deviceId ? action + ":" + deviceId : action,
  () => focusKeyAfterPairingAction(action, pairingState.windowStatus));
  control.dataset.pairingAction = action;
  return control;
}

function panel(title, description) {
  const card = element("section", "setup-card");
  card.setAttribute("aria-labelledby", "step-title");
  card.append(element("p", "eyebrow", "APPLIANCE SETUP"));
  card.append(element("h1", "step-title", title));
  card.lastChild.id = "step-title";
  card.lastChild.tabIndex = -1;
  card.lastChild.dataset.focusKey = "page-heading";
  card.append(element("p", "step-description", description));
  return card;
}

function renderProgress() {
  const progress = element("div", "progress");
  const currentIndex = steps.findIndex((step) => step.id === state.stage);
  const mobileSummary = element("p", "progress-mobile");
  mobileSummary.append(element("span", "", "Step " + (currentIndex + 1) + " of " + steps.length));
  mobileSummary.append(element("strong", "", steps[currentIndex].label));
  progress.append(mobileSummary);

  const list = element("ol", "progress-list");

  steps.forEach((step, index) => {
    const item = element("li", "progress-item");
    if (index < currentIndex) item.classList.add("is-complete");
    if (index === currentIndex) {
      item.classList.add("is-current");
      item.setAttribute("aria-current", "step");
    }
    item.append(element("span", "progress-number", String(index + 1)));
    item.append(element("span", "progress-label", step.label));
    list.append(item);
  });

  progress.append(list);
  return progress;
}

function renderStage() {
  if (state.stage === "welcome") {
    const card = panel("Set up your private AI appliance", "A guided simulation walks through how a real appliance could prepare for devices on your home network.");
    card.append(element("div", "info-box", "This clickable prototype simulates each step. It does not turn on Wi-Fi, create cryptographic keys, pair a real device, or collect network credentials."));
    card.append(button("Start setup simulation", "START_SETUP"));
    return card;
  }

  if (state.stage === "identity") {
    const card = panel("Create appliance identity", "The appliance creates its identity during your first setup, so it is unique to your home.");
    card.append(element("div", "identity-preview", "DEMO-LOCAL-001"));
    card.append(element("p", "fine-print", "Demo identifier only. No cryptographic keys are created in this prototype."));
    card.append(button("Continue to device pairing", "CREATE_DEMO_IDENTITY"));
    return card;
  }

  if (state.stage === "setup_network") {
    const card = panel("Connect to the setup network", "On a real appliance, connect your phone to PrivateAI-Setup, then open this setup page.");
    card.append(element("div", "info-box", "This prototype does not create a Wi-Fi network. The next button only simulates opening the setup page."));
    card.append(button("Simulate opening the setup page", "OPEN_SETUP_PAGE"));
    return card;
  }

  if (state.stage === "pairing") {
    const card = panel("Pair your phone", "A real appliance will require a physical action before it trusts a new device.");
    card.append(element("div", "info-box", "This button changes only the demo state. It does not sense a hardware button or authenticate a phone."));
    card.append(button("Simulate physical pairing button press", "SIMULATE_PAIRING"));
    return card;
  }

  if (state.stage === "wifi") {
    const card = panel("Connect to your home network", "Use the preselected test network to continue. This prototype does not scan for networks or ask for a password.");
    const network = element("div", "network-option");
    const icon = element("span", "network-icon", "⌁");
    icon.setAttribute("aria-hidden", "true");
    network.append(icon);
    const details = element("span", "network-details");
    details.append(element("strong", "", "Demo Home Network"));
    details.append(element("span", "", "Preselected test network · no password needed"));
    network.append(details);
    network.append(element("span", "network-check", "SELECTED"));
    card.append(network);
    if (state.connectionError) {
      const error = element("div", "error-box", state.connectionError);
      error.setAttribute("role", "alert");
      card.append(error);
    }
    card.append(button(state.connectionError ? "Try the demo network again" : "Continue with test network", "USE_TEST_NETWORK"));
    return card;
  }

  if (state.stage === "connecting") {
    const card = panel("Joining your network", "Choose whether the demo network connects or is temporarily unavailable. No real connection is attempted.");
    card.append(element("div", "connection-status", "Test network: " + state.networkName));
    card.append(button("Simulate successful connection", "SIMULATE_NETWORK_CONNECTED"));
    card.append(button("Simulate network unavailable", "SIMULATE_NETWORK_FAILURE", true));
    return card;
  }

  const card = panel("Setup simulation complete", "The demo has reached the end of its setup flow.");
  card.append(element("div", "ready-status", "Setup simulation complete · no real device is authenticated"));
  card.append(element("p", "fine-print", "The real Wi-Fi radio, device pairing, and local AI service are not connected in this prototype."));
  card.append(actionButton("Explore device management simulation", () => {
    activeView = "pairing";
  }, true));
  card.append(button("Run setup again", "RESET", true));
  return card;
}

function renderPairingSimulation() {
  const card = panel("Manage demo devices", "Explore the pairing and removal journey without connecting or authenticating a real device.");
  card.append(element("div", "simulation-only-label", "SIMULATION ONLY · data stays in this page and is not saved"));
  card.append(element("div", "info-box", "This screen creates no keys, credentials, or trusted-device records. Refreshing the page clears the demo."));

  const status = element("p", "pairing-status", pairingState.statusMessage);
  card.append(status);

  if (pairingError) {
    const error = element("div", "error-box", pairingError);
    error.setAttribute("role", "alert");
    card.append(error);
  }

  if (pairingState.windowStatus === "open") {
    card.append(pairingButton("Add one demo device", "ADD_DEMO_DEVICE"));
    card.append(pairingButton("Simulate pairing window expiry", "SIMULATE_EXPIRY", true));
  } else {
    card.append(pairingButton(
      pairingError ? "Retry with a new simulated window" : "Open simulated pairing window",
      "OPEN_WINDOW",
    ));
    if (pairingState.windowStatus === "expired") {
      card.append(pairingButton("Test rejection of an expired demo invitation", "ADD_DEMO_DEVICE", true));
    }
  }

  const devices = element("section", "device-section");
  const devicesHeading = element("h2", "device-section-title", "Demo devices");
  devicesHeading.tabIndex = -1;
  devicesHeading.dataset.focusKey = "device-list-heading";
  devices.append(devicesHeading);
  if (pairingState.devices.length === 0) {
    devices.append(element("p", "fine-print", "No demo devices have been added."));
  } else {
    const list = element("ul", "device-list");
    pairingState.devices.forEach((device) => {
      const item = element("li", "device-row");
      const details = element("div", "device-details");
      details.append(element("strong", "", device.label));
      details.append(element("span", "device-id", device.id + " · simulation only"));
      details.append(element(
        "span",
        device.status === "demo-active" ? "device-state" : "device-state is-removed",
        device.status === "demo-active" ? "Demo entry · not authenticated" : "Removed in this simulation",
      ));
      item.append(details);
      if (device.status === "demo-active") {
        item.append(pairingButton("Remove " + device.label + " (simulation)", "REMOVE_DEMO_DEVICE", true, device.id));
      }
      list.append(item);
    });
    devices.append(list);
  }
  card.append(devices);
  card.append(pairingButton("Reset demo devices", "RESET_SIMULATION", true));
  card.append(actionButton("Back to setup simulation", () => {
    activeView = "setup";
  }, true, undefined, "BACK_TO_SETUP"));
  return card;
}

function render() {
  root.replaceChildren();
  root.append(element("div", "simulation-banner", "DEVELOPMENT SIMULATION — no real device or network changes"));
  if (activeView === "pairing") {
    root.append(renderPairingSimulation());
    return;
  }
  root.append(renderProgress());
  root.append(renderStage());
}

render();
