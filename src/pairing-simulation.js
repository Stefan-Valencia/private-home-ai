export const SIMULATED_WINDOW_DURATION_MS = 60_000;

export function initialPairingSimulationState() {
  return {
    windowStatus: "closed",
    windowExpiresAt: null,
    devices: [],
    nextDeviceNumber: 1,
    statusMessage: "Simulation only: no demo pairing window is open.",
  };
}

export function expirePairingWindow(state, now = Date.now(), expectedExpiresAt = state.windowExpiresAt) {
  if (
    state.windowStatus !== "open"
    || expectedExpiresAt !== state.windowExpiresAt
    || now < expectedExpiresAt
  ) {
    return state;
  }

  return {
    ...state,
    windowStatus: "expired",
    windowExpiresAt: null,
    statusMessage: "Simulation only: the demo window expired. No demo device was added.",
  };
}

export function focusKeyAfterWindowExpiry(activeFocusKey, focusIsInsideApp) {
  if (!focusIsInsideApp) return null;
  if (["ADD_DEMO_DEVICE", "SIMULATE_EXPIRY"].includes(activeFocusKey)) return "OPEN_WINDOW";
  return activeFocusKey || "page-heading";
}

export function focusKeyAfterPairingAction(action, windowStatus) {
  if (action === "OPEN_WINDOW" && windowStatus === "open") return "ADD_DEMO_DEVICE";
  if (["ADD_DEMO_DEVICE", "SIMULATE_EXPIRY"].includes(action)
    && ["expired", "used"].includes(windowStatus)) {
    return "OPEN_WINDOW";
  }
  if (action === "RESET_SIMULATION") return "RESET_SIMULATION";
  return "page-heading";
}

export function transitionPairingSimulation(state, action, now = Date.now()) {
  const current = expirePairingWindow(state, now);

  if (action.type === "RESET_SIMULATION") {
    return initialPairingSimulationState();
  }

  if (action.type === "OPEN_WINDOW") {
    if (current.windowStatus === "open") {
      throw new Error("A simulated pairing window is already open.");
    }
    return {
      ...current,
      windowStatus: "open",
      windowExpiresAt: now + SIMULATED_WINDOW_DURATION_MS,
      statusMessage: "Simulation only: the demo window is open for one synthetic device.",
    };
  }

  if (action.type === "SIMULATE_EXPIRY") {
    if (current.windowStatus !== "open") {
      throw new Error("There is no open simulated pairing window to expire.");
    }
    return {
      ...current,
      windowStatus: "expired",
      windowExpiresAt: null,
      statusMessage: "Simulation only: the demo window expired. No demo device was added.",
    };
  }

  if (action.type === "ADD_DEMO_DEVICE") {
    if (current.windowStatus === "expired") {
      throw new Error("The simulated pairing window expired. Open a new one to try again.");
    }
    if (current.windowStatus === "used") {
      throw new Error("This simulated window has already been used. Open a new one to add another demo device.");
    }
    if (current.windowStatus !== "open") {
      throw new Error("Open a simulated pairing window before adding a demo device.");
    }
    const number = current.nextDeviceNumber;
    const id = "SIM-" + String(number).padStart(3, "0");
    const device = {
      id,
      label: "Demo device " + number,
      status: "demo-active",
    };

    return {
      ...current,
      windowStatus: "used",
      windowExpiresAt: null,
      devices: [...current.devices, device],
      nextDeviceNumber: number + 1,
      statusMessage: "Simulation only: one demo device was added. It is not authenticated.",
    };
  }

  if (action.type === "REMOVE_DEMO_DEVICE") {
    const device = current.devices.find((item) => item.id === action.deviceId);
    if (device?.status === "demo-active") {
      return {
        ...current,
        devices: current.devices.map((item) => (
          item.id === action.deviceId ? { ...item, status: "demo-removed" } : item
        )),
        statusMessage: "Simulation only: the demo device was removed. No credential was revoked.",
      };
    }
    throw new Error("This demo device is no longer available.");
  }

  throw new Error("This action is not available in the current simulation state.");
}

export function attemptPairingSimulationAction(state, action, now = Date.now()) {
  const current = expirePairingWindow(state, now);
  try {
    return { state: transitionPairingSimulation(current, action, now), error: null };
  } catch (error) {
    return { state: current, error };
  }
}
