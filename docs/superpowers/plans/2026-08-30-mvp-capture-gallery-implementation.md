# Kinetic Photo Booth MVP — Capture → S3 → Gallery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the phase-1 MVP pipeline: Pi Zero W captures a photo on
button press and uploads it to S3; an operator logs into a serverless
gallery site and sees pre-signed links to every photo. No payment, no
watermark, no accounts.

**Architecture:** Serverless AWS (S3 + CloudFront + API Gateway + Lambda),
deployed via a single CloudFormation template. A LocalStack-based local
stack lets everything except real Pi hardware be developed and tested
without an AWS account. GitHub Actions runs tests on every push and deploys
the CFT to AWS on merge to `main`.

**Tech Stack:** Python 3.12 (Lambdas, Pi capture script, dev tooling),
vanilla HTML/JS (gallery frontend, no framework — keeps CloudFront/S3
static hosting trivial), AWS CloudFormation, LocalStack + `awslocal` for
local dev, GitHub Actions for CI/CD, `pytest` + `moto` for testing.

## Global Constraints

- S3 object keys always follow `events/{event-id}/{device-id}/{uuid}.jpg`
  (from the design spec) — no task may deviate from this, even though
  phase 1 has one fixed `event-id`.
- The Pi/uploader IAM identity may only ever be granted `s3:PutObject` on
  the photos bucket — never `List`/`Get`/`Delete`.
- Photos bucket is private with a 30-day expiration lifecycle rule; no
  public bucket policy is permitted at any point.
- Pre-signed GET URLs expire in 30 minutes.
- All AWS resources are defined in one CloudFormation template
  (`infra/template.yaml`) — no manually-clicked console resources except
  the one-time IAM access key described in the handoff checklist.

---

## File Structure

```
photo-booth/
├── Makefile
├── infra/
│   └── template.yaml              # single CloudFormation template
├── src/
│   ├── lambdas/
│   │   ├── auth/
│   │   │   ├── handler.py
│   │   │   └── requirements.txt
│   │   └── list_photos/
│   │       ├── handler.py
│   │       └── requirements.txt
│   └── common/
│       └── session.py             # shared JWT sign/verify used by both Lambdas
├── frontend/
│   ├── index.html
│   ├── app.js
│   └── style.css
├── scripts/
│   └── upload_test_photo.py       # dev-tooling uploader (mimics the Pi)
├── pi/
│   └── capture.py                 # Pi Zero W button->webcam->S3 script
├── tests/
│   ├── unit/
│   │   ├── test_session.py
│   │   ├── test_auth_handler.py
│   │   ├── test_list_photos_handler.py
│   │   └── test_capture.py
│   └── integration/
│       └── test_gallery_flow.py   # runs against LocalStack
├── docker-compose.localstack.yml
├── requirements-dev.txt
├── .github/workflows/
│   ├── ci.yml
│   └── deploy.yml
└── docs/superpowers/
    ├── specs/2026-08-30-mvp-capture-gallery-design.md
    └── plans/2026-08-30-mvp-capture-gallery-implementation.md
```

---

### Task 1: Repo scaffolding and Makefile skeleton

**Files:**
- Create: `Makefile`
- Create: `.gitignore`
- Create: `requirements-dev.txt`
- Create: `README.md`

**Interfaces:**
- Produces: `make` targets (`test`, `lint`, `local-up`, `local-down`,
  `local-deploy`, `seed`, `integration-test`) that later tasks fill in —
  defined now as stubs so every later task has a stable place to hook into.

- [ ] **Step 1: Create `.gitignore`**

```
__pycache__/
*.pyc
.venv/
.env
.localstack/
node_modules/
```

- [ ] **Step 2: Create `requirements-dev.txt`**

```
pytest==8.3.3
moto[s3]==5.0.13
boto3==1.35.24
PyJWT==2.9.0
requests==2.32.3
black==24.8.0
flake8==7.1.1
```

- [ ] **Step 3: Create `Makefile` with stub targets**

```makefile
.PHONY: test lint local-up local-down local-deploy seed integration-test

test:
	pytest tests/unit -v

lint:
	black --check src pi scripts tests
	flake8 src pi scripts tests

local-up:
	docker compose -f docker-compose.localstack.yml up -d

local-down:
	docker compose -f docker-compose.localstack.yml down

local-deploy:
	AWS_ENDPOINT_URL=http://localhost:4566 \
	aws cloudformation deploy \
	  --template-file infra/template.yaml \
	  --stack-name photo-booth-local \
	  --capabilities CAPABILITY_NAMED_IAM \
	  --parameter-overrides GalleryPassword=localtest \
	  --endpoint-url http://localhost:4566

seed:
	python scripts/upload_test_photo.py --count 3 --endpoint-url http://localhost:4566

integration-test:
	pytest tests/integration -v
```

