import { initialState, steps, transition } from "./setup-state.js";

const root = document.querySelector("#app");
let state = initialState();

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function button(label, action, secondary) {
  const control = element("button", secondary ? "button button-secondary" : "button button-primary", label);
  control.type = "button";
  control.addEventListener("click", () => {
    state = transition(state, { type: action });
    render();
    root.querySelector("h1")?.focus();
  });
  return control;
}

function panel(title, description) {
  const card = element("section", "setup-card");
  card.setAttribute("aria-labelledby", "step-title");
  card.append(element("p", "eyebrow", "APPLIANCE SETUP"));
  card.append(element("h1", "step-title", title));
  card.lastChild.id = "step-title";
  card.lastChild.tabIndex = -1;
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
    const card = panel("Set up your private AI appliance", "A short guided setup gets your appliance ready for trusted devices on your home network.");
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
    card.append(element("div", "info-box", "For this simulation, use the button below to stand in for pressing the appliance pairing button."));
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

  const card = panel("Your appliance is ready", "Your trusted device can now open the local AI interface on your home network.");
  card.append(element("div", "ready-status", "Setup complete · simulation only"));
  card.append(element("p", "fine-print", "The real Wi-Fi radio, device pairing, and local AI service are not connected in this prototype."));
  card.append(button("Run setup again", "RESET", true));
  return card;
}

function render() {
  root.replaceChildren();
  root.append(element("div", "simulation-banner", "DEVELOPMENT SIMULATION — no real device or network changes"));
  root.append(renderProgress());
  root.append(renderStage());
}

render();

