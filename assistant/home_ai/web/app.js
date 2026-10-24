const messageList = document.querySelector("#messages");
const form = document.querySelector("#chat-form");
const promptField = document.querySelector("#prompt");
const sendButton = document.querySelector("#send-button");
const fileInput = document.querySelector("#document-file");
const uploadStatus = document.querySelector("#upload-status");
const documentList = document.querySelector("#document-list");
const documentCount = document.querySelector("#document-count");
const modelStatus = document.querySelector("#model-status");
const statusDot = document.querySelector("#status-dot");
const modelCheckButton = document.querySelector("#model-check-button");

function addMessage(role, text) {
  const item = document.createElement("div");
  item.className = `message ${role === "user" ? "user-message" : "assistant-message"}`;
  const label = document.createElement("span");
  label.className = "message-label";
  label.textContent = role === "user" ? "You" : "Assistant";
  const content = document.createElement("p");
  content.textContent = text;
  item.append(label, content);
  messageList.append(item);
  item.scrollIntoView({ block: "nearest", behavior: "smooth" });
}

async function loadStatus() {
  modelCheckButton.disabled = true;
  try {
    const response = await fetch("/api/health", { cache: "no-store" });
    const result = await response.json();
    const ready = response.ok && result.status === "ready";
    modelStatus.textContent = ready ? "Local model ready" : "Local model unavailable — start it to chat";
    statusDot.classList.toggle("ready", ready);
  } catch {
    modelStatus.textContent = "Local assistant service unavailable";
    statusDot.classList.remove("ready");
  } finally {
    modelCheckButton.disabled = false;
  }
}

async function loadDocuments({ focusDocumentId = null, restoreRemovalFocus = false } = {}) {
  try {
    const response = await fetch("/api/documents", { cache: "no-store" });
    if (!response.ok) throw new Error("Could not load documents.");
    const { documents } = await response.json();
    documentList.replaceChildren();
    documentCount.textContent = String(documents.length);
    for (const doc of documents) {
      const item = document.createElement("li");
      const name = document.createElement("span");
      name.className = "doc-name";
      name.textContent = doc.filename;
      const detail = document.createElement("span");
      detail.className = "doc-detail";
      detail.textContent = `${doc.pages} ${doc.pages === 1 ? "page" : "pages"}`;
      const remove = document.createElement("button");
      remove.className = "remove-button";
      remove.type = "button";
      remove.textContent = "Remove";
      remove.dataset.documentId = doc.document_id;
      remove.setAttribute("aria-label", `Remove ${doc.filename} from the local index`);
      remove.addEventListener("click", async () => {
        remove.disabled = true;
        const removeButtons = Array.from(documentList.querySelectorAll(".remove-button"));
        const buttonIndex = removeButtons.indexOf(remove);
        const nextButton = removeButtons[buttonIndex + 1] || removeButtons[buttonIndex - 1];
        const nextDocumentId = nextButton?.dataset.documentId || null;
        try {
          const response = await fetch(`/api/documents/${encodeURIComponent(doc.document_id)}`, {
            method: "DELETE",
          });
          const result = await response.json();
          if (!response.ok) throw new Error(result.error || "The document could not be removed.");
          uploadStatus.textContent = `${doc.filename} removed from the local index.`;
          await loadDocuments({ focusDocumentId: nextDocumentId, restoreRemovalFocus: true });
        } catch (error) {
          uploadStatus.textContent = error.message || "The document could not be removed.";
          remove.disabled = false;
          remove.focus();
        }
      });
      const details = document.createElement("div");
      details.className = "doc-details";
      details.append(name, detail);
      item.append(details, remove);
      documentList.append(item);
    }
    if (documents.length === 0) {
      const empty = document.createElement("li");
      empty.className = "empty-documents";
      empty.textContent = "No documents added yet.";
      documentList.append(empty);
    }
    if (restoreRemovalFocus) {
      const nextButton = Array.from(documentList.querySelectorAll(".remove-button"))
        .find((button) => button.dataset.documentId === focusDocumentId);
      (nextButton || fileInput).focus();
    }
  } catch {
    uploadStatus.textContent = "The document list could not be loaded.";
    if (restoreRemovalFocus) fileInput.focus();
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const prompt = promptField.value.trim();
  if (!prompt || sendButton.disabled) return;
  addMessage("user", prompt);
  promptField.value = "";
  sendButton.disabled = true;
  sendButton.textContent = "Thinking…";
  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt }),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "The assistant could not answer.");
    addMessage("assistant", result.answer);
  } catch (error) {
    addMessage("assistant", error.message || "The local assistant could not complete that request.");
  } finally {
    sendButton.disabled = false;
    sendButton.innerHTML = 'Send <span aria-hidden="true">↗</span>';
    promptField.focus();
  }
});

promptField.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    form.requestSubmit();
  }
});

fileInput.addEventListener("change", async () => {
  const file = fileInput.files?.[0];
  if (!file) return;
  uploadStatus.textContent = `Adding ${file.name}…`;
  try {
    const response = await fetch("/api/documents", {
      method: "POST",
      headers: { "Content-Type": "application/octet-stream", "X-Filename": encodeURIComponent(file.name) },
      body: file,
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "The document could not be added.");
    uploadStatus.textContent = `${result.filename} added. You can ask questions about it.`;
    await loadDocuments();
  } catch (error) {
    uploadStatus.textContent = error.message || "The document could not be added.";
  } finally {
    fileInput.value = "";
  }
});

void loadStatus();
void loadDocuments();
modelCheckButton.addEventListener("click", () => void loadStatus());
window.setInterval(() => {
  if (!statusDot.classList.contains("ready")) void loadStatus();
}, 15_000);
