const SESSION_KEY = "kpb_session";

function showGallery() {
  document.getElementById("login-view").hidden = true;
  document.getElementById("gallery-view").hidden = false;
}

async function login(password) {
  const res = await fetch(`${window.API_BASE_URL}/auth`, {
    method: "POST",
    body: JSON.stringify({ password }),
  });
  if (!res.ok) throw new Error("invalid credentials");
  const { session } = await res.json();
  sessionStorage.setItem(SESSION_KEY, session);
}

async function loadPhotos() {
  const token = sessionStorage.getItem(SESSION_KEY);
  const res = await fetch(`${window.API_BASE_URL}/photos`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (res.status === 401) {
    sessionStorage.removeItem(SESSION_KEY);
    location.reload();
    return;
  }
  const { photos } = await res.json();
  const grid = document.getElementById("photo-grid");
  const emptyState = document.getElementById("empty-state");
  grid.innerHTML = "";
  emptyState.hidden = photos.length > 0;
  for (const photo of photos) {
    const img = document.createElement("img");
    img.src = photo.url;
    img.alt = photo.key;
    grid.appendChild(img);
  }
}

document.getElementById("login-btn").addEventListener("click", async () => {
  const password = document.getElementById("password").value;
  try {
    await login(password);
    showGallery();
    await loadPhotos();
  } catch {
    document.getElementById("login-error").hidden = false;
  }
});

if (sessionStorage.getItem(SESSION_KEY)) {
  showGallery();
  loadPhotos();
}