- [ ] **Step 4: Create minimal `README.md`**

```markdown
# Kinetic Photo Booth

Pi Zero W button/webcam -> S3 -> serverless gallery. See
`docs/superpowers/specs/2026-08-30-mvp-capture-gallery-design.md` for the
design and `docs/superpowers/plans/2026-08-30-mvp-capture-gallery-implementation.md`
for the build plan.

## Quickstart (local, no AWS account needed)

    make local-up
    make local-deploy
    make seed
    make integration-test
```

- [ ] **Step 5: Commit**

```bash
git add Makefile .gitignore requirements-dev.txt README.md
git commit -m "chore: scaffold repo with Makefile and dev requirements"
```

---

### Task 2: CloudFormation — S3 photos bucket

**Files:**
- Create: `infra/template.yaml` (started here, extended by later tasks)

**Interfaces:**
- Produces: CFN resource `PhotosBucket` (logical ID) and output
  `PhotosBucketName` — every later infra task references this exact name.

- [ ] **Step 1: Write `infra/template.yaml` with the photos bucket**

```yaml
AWSTemplateFormatVersion: "2010-09-09"
Transform: AWS::Serverless-2016-10-31
Description: Kinetic Photo Booth MVP - capture -> S3 -> gallery

Parameters:
  GalleryPassword:
    Type: String
    NoEcho: true
    Description: Shared operator password for the gallery login

Resources:
  PhotosBucket:
    Type: AWS::S3::Bucket
    Properties:
      BucketName: !Sub "kinetic-photo-booth-photos-${AWS::AccountId}"
      PublicAccessBlockConfiguration:
        BlockPublicAcls: true
        BlockPublicPolicy: true
        IgnorePublicAcls: true
        RestrictPublicBuckets: true
      LifecycleConfiguration:
        Rules:
          - Id: expire-after-30-days
            Status: Enabled
            ExpirationInDays: 30

Outputs:
  PhotosBucketName:
    Value: !Ref PhotosBucket
    Export:
      Name: kinetic-photo-booth-photos-bucket-name
```

- [ ] **Step 2: Validate the template syntactically**

Run: `aws cloudformation validate-template --template-body file://infra/template.yaml`
Expected: no errors (this only checks YAML/CFN syntax, not deployability —
real deployment is exercised against LocalStack in Task 10).

- [ ] **Step 3: Commit**

```bash
git add infra/template.yaml
git commit -m "infra: add private photos S3 bucket with 30-day lifecycle rule"
```

---

### Task 3: Shared session module (JWT sign/verify)

**Files:**
- Create: `src/common/session.py`
- Test: `tests/unit/test_session.py`

**Interfaces:**
- Produces: `create_session(secret: str) -> str`,
  `verify_session(token: str, secret: str) -> bool` — used by both the
  auth Lambda (Task 4) and the list Lambda (Task 5).

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_session.py
import time
from src.common.session import create_session, verify_session

def test_valid_session_verifies():
    token = create_session(secret="test-secret")
    assert verify_session(token, secret="test-secret") is True

def test_session_with_wrong_secret_fails():
    token = create_session(secret="test-secret")
    assert verify_session(token, secret="wrong-secret") is False

def test_expired_session_fails(monkeypatch):
    token = create_session(secret="test-secret", ttl_seconds=1)
    time.sleep(2)
    assert verify_session(token, secret="test-secret") is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_session.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.common.session'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/common/session.py
import time
import jwt

DEFAULT_TTL_SECONDS = 60 * 60  # 1 hour

