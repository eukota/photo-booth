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
    grid.appendChild(buildPhotoTile(photo));
  }
}

function buildPhotoTile(photo) {
  const tile = document.createElement("div");
  tile.className = "photo-tile";

  const img = document.createElement("img");
  img.src = photo.url;
  img.alt = photo.key;
  tile.appendChild(img);

  // Operator convenience: one click to save, right from this screen.
  const downloadLink = document.createElement("a");
  downloadLink.href = photo.url;
  downloadLink.download = photo.key.split("/").pop();
  downloadLink.className = "download-link";
  downloadLink.textContent = "Download";
  tile.appendChild(downloadLink);

  // Patron self-serve: scan with your own phone to get the photo
  // directly - no operator involvement needed. Same presigned URL as
  // the download link and <img> above, just QR-encoded.
  const qrWrapper = document.createElement("div");
  qrWrapper.className = "qr-code";
  const qr = qrcode(0, "M");
  qr.addData(photo.url);
  qr.make();
  qrWrapper.innerHTML = qr.createSvgTag(3, 8);
  tile.appendChild(qrWrapper);

  return tile;
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
