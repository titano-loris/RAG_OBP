const form = document.getElementById("chatForm");
const input = document.getElementById("messageInput");
const button = document.getElementById("sendButton");
const messages = document.getElementById("messages");
const emptyState = document.getElementById("emptyState");
const typingIndicator = document.getElementById("typingIndicator");

let isLoading = false;

function updateControls() {
  button.disabled = isLoading || input.value.trim() === "";
  input.disabled = isLoading;
}

function updateEmptyState() {
  const hasMessages = messages.children.length > 0;
  if (hasMessages) {
    if (emptyState && emptyState.parentNode) {
      emptyState.parentNode.removeChild(emptyState);
    }
  } else {
    // If the emptyState was removed earlier, recreate it so the initial
    // state is available when there are no messages.
    if (!document.getElementById("emptyState")) {
      const el = document.createElement("div");
      el.id = "emptyState";
      el.className = "empty-state";
      el.setAttribute("data-testid", "empty-state");
      el.textContent = "Aucune question pour le moment.";
      messages.insertAdjacentElement("afterend", el);
    }
  }
}

function addMessage(text, role, isError = false) {
  const wrapper = document.createElement("div");
  const messageTestId = isError
    ? "message-error"
    : role === "user"
      ? "message-question"
      : "message-answer";
  const content = document.createElement("span");

  wrapper.className = `message ${role}${isError ? " error" : ""}`;
  wrapper.setAttribute("data-testid", "message");
  wrapper.setAttribute("data-role", role);
  wrapper.setAttribute("data-kind", isError ? "error" : role);
  content.setAttribute("data-testid", messageTestId);
  content.textContent = text;
  wrapper.appendChild(content);
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
      addMessage(data.error || "Une erreur est survenue.", "assistant", true);
    } else {
      addMessage(data.answer, "assistant");
    }
  } catch (error) {
    addMessage(
      "Le service est indisponible. Réessayez plus tard.",
      "assistant",
      true,
    );
  } finally {
    isLoading = false;
    updateControls();
    showTyping(false);
  }
});

input.addEventListener("input", updateControls);
updateControls();