def create_session(secret: str, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> str:
    payload = {"exp": int(time.time()) + ttl_seconds, "role": "operator"}
    return jwt.encode(payload, secret, algorithm="HS256")

def verify_session(token: str, secret: str) -> bool:
    try:
        jwt.decode(token, secret, algorithms=["HS256"])
        return True
    except jwt.PyJWTError:
        return False
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_session.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add src/common/session.py tests/unit/test_session.py
git commit -m "feat: add shared JWT session create/verify helpers"
```

---

### Task 4: Auth Lambda

**Files:**
- Create: `src/lambdas/auth/handler.py`
- Create: `src/lambdas/auth/requirements.txt`
- Test: `tests/unit/test_auth_handler.py`

**Interfaces:**
- Consumes: `create_session(secret, ttl_seconds=...)` from
  `src/common/session.py` (Task 3).
- Produces: `lambda_handler(event, context) -> dict` with API Gateway HTTP
  API proxy response shape (`statusCode`, `body`); reads
  `GALLERY_PASSWORD` and `SESSION_SECRET` from environment variables —
  these exact env var names are wired into `infra/template.yaml` in
  Task 6.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_auth_handler.py
import json
import os
from src.lambdas.auth.handler import lambda_handler

def test_correct_password_returns_session(monkeypatch):
    monkeypatch.setenv("GALLERY_PASSWORD", "correct-horse")
    monkeypatch.setenv("SESSION_SECRET", "test-secret")
    event = {"body": json.dumps({"password": "correct-horse"})}
    result = lambda_handler(event, None)
    assert result["statusCode"] == 200
    assert "session" in json.loads(result["body"])

def test_wrong_password_returns_401(monkeypatch):
    monkeypatch.setenv("GALLERY_PASSWORD", "correct-horse")
    monkeypatch.setenv("SESSION_SECRET", "test-secret")
    event = {"body": json.dumps({"password": "wrong"})}
    result = lambda_handler(event, None)
    assert result["statusCode"] == 401
    assert "session" not in result["body"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_auth_handler.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.lambdas.auth.handler'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/lambdas/auth/handler.py
import json
import os
from src.common.session import create_session

def lambda_handler(event, context):
    body = json.loads(event.get("body") or "{}")
    submitted = body.get("password", "")
    expected = os.environ["GALLERY_PASSWORD"]

    if submitted != expected:
        return {
            "statusCode": 401,
            "body": json.dumps({"error": "invalid credentials"}),
        }

    token = create_session(secret=os.environ["SESSION_SECRET"])
    return {
        "statusCode": 200,
        "body": json.dumps({"session": token}),
    }
```

```
# src/lambdas/auth/requirements.txt
PyJWT==2.9.0
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_auth_handler.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add src/lambdas/auth tests/unit/test_auth_handler.py
git commit -m "feat: add auth Lambda handler with password check and JWT session"
```

---

### Task 5: List-photos Lambda

**Files:**
- Create: `src/lambdas/list_photos/handler.py`
- Create: `src/lambdas/list_photos/requirements.txt`
- Test: `tests/unit/test_list_photos_handler.py`

**Interfaces:**
- Consumes: `verify_session(token, secret)` from `src/common/session.py`
  (Task 3); reads `PHOTOS_BUCKET_NAME` and `SESSION_SECRET` env vars.
- Produces: `lambda_handler(event, context) -> dict` returning
  `{"statusCode": 200, "body": json.dumps({"photos": [{"key": str, "url": str}]})}`
  — this exact response shape (`photos` list of `{key, url}` objects) is
  what the frontend (Task 8) renders.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_list_photos_handler.py
import json
import boto3
import pytest
from moto import mock_aws
from src.common.session import create_session

@pytest.fixture
def bucket_with_photos(monkeypatch):
    monkeypatch.setenv("PHOTOS_BUCKET_NAME", "test-bucket")
    monkeypatch.setenv("SESSION_SECRET", "test-secret")
    with mock_aws():
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket="test-bucket")
        s3.put_object(Bucket="test-bucket", Key="events/e1/pi-1/abc.jpg", Body=b"fake")
        s3.put_object(Bucket="test-bucket", Key="events/e1/pi-2/def.jpg", Body=b"fake")
        yield

def test_valid_session_lists_photos(bucket_with_photos):
    from src.lambdas.list_photos.handler import lambda_handler
    token = create_session(secret="test-secret")
    event = {"headers": {"authorization": f"Bearer {token}"}}
    result = lambda_handler(event, None)
    assert result["statusCode"] == 200
    photos = json.loads(result["body"])["photos"]
    assert len(photos) == 2
    assert all("url" in p and "key" in p for p in photos)

def test_missing_session_returns_401(bucket_with_photos):
    from src.lambdas.list_photos.handler import lambda_handler
    event = {"headers": {}}
    result = lambda_handler(event, None)
    assert result["statusCode"] == 401
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_list_photos_handler.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.lambdas.list_photos.handler'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/lambdas/list_photos/handler.py
import json
import os
import boto3
from src.common.session import verify_session

PRESIGN_TTL_SECONDS = 30 * 60


def lambda_handler(event, context):
    auth_header = (event.get("headers") or {}).get("authorization", "")
    token = auth_header.removeprefix("Bearer ").strip()

    if not token or not verify_session(token, secret=os.environ["SESSION_SECRET"]):
        return {"statusCode": 401, "body": json.dumps({"error": "unauthorized"})}

    bucket = os.environ["PHOTOS_BUCKET_NAME"]
    s3 = boto3.client("s3")
    response = s3.list_objects_v2(Bucket=bucket)

    photos = [
        {
            "key": obj["Key"],
            "url": s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": bucket, "Key": obj["Key"]},
                ExpiresIn=PRESIGN_TTL_SECONDS,
            ),
        }
        for obj in response.get("Contents", [])
    ]

    return {"statusCode": 200, "body": json.dumps({"photos": photos})}
