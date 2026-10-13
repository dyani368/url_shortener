const state = { token: sessionStorage.getItem("shortly_token"), username: "", authMode: "login", urls: [] };

const $ = (selector) => document.querySelector(selector);
const welcomeView = $("#welcome-view");
const dashboardView = $("#dashboard-view");
const logoutButton = $("#logout-button");
const authForm = $("#auth-form");
const authMessage = $("#auth-message");
const createMessage = $("#create-message");
const toast = $("#toast");

let toastTimeout;

function showToast(message, isError = false) {
  toast.textContent = message;
  toast.classList.toggle("error", isError);
  toast.classList.add("visible");
  clearTimeout(toastTimeout);
  toastTimeout = setTimeout(() => toast.classList.remove("visible"), 3200);
}

async function api(path, options = {}) {
  const headers = new Headers(options.headers || {});
  if (state.token) headers.set("Authorization", `Bearer ${state.token}`);
  if (options.body && !(options.body instanceof URLSearchParams)) headers.set("Content-Type", "application/json");

  const response = await fetch(path, { ...options, headers });
  if (response.status === 204) return null;

  const contentType = response.headers.get("content-type") || "";
  const body = contentType.includes("application/json") ? await response.json() : await response.text();
  if (!response.ok) {
    const detail = typeof body === "object" ? body.detail : body;
    const message = Array.isArray(detail) ? detail.map((item) => item.msg).join(" ") : detail;
    throw new Error(message || `Request failed (${response.status})`);
  }
  return body;
}

function setAuthMode(mode) {
  state.authMode = mode;
  const isRegister = mode === "register";
  $("#auth-title").textContent = isRegister ? "Make yourself at home" : "Welcome back";
  $("#auth-subtitle").textContent = isRegister ? "Your little link studio is one step away." : "Pick up right where you left off.";
  $("#auth-submit").innerHTML = isRegister ? 'Create account <span aria-hidden="true">→</span>' : 'Log in <span aria-hidden="true">→</span>';
  $("#email-field").classList.toggle("hidden", !isRegister);
  $("#email-field input").required = isRegister;
  $("#auth-form [name=password]").autocomplete = isRegister ? "new-password" : "current-password";
  authMessage.textContent = "";
  authMessage.classList.remove("success");
  document.querySelectorAll("[data-auth-mode]").forEach((tab) => {
    const active = tab.dataset.authMode === mode;
    tab.classList.toggle("active", active);
    tab.setAttribute("aria-selected", String(active));
  });
}

function showSignedOut() {
  state.token = null;
  state.username = "";
  state.urls = [];
  sessionStorage.removeItem("shortly_token");
  welcomeView.classList.remove("hidden");
  dashboardView.classList.add("hidden");
  logoutButton.classList.add("hidden");
}

function showSignedIn(username) {
  state.username = username;
  welcomeView.classList.add("hidden");
  dashboardView.classList.remove("hidden");
  logoutButton.classList.remove("hidden");
  $("#greeting-name").textContent = `${username}.`;
  $("#today-label").textContent = new Intl.DateTimeFormat(undefined, { weekday: "short", month: "short", day: "numeric" }).format(new Date());
  void refreshUrls();
}

function formatDate(value) {
  if (!value) return "Not yet";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Not yet";
  return new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric", year: "numeric" }).format(date);
}

