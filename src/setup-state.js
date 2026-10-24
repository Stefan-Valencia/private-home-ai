export const steps = [
  { id: "welcome", label: "Welcome" },
  { id: "setup_network", label: "Setup Wi-Fi" },
  { id: "identity", label: "Identity" },
  { id: "pairing", label: "Pair device" },
  { id: "wifi", label: "Home network" },
  { id: "connecting", label: "Connect" },
  { id: "ready", label: "Ready" },
];

export function initialState() {
  return {
    stage: "welcome",
    accessPoint: "off",
    demoDeviceId: null,
    pairingAuthorized: false,
    networkName: null,
    networkConnected: false,
    connectionError: null,
  };
}

export function transition(state, action) {
  if (action.type === "RESET") return initialState();

  if (action.type === "START_SETUP" && state.stage === "welcome") {
    return { ...state, stage: "setup_network", accessPoint: "simulated" };
  }

  if (action.type === "OPEN_SETUP_PAGE" && state.stage === "setup_network") {
    return { ...state, stage: "identity" };
  }

  if (action.type === "CREATE_DEMO_IDENTITY" && state.stage === "identity") {
    return { ...state, stage: "pairing", demoDeviceId: "DEMO-LOCAL-001" };
  }

  if (action.type === "SIMULATE_PAIRING" && state.stage === "pairing") {
    return { ...state, stage: "wifi", pairingAuthorized: true };
  }

  if (action.type === "USE_TEST_NETWORK" && state.stage === "wifi" && state.pairingAuthorized) {
    return { ...state, stage: "connecting", networkName: "Demo Home Network", connectionError: null };
  }

  if (action.type === "SIMULATE_NETWORK_FAILURE" && state.stage === "connecting") {
    return {
      ...state,
      stage: "wifi",
      networkConnected: false,
      connectionError: "The demo router is unavailable. Check the network and try again.",
    };
  }

  if (action.type === "SIMULATE_NETWORK_CONNECTED" && state.stage === "connecting") {
    return {
      ...state,
      stage: "ready",
      accessPoint: "closed",
      networkConnected: true,
    };
  }

  throw new Error("Action " + action.type + " is not allowed from stage " + state.stage);
}