```

```
# src/lambdas/list_photos/requirements.txt
PyJWT==2.9.0
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_list_photos_handler.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add src/lambdas/list_photos tests/unit/test_list_photos_handler.py
git commit -m "feat: add list-photos Lambda with session check and presigned URLs"
```

---

### Task 6: CloudFormation — Lambdas, IAM, API Gateway, Secrets Manager

**Files:**
- Modify: `infra/template.yaml`

**Interfaces:**
- Consumes: `PhotosBucket` resource from Task 2; `src/lambdas/auth/handler.py`
  and `src/lambdas/list_photos/handler.py` from Tasks 4–5 (packaged as
  `CodeUri`).
- Produces: CFN outputs `ApiBaseUrl` (used by the frontend in Task 8) and
  `PhotoUploaderAccessKeyOutput` is deliberately NOT produced — see Step 3
  note on why the uploader IAM user's access key is created manually.

- [ ] **Step 1: Add the SAM transform's implicit requirements and the
  session-secret resource**

Append to `infra/template.yaml` under `Resources:`:

```yaml
  SessionSecret:
    Type: AWS::SecretsManager::Secret
    Properties:
      Name: kinetic-photo-booth-session-secret
      GenerateSecretString:
        SecretStringTemplate: '{}'
        GenerateStringKey: "secret"
        PasswordLength: 32
        ExcludePunctuation: true
```

- [ ] **Step 2: Add the auth and list-photos Lambda functions**

```yaml
  AuthFunction:
    Type: AWS::Serverless::Function
    Properties:
      FunctionName: kinetic-photo-booth-auth
      Runtime: python3.12
      Handler: handler.lambda_handler
      CodeUri: ../src/lambdas/auth/
      Timeout: 10
      Environment:
        Variables:
          GALLERY_PASSWORD: !Ref GalleryPassword
          SESSION_SECRET: !Sub "{{resolve:secretsmanager:${SessionSecret}:SecretString:secret}}"
      Events:
        AuthApi:
          Type: HttpApi
          Properties:
            ApiId: !Ref GalleryApi
            Path: /auth
            Method: POST

  ListPhotosFunction:
    Type: AWS::Serverless::Function
    Properties:
      FunctionName: kinetic-photo-booth-list-photos
      Runtime: python3.12
      Handler: handler.lambda_handler
      CodeUri: ../src/lambdas/list_photos/
      Timeout: 10
      Policies:
        - S3ReadPolicy:
            BucketName: !Ref PhotosBucket
      Environment:
        Variables:
          PHOTOS_BUCKET_NAME: !Ref PhotosBucket
          SESSION_SECRET: !Sub "{{resolve:secretsmanager:${SessionSecret}:SecretString:secret}}"
      Events:
        ListApi:
          Type: HttpApi
          Properties:
            ApiId: !Ref GalleryApi
            Path: /photos
            Method: GET
```

- [ ] **Step 3: Add the HTTP API and the Pi/uploader IAM user**

```yaml
  GalleryApi:
    Type: AWS::Serverless::HttpApi
    Properties:
      StageName: prod
      # Throttle the whole API (the /auth route is the sensitive one - a
      # single shared password - so keep this low; per the design's
      # error-handling section, brute-force attempts must be blunted).
      DefaultRouteSettings:
        ThrottlingBurstLimit: 5
        ThrottlingRateLimit: 1

  PhotoUploaderUser:
    Type: AWS::IAM::User
    Properties:
      UserName: kinetic-photo-booth-uploader
      Policies:
        - PolicyName: PutObjectOnly
          PolicyDocument:
            Version: "2012-10-17"
            Statement:
              - Effect: Allow
                Action: s3:PutObject
                Resource: !Sub "${PhotosBucket.Arn}/*"
```

Note: `PhotoUploaderUser` intentionally has no `AWS::IAM::AccessKey`
resource. CloudFormation would store the secret access key in the stack's
state/outputs, which is a credential-hygiene risk. The access key is
created once, manually, via `aws iam create-access-key` — see the
"AWS account handoff checklist" at the end of this plan.

- [ ] **Step 4: Add the `ApiBaseUrl` output**

```yaml
  ApiBaseUrl:
    Value: !Sub "https://${GalleryApi}.execute-api.${AWS::Region}.amazonaws.com"
