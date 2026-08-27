const form = document.getElementById("chatForm");
const input = document.getElementById("messageInput");
const button = document.getElementById("sendButton");
const messages = document.getElementById("messages");
const typingIndicator = document.getElementById("typingIndicator");

let isLoading = false;

function updateControls() {
  button.disabled = isLoading || input.value.trim() === "";
  input.disabled = isLoading;
}

function updateEmptyState() {
  const hasMessages = messages.children.length > 0;
  const existing = document.getElementById("emptyState");

  if (hasMessages) {
    if (existing && existing.parentNode) {
      existing.parentNode.removeChild(existing);
    }
    return;
  }

  // Recreate the empty state if the history becomes empty again.
  if (!existing) {
    const el = document.createElement("div");
    el.id = "emptyState";
    el.className = "empty-state";
    el.setAttribute("data-testid", "empty-state");
    el.textContent = "No question yet. Ask something about the OBP API.";
    messages.insertAdjacentElement("afterend", el);
  }
}

function addMessage(text, role, { isError = false, sources = [] } = {}) {
  const wrapper = document.createElement("div");
  const messageTestId = isError
    ? "message-error"
    : role === "user"
      ? "message-question"
      : "message-answer";

  wrapper.className = `message ${role}${isError ? " error" : ""}`;
  wrapper.setAttribute("data-testid", "message");
  wrapper.setAttribute("data-role", role);
  wrapper.setAttribute("data-kind", isError ? "error" : role);

  const content = document.createElement("span");
  content.setAttribute("data-testid", messageTestId);
  content.textContent = text;
  wrapper.appendChild(content);

  // Traceability: the endpoints actually used to build the answer are
  // displayed to the user and exposed to the test layer.
  if (sources.length > 0) {
    const sourcesEl = document.createElement("div");
    sourcesEl.className = "message-sources";
    sourcesEl.setAttribute("data-testid", "message-sources");
    sourcesEl.textContent = `Sources: ${sources.join(", ")}`;
    wrapper.appendChild(sourcesEl);
  }

  messages.appendChild(wrapper);
  messages.scrollTop = messages.scrollHeight;
  updateEmptyState();
}

function showTyping(isVisible) {
  typingIndicator.classList.toggle("hidden", !isVisible);
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const text = input.value.trim();
  if (!text || isLoading) {
    return;
  }

  addMessage(text, "user");
  input.value = "";
  isLoading = true;
  updateControls();
  showTyping(true);

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text }),
    });

    const data = await response.json();
    if (!response.ok || data.error) {
      addMessage(data.error || "An error occurred.", "assistant", { isError: true });
    } else {
      addMessage(data.answer, "assistant", { sources: data.sources || [] });
    }
  } catch (error) {
    addMessage("Service unavailable. Please try again later.", "assistant", {
      isError: true,
    });
  } finally {
    isLoading = false;
    updateControls();
    showTyping(false);
  }
});

input.addEventListener("input", updateControls);
updateControls();
updateEmptyState();