function renderUrls() {
  const list = $("#links-list");
  list.replaceChildren();
  const totalClicks = state.urls.reduce((sum, url) => sum + (url.click_count || 0), 0);
  $("#stat-links").textContent = state.urls.length.toLocaleString();
  $("#stat-clicks").textContent = totalClicks.toLocaleString();
  $("#links-bar").style.width = `${Math.min(100, state.urls.length * 10 + 8)}%`;
  $("#clicks-bar").style.width = `${totalClicks ? Math.min(100, Math.log10(totalClicks + 1) * 28) : 8}%`;

  if (state.urls.length === 0) {
    const empty = document.createElement("div");
    empty.className = "empty-state";
    empty.innerHTML = '<div class="empty-illustration">↗</div><h3>Your first short link is waiting.</h3><p>Paste a link above and we’ll tidy it up for you.</p>';
    list.append(empty);
    return;
  }

  for (const url of state.urls) {
    const row = document.createElement("article");
    row.className = "link-row";

    const main = document.createElement("div");
    main.className = "link-main";
    const mark = document.createElement("span");
    mark.className = "link-mark";
    mark.setAttribute("aria-hidden", "true");
    mark.textContent = "↗";
    const info = document.createElement("div");
    info.className = "link-info";
    const shortLink = document.createElement("a");
    shortLink.className = "short-link";
    shortLink.href = `${window.location.origin}/${encodeURIComponent(url.short_code)}`;
    shortLink.target = "_blank";
    shortLink.rel = "noopener noreferrer";
    shortLink.textContent = shortLink.href.replace(/^https?:\/\//, "");
    shortLink.title = shortLink.href;
    const longLink = document.createElement("span");
    longLink.className = "long-link";
    longLink.textContent = url.long_url;
    longLink.title = `${url.long_url} · expires ${formatDate(url.expiry_date)}`;
    info.append(shortLink, longLink);
    main.append(mark, info);

    const clicks = document.createElement("span");
    clicks.className = "link-clicks";
    clicks.textContent = Number(url.click_count || 0).toLocaleString();
    const created = document.createElement("span");
    created.className = "link-created";
    created.textContent = formatDate(url.created_at);

    const actions = document.createElement("div");
    actions.className = "link-actions";
    const copy = document.createElement("button");
    copy.className = "icon-button";
    copy.type = "button";
    copy.title = "Copy short link";
    copy.setAttribute("aria-label", `Copy link ${url.short_code}`);
    copy.textContent = "▣";
    copy.addEventListener("click", () => copyLink(shortLink.href));
    const analytics = document.createElement("button");
    analytics.className = "icon-button";
    analytics.type = "button";
    analytics.title = "Refresh click analytics";
    analytics.setAttribute("aria-label", `View analytics for ${url.short_code}`);
    analytics.textContent = "◷";
    analytics.addEventListener("click", () => loadAnalytics(url.id));
    const remove = document.createElement("button");
    remove.className = "icon-button delete";
    remove.type = "button";
    remove.title = "Delete link";
    remove.setAttribute("aria-label", `Delete link ${url.short_code}`);
    remove.textContent = "×";
    remove.addEventListener("click", () => deleteUrl(url.id, url.short_code));
    actions.append(copy, analytics, remove);
    row.append(main, clicks, created, actions);
    list.append(row);
  }
}

async function copyLink(value) {
  try {
    await navigator.clipboard.writeText(value);
    showToast("Short link copied. Off it goes!");
  } catch {
    showToast(`Copy this link: ${value}`);
  }
}

async function refreshUrls() {
  const refresh = $("#refresh-button");
  refresh.disabled = true;
  try {
    state.urls = await api("/api/urls");
    renderUrls();
  } catch (error) {
    if (/credentials|unauthorized/i.test(error.message)) showSignedOut();
    else showToast(error.message, true);
  } finally {
    refresh.disabled = false;
  }
}

async function loadAnalytics(urlId) {
  try {
    const result = await api(`/api/analytics/${urlId}`);
    const savedUrl = state.urls.find((url) => url.id === urlId);
    if (savedUrl) {
      savedUrl.click_count = result.click_count;
      savedUrl.last_clicked_at = result.last_clicked_at;
      renderUrls();
    }
    const lastClick = result.last_clicked_at ? formatDate(result.last_clicked_at) : "No clicks yet";
    showToast(`${result.click_count.toLocaleString()} total clicks · last clicked ${lastClick}`);
  } catch (error) {
    showToast(error.message, true);
  }
}

async function deleteUrl(urlId, shortCode) {
  if (!window.confirm(`Delete the short link ${shortCode}?`)) return;
  try {
    await api(`/api/urls/${urlId}`, { method: "DELETE" });
    showToast("Link removed from your collection.");
    await refreshUrls();
  } catch (error) {
    showToast(error.message, true);
  }
}

document.querySelectorAll("[data-auth-mode]").forEach((tab) => {
  tab.addEventListener("click", () => setAuthMode(tab.dataset.authMode));
});

authForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const submit = $("#auth-submit");
  const form = new FormData(authForm);
  const username = String(form.get("username")).trim();
  const password = String(form.get("password"));
  submit.disabled = true;
  authMessage.textContent = "";
  authMessage.classList.remove("success");

  try {
    if (state.authMode === "register") {
      await api("/api/users/register", {
        method: "POST",
        body: JSON.stringify({ username, email: String(form.get("email")).trim(), password }),
      });
      setAuthMode("login");
      $("#auth-form [name=username]").value = username;
      authMessage.textContent = "Account created. Log in to open your link studio.";
      authMessage.classList.add("success");
    } else {
      const credentials = new URLSearchParams({ username, password });
      const result = await api("/api/users/token", { method: "POST", body: credentials });
      state.token = result.access_token;
      sessionStorage.setItem("shortly_token", state.token);
      showSignedIn(username);
      authForm.reset();
    }
  } catch (error) {
    authMessage.textContent = error.message;
  } finally {
    submit.disabled = false;
  }
});

$("#create-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const submit = $("#create-submit");
  const longUrl = new FormData(form).get("long_url");
  submit.disabled = true;
  createMessage.textContent = "";

  try {
    const created = await api("/api/urls", { method: "POST", body: JSON.stringify({ long_url: longUrl }) });
    form.reset();
    await refreshUrls();
    showToast(`Your short link is ready: ${window.location.origin}/${created.short_code}`);
  } catch (error) {
    createMessage.textContent = error.message;
  } finally {
    submit.disabled = false;
  }
});

$("#refresh-button").addEventListener("click", () => void refreshUrls());
logoutButton.addEventListener("click", () => {
  showSignedOut();
  setAuthMode("login");
  showToast("You’re logged out. See you soon!");
});

async function restoreSession() {
  if (!state.token) return;
  try {
    const user = await api("/api/users/me");
    showSignedIn(user.username);
  } catch {
    showSignedOut();
  }
}

async function checkService() {
  const status = $("#service-status");
  try {
    const response = await fetch("/health/ready");
    const body = await response.json();
    status.querySelector("span:last-child").textContent = response.ok && body.status === "ok" ? "API ready" : "API needs attention";
    status.classList.toggle("service-error", !response.ok);
  } catch {
    status.querySelector("span:last-child").textContent = "API unreachable";
    status.classList.add("service-error");
  }
}

void checkService();
void restoreSession();