```

(Add this under the existing `Outputs:` key alongside `PhotosBucketName`.)

- [ ] **Step 5: Validate template**

Run: `sam validate --template infra/template.yaml`
Expected: no errors

- [ ] **Step 6: Commit**

```bash
git add infra/template.yaml
git commit -m "infra: add auth/list Lambdas, HTTP API, session secret, uploader IAM user"
```

---

### Task 7: CloudFormation — frontend hosting (S3 + CloudFront)

**Files:**
- Modify: `infra/template.yaml`

**Interfaces:**
- Produces: output `GalleryUrl` — the CloudFront domain the operator opens
  in a browser.

- [ ] **Step 1: Add the frontend bucket and CloudFront distribution**

```yaml
  FrontendBucket:
    Type: AWS::S3::Bucket
    Properties:
      BucketName: !Sub "kinetic-photo-booth-frontend-${AWS::AccountId}"
      PublicAccessBlockConfiguration:
        BlockPublicAcls: true
        BlockPublicPolicy: true
        IgnorePublicAcls: true
        RestrictPublicBuckets: true

  FrontendOAC:
    Type: AWS::CloudFront::OriginAccessControl
    Properties:
      OriginAccessControlConfig:
        Name: kinetic-photo-booth-frontend-oac
        OriginAccessControlOriginType: s3
        SigningBehavior: always
        SigningProtocol: sigv4

  FrontendDistribution:
    Type: AWS::CloudFront::Distribution
    Properties:
      DistributionConfig:
        Enabled: true
        DefaultRootObject: index.html
        Origins:
          - Id: frontend-origin
            DomainName: !GetAtt FrontendBucket.RegionalDomainName
            S3OriginConfig: {}
            OriginAccessControlId: !Ref FrontendOAC
        DefaultCacheBehavior:
          TargetOriginId: frontend-origin
          ViewerProtocolPolicy: redirect-to-https
          CachePolicyId: 658327ea-f89d-4fab-a63d-7e88639e58f6 # CachingOptimized

  FrontendBucketPolicy:
    Type: AWS::S3::BucketPolicy
    Properties:
      Bucket: !Ref FrontendBucket
      PolicyDocument:
        Statement:
          - Effect: Allow
            Principal:
              Service: cloudfront.amazonaws.com
            Action: s3:GetObject
            Resource: !Sub "${FrontendBucket.Arn}/*"
            Condition:
              StringEquals:
                AWS:SourceArn: !Sub "arn:aws:cloudfront::${AWS::AccountId}:distribution/${FrontendDistribution}"
```

- [ ] **Step 2: Add the `GalleryUrl` output**

```yaml
  GalleryUrl:
    Value: !Sub "https://${FrontendDistribution.DomainName}"
```

- [ ] **Step 3: Validate template**

Run: `sam validate --template infra/template.yaml`
Expected: no errors

- [ ] **Step 4: Commit**

```bash
git add infra/template.yaml
git commit -m "infra: add CloudFront-fronted S3 bucket for gallery frontend hosting"
```

---

### Task 8: Gallery frontend (login + photo grid)

**Files:**
- Create: `frontend/index.html`
- Create: `frontend/app.js`
- Create: `frontend/style.css`

**Interfaces:**
- Consumes: `POST {API_BASE_URL}/auth` returning `{"session": str}` (Task 4)
  and `GET {API_BASE_URL}/photos` with `Authorization: Bearer <token>`
  returning `{"photos": [{"key": str, "url": str}]}` (Task 5).
- `API_BASE_URL` is injected as a global `window.API_BASE_URL` set by a
  small inline `<script>` in `index.html` — deploy step (Task 9's
  `local-deploy`, and the real deploy workflow in Task 14) replaces this
  placeholder with the actual `ApiBaseUrl` stack output.

- [ ] **Step 1: Write `frontend/index.html`**

```html
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Kinetic Photo Booth Gallery</title>
  <link rel="stylesheet" href="style.css">
  <script>window.API_BASE_URL = "__API_BASE_URL__";</script>
</head>
<body>
  <div id="login-view">
    <input id="password" type="password" placeholder="Operator password">
    <button id="login-btn">Log in</button>
    <p id="login-error" class="error" hidden>Wrong password.</p>
  </div>
  <div id="gallery-view" hidden>
    <div id="photo-grid"></div>
    <p id="empty-state" hidden>No photos yet.</p>
  </div>
  <script src="app.js"></script>
</body>
</html>
```

- [ ] **Step 2: Write `frontend/app.js`**

```javascript
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
```

- [ ] **Step 3: Write `frontend/style.css`**

```css
body { font-family: sans-serif; background: #111; color: #eee; }
#photo-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 8px; }
#photo-grid img { width: 100%; border-radius: 4px; }
.error { color: #f66; }
```

- [ ] **Step 4: Manual verification (no automated test — static assets)**

Open `frontend/index.html` directly in a browser with
`window.API_BASE_URL` hand-edited to a running local API (from Task 10);
confirm the login form appears and, on submit, either shows the error text
or the (initially empty) gallery grid.

- [ ] **Step 5: Commit**

```bash
git add frontend/
git commit -m "feat: add gallery frontend (login + photo grid)"
```

---

### Task 9: Dev tooling — test photo uploader

**Files:**
- Create: `scripts/upload_test_photo.py`
- Test: covered by `tests/integration/test_gallery_flow.py` in Task 11
  (this script has no unit test of its own — it's a thin CLI wrapper
  around `boto3`, verified end-to-end instead)

**Interfaces:**
- Produces: a CLI, `python scripts/upload_test_photo.py --count N
  [--endpoint-url URL] [--event-id ID] [--device-id ID]`, uploading N
  1x1-pixel JPEG fixtures using the same key structure the Pi uses
  (`events/{event-id}/{device-id}/{uuid}.jpg`).

- [ ] **Step 1: Write `scripts/upload_test_photo.py`**

```python
#!/usr/bin/env python3
import argparse
import io
import uuid
import boto3

# Smallest valid 1x1 black JPEG, used as a stand-in for a real capture.
FIXTURE_JPEG_BYTES = bytes.fromhex(
    "ffd8ffe000104a46494600010100000100010000ffdb004300010101010101"
    "01010101010101010101010101010101010101010101010101010101010101"
    "01010101010101010101010101010101010101010101010101010101010101"
    "0101ffc9000b080001000101011100ffcc000600101005ffda0008010100003f00d2cf20ffd9"
)


def upload(bucket: str, event_id: str, device_id: str, count: int, endpoint_url: str | None):
    s3 = boto3.client("s3", endpoint_url=endpoint_url)
    for _ in range(count):
        key = f"events/{event_id}/{device_id}/{uuid.uuid4()}.jpg"
        s3.upload_fileobj(io.BytesIO(FIXTURE_JPEG_BYTES), bucket, key)
        print(f"uploaded {key}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--bucket", default="kinetic-photo-booth-photos-000000000000")
    parser.add_argument("--event-id", default="test-event")
    parser.add_argument("--device-id", default="test-device")
    parser.add_argument("--count", type=int, default=1)
    parser.add_argument("--endpoint-url", default=None)
    args = parser.parse_args()
    upload(args.bucket, args.event_id, args.device_id, args.count, args.endpoint_url)
```

- [ ] **Step 2: Manual smoke check (no AWS/LocalStack needed yet)**

Run: `python scripts/upload_test_photo.py --help`
Expected: argparse help text prints, no errors.

- [ ] **Step 3: Commit**

```bash
git add scripts/upload_test_photo.py
git commit -m "feat: add dev-tooling script to upload fixture photos"
```

---

### Task 10: LocalStack local dev/test stack

**Files:**
- Create: `docker-compose.localstack.yml`
- Modify: `Makefile` (`local-deploy` target needs the real bucket-name
  parameter override, and a step to sync the frontend)

**Interfaces:**
- Consumes: `infra/template.yaml` (Tasks 2, 6, 7).
- Produces: a running LocalStack instance on `localhost:4566` with the
  full stack deployed, addressable by every later local test.

- [ ] **Step 1: Write `docker-compose.localstack.yml`**

```yaml
services:
  localstack:
    image: localstack/localstack:3.7
    ports:
      - "4566:4566"
    environment:
      - SERVICES=s3,lambda,apigateway,secretsmanager,cloudformation,iam,sts,cloudfront
      - DEBUG=0
    volumes:
      - "./.localstack:/var/lib/localstack"
```

- [ ] **Step 2: Update the `local-deploy` Makefile target to pass a fixed
  account ID (LocalStack's default) and sync the frontend afterward**

```makefile
local-deploy:
	AWS_ENDPOINT_URL=http://localhost:4566 \
	sam deploy \
	  --template-file infra/template.yaml \
	  --stack-name photo-booth-local \
	  --capabilities CAPABILITY_NAMED_IAM \
	  --parameter-overrides GalleryPassword=localtest \
	  --resolve-s3 \
	  --no-confirm-changeset \
	  --region us-east-1
	aws --endpoint-url=http://localhost:4566 s3 sync frontend/ \
	  s3://kinetic-photo-booth-frontend-000000000000/
```

- [ ] **Step 3: Bring the stack up and deploy**

Run: `make local-up && sleep 5 && make local-deploy`
Expected: `sam deploy` reports `Successfully created/updated stack -
photo-booth-local`

- [ ] **Step 4: Commit**

```bash
git add docker-compose.localstack.yml Makefile
git commit -m "chore: add LocalStack compose file and local-deploy target"
```

---

### Task 11: Integration test against LocalStack

**Files:**
- Create: `tests/integration/test_gallery_flow.py`

**Interfaces:**
- Consumes: the deployed LocalStack stack from Task 10 (the auth and
  `/photos` HTTP endpoints, and `scripts/upload_test_photo.py` from
  Task 9).

- [ ] **Step 1: Write the test**

```python
# tests/integration/test_gallery_flow.py
import os
import subprocess
import sys
import requests
import pytest

LOCALSTACK_ENDPOINT = "http://localhost:4566"
API_BASE_URL = os.environ.get("LOCAL_API_BASE_URL")  # set by CI/dev after deploy


@pytest.mark.skipif(not API_BASE_URL, reason="LOCAL_API_BASE_URL not set; run `make local-deploy` first")
def test_uploaded_photos_appear_in_gallery():
    subprocess.run(
        [sys.executable, "scripts/upload_test_photo.py",
         "--count", "2", "--endpoint-url", LOCALSTACK_ENDPOINT],
        check=True,
    )

    auth_res = requests.post(f"{API_BASE_URL}/auth", json={"password": "localtest"})
    assert auth_res.status_code == 200
    token = auth_res.json()["session"]

    photos_res = requests.get(
        f"{API_BASE_URL}/photos", headers={"Authorization": f"Bearer {token}"}
    )
    assert photos_res.status_code == 200
    photos = photos_res.json()["photos"]
    assert len(photos) >= 2
    for photo in photos:
        fetched = requests.get(photo["url"])
        assert fetched.status_code == 200
```

- [ ] **Step 2: Run it against the LocalStack stack from Task 10**

Run:
```bash
export LOCAL_API_BASE_URL=$(aws --endpoint-url=http://localhost:4566 \
  cloudformation describe-stacks --stack-name photo-booth-local \
  --query "Stacks[0].Outputs[?OutputKey=='ApiBaseUrl'].OutputValue" --output text)
pytest tests/integration/test_gallery_flow.py -v
```
Expected: 1 passed

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_gallery_flow.py
git commit -m "test: add end-to-end LocalStack integration test for gallery flow"
```

---

### Task 12: Pi Zero W capture script

**Files:**
- Create: `pi/capture.py`
- Test: `tests/unit/test_capture.py`

**Interfaces:**
- Produces: `capture_and_upload(bucket: str, event_id: str, device_id: str,
  capture_fn=default_capture, s3_client=None, max_retries=3) -> str`
  (returns the uploaded S3 key). `capture_fn` and `s3_client` are
  injectable so this is unit-testable without real hardware; on the
  physical Pi, `default_capture` shells out to `fswebcam`.
- **Not hardware-verified in this plan** — GPIO wiring and the real
  `fswebcam` call can only be confirmed once the Pi + camera + button are
  assembled. This task delivers code whose upload/retry/queue logic is
  fully tested via injected fakes; hardware verification is a follow-up
  once the physical unit exists (tracked in the `.context` project notes,
  not blocking this plan).

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_capture.py
import boto3
import pytest
from moto import mock_aws
from pi.capture import capture_and_upload

def fake_capture_ok():
    return b"fake-jpeg-bytes"

def fake_capture_fails():
    raise RuntimeError("webcam not found")

@mock_aws
def test_successful_capture_uploads_with_correct_key_structure():
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket="test-bucket")

    key = capture_and_upload(
        bucket="test-bucket", event_id="e1", device_id="pi-7",
        capture_fn=fake_capture_ok, s3_client=s3,
    )

    assert key.startswith("events/e1/pi-7/")
    assert key.endswith(".jpg")
    obj = s3.get_object(Bucket="test-bucket", Key=key)
    assert obj["Body"].read() == b"fake-jpeg-bytes"

@mock_aws
def test_capture_failure_raises_after_retries():
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket="test-bucket")

    with pytest.raises(RuntimeError, match="webcam not found"):
        capture_and_upload(
            bucket="test-bucket", event_id="e1", device_id="pi-7",
            capture_fn=fake_capture_fails, s3_client=s3, max_retries=2,
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_capture.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'pi.capture'`

- [ ] **Step 3: Write minimal implementation**

```python
# pi/capture.py
import io
import subprocess
import time
import uuid


def default_capture() -> bytes:
    """Grab one still frame from the USB webcam via fswebcam."""
    result = subprocess.run(
        ["fswebcam", "--no-banner", "-r", "1280x720", "-"],
        capture_output=True, check=True,
    )
    return result.stdout


def capture_and_upload(bucket: str, event_id: str, device_id: str,
                        capture_fn=default_capture, s3_client=None,
                        max_retries: int = 3) -> str:
    last_error = None
    for attempt in range(max_retries):
        try:
            image_bytes = capture_fn()
            key = f"events/{event_id}/{device_id}/{uuid.uuid4()}.jpg"
            s3_client.upload_fileobj(io.BytesIO(image_bytes), bucket, key)
            return key
        except Exception as error:  # noqa: BLE001 - retry any capture/upload failure
            last_error = error
            time.sleep(min(2 ** attempt, 10))
    raise last_error
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_capture.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add pi/capture.py tests/unit/test_capture.py
git commit -m "feat: add Pi capture-and-upload logic with retry (hardware untested)"
```

---

### Task 13: GitHub Actions CI (test on every push)

**Files:**
- Create: `.github/workflows/ci.yml`

**Interfaces:**
- Consumes: `Makefile` targets `test` and `lint` (Task 1),
  `requirements-dev.txt` (Task 1).

- [ ] **Step 1: Write `.github/workflows/ci.yml`**

```yaml
name: CI

on:
  push:
    branches: ["**"]
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -r requirements-dev.txt
      - run: make lint
      - run: make test
```

- [ ] **Step 2: Verify locally before pushing**

Run: `pip install -r requirements-dev.txt && make lint && make test`
Expected: lint passes (or is fixed), all unit tests pass

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: run lint and unit tests on every push"
```

---

### Task 14: GitHub Actions deploy (CFT to real AWS on merge to main)

**Files:**
- Create: `.github/workflows/deploy.yml`

**Interfaces:**
- Consumes: `infra/template.yaml` (Tasks 2, 6, 7), `frontend/` (Task 8);
  requires repository secrets `AWS_ACCOUNT_ID` and an OIDC-assumable
  role ARN `AWS_DEPLOY_ROLE_ARN` (see AWS account handoff checklist
  below — no long-lived access keys are stored in GitHub).

- [ ] **Step 1: Write `.github/workflows/deploy.yml`**

```yaml
name: Deploy

on:
  push:
    branches: [main]

permissions:
  id-token: write
  contents: read

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: production
    steps:
      - uses: actions/checkout@v4

      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_DEPLOY_ROLE_ARN }}
          aws-region: us-east-1

      - uses: aws-actions/setup-sam@v2

      - name: Deploy CloudFormation stack
        run: |
          sam deploy \
            --template-file infra/template.yaml \
            --stack-name photo-booth-prod \
            --capabilities CAPABILITY_NAMED_IAM \
            --parameter-overrides GalleryPassword=${{ secrets.GALLERY_PASSWORD }} \
            --resolve-s3 \
            --no-confirm-changeset \
            --no-fail-on-empty-changeset \
            --region us-east-1

      - name: Get API base URL and sync frontend
        run: |
          API_URL=$(aws cloudformation describe-stacks \
            --stack-name photo-booth-prod \
            --query "Stacks[0].Outputs[?OutputKey=='ApiBaseUrl'].OutputValue" \
            --output text)
          sed "s|__API_BASE_URL__|$API_URL|" frontend/index.html > /tmp/index.html
          cp /tmp/index.html frontend/index.html
          aws s3 sync frontend/ s3://kinetic-photo-booth-frontend-${{ secrets.AWS_ACCOUNT_ID }}/
```

- [ ] **Step 2: No automated test for this workflow** — it can only be
  exercised once AWS account access is granted (see handoff checklist).
  Once secrets are set, verify by merging to `main` and checking the
  Actions run + `aws cloudformation describe-stacks --stack-name
  photo-booth-prod` succeeds.

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/deploy.yml
git commit -m "ci: add GitHub Actions workflow to deploy CFT and frontend to AWS on merge to main"
```

---

## AWS account handoff checklist (what's needed to unblock Task 14)

These are the only manual, console/CLI, non-CloudFormation steps in this
plan — everything else is defined as code in `infra/template.yaml`.

1. **An AWS account** (or a dedicated sub-account) this project can own.
2. **An OIDC identity provider for GitHub Actions** in that account
   (`token.actions.githubusercontent.com`), plus an IAM role
   (`AWS_DEPLOY_ROLE_ARN`) trusting it, scoped to this repo
   (`repo:<your-org-or-user>/photo-booth:ref:refs/heads/main`). This
   role needs permission to deploy the CFT (CloudFormation, S3, Lambda,
   API Gateway, IAM, Secrets Manager, CloudFront) — avoids long-lived
   access keys in GitHub entirely.
3. **Two GitHub repository secrets**:
   - `AWS_ACCOUNT_ID`
   - `AWS_DEPLOY_ROLE_ARN`
   - `GALLERY_PASSWORD` (the real operator password for production)
4. **After the first successful deploy**, manually create the Pi
   uploader's access key (not stored in CloudFormation state, per
   Task 6 Step 3):
   ```bash
   aws iam create-access-key --user-name kinetic-photo-booth-uploader
   ```
   Store the resulting `AccessKeyId`/`SecretAccessKey` on each Pi's local
   config (not in git, not in CloudFormation).

Everything through Task 13 (repo, Lambdas, frontend, CFT, LocalStack,
integration tests, CI) can be built and tested with zero AWS account
access. Task 14's workflow can be written and committed now, but its
first real run — and the physical-Pi hardware verification in Task 12 —
wait on items 1–4 above and on the Pi hardware itself, respectively.
