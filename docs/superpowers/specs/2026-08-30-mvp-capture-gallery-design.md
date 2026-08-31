# Kinetic Photo Booth — MVP: Capture → S3 → Gallery

**Status:** Approved for planning
**Date:** 2026-08-30
**Context project:** `~/.context/projects/kinetic-photo-booth/`

## Purpose

Build the smallest end-to-end pipeline that lets a haunted-house-style event
capture photos on button press and display them to a single operator in a
web gallery shortly after. No payment, no watermarking, no accounts — those
are explicitly phase 2+. This phase proves out capture hardware, storage,
and a serverless gallery service, and lays groundwork (S3 key structure,
Lambda contracts) so phase 2 doesn't require a data migration or contract
break.

## Out of scope (phase 2+)

- Payment / pay-to-unlock (Stripe or otherwise)
- Watermarking
- Multi-user accounts / per-user login
- Per-event gallery filtering (built as a hook, not exercised)
- Camera self-registration UI

## Architecture

```
[Pi Zero W: button + USB webcam]
        | WiFi (portable hotspot/travel router, open network)
        v
   S3 PutObject  ---->  [S3 bucket: private, 30-day lifecycle policy]
                              ^
                              | pre-signed GET URLs (short TTL)
                              |
[CloudFront + S3 static site] --calls--> [API Gateway]
        ^                                      |
        | operator browser                     +--> [Lambda: auth]  (shared password -> session)
        |                                      |
        +--- session/cookie ------------------ +--> [Lambda: list]  (ListObjectsV2 -> pre-signed URLs)
```

One or more Pi Zero W units can feed the same bucket concurrently; the
gallery doesn't distinguish device count.

## Components

### 1. Capture device (Pi Zero W)
- GPIO button triggers capture.
- USB webcam captures a still frame (`fswebcam`/`ffmpeg`/`v4l2`).
- Python + `boto3` uploads directly to S3 using credentials scoped to
  `PutObject` on this bucket only (no read/list/delete).
- Object key: `events/{event-id}/{device-id}/{uuid}.jpg` — event-id is fixed
  for phase 1 (single event) but present in every key from day one.
- On upload failure (WiFi drop, S3 unreachable): retry with backoff; if
  still failing, queue the file on local SD storage and retry on next
  trigger/heartbeat rather than dropping the photo.

### 2. S3 bucket
- Private, no public access, no public bucket policy.
- Lifecycle rule: expire objects after 30 days.
- Key prefix structure (`events/{event-id}/{device-id}/{uuid}.jpg`) is the
  only phase-2 hook baked into storage.

### 3. Auth Lambda (behind API Gateway)
- Accepts a shared operator password, stored in Secrets Manager in deployed
  environments (an env var is used only for local/offline testing).
- On success, issues a short-lived signed session (cookie or JWT).
- Rejections are generic (no hints); requests are rate-limited to blunt
  brute-force attempts against the single shared credential.
- Phase-2 hook: swap the password check for Cognito/per-user auth without
  changing what it returns to the frontend (a valid session).

### 4. List Lambda (behind API Gateway)
- Requires a valid session (checked via the auth Lambda's session format).
- Calls `ListObjectsV2` on the bucket, generates a pre-signed GET URL (short
  TTL, e.g. 15–60 min) per object, returns the list to the frontend.
- Accepts an optional event/tenant filter query param — ignored/unused in
  phase 1, present so the frontend contract doesn't change in phase 2.

### 5. Gallery frontend
- Static HTML/JS hosted on S3, served via CloudFront.
- Login screen (password) → calls auth Lambda → stores session →
  calls list Lambda → renders all returned photos.
- Empty state when no photos exist yet.
- Expired session redirects back to login.

### 6. Dev tooling: test photo uploader
- CLI/script (`scripts/upload-test-photo.sh` or Python equivalent) that
  mimics the Pi's upload exactly: same key structure, same IAM scope
  (`PutObject` only).
- Used for manual testing (seed bucket, load gallery) and integration tests
  (upload fixture images, hit list Lambda, assert URLs come back).
- Lives in-repo, wired into `make seed` / `make test`.

## Data flow

1. Button press on Pi → webcam captures frame → Pi uploads to S3 directly.
2. Operator opens gallery site, logs in with shared password → auth Lambda
   issues session.
3. Frontend calls list Lambda with session → Lambda lists bucket, returns
   pre-signed URLs.
4. Browser renders all current photos (flat list, no per-event filtering
   in phase 1).

## Error handling

| Failure | Behavior |
|---|---|
| Pi can't reach S3 | Retry w/ backoff; queue locally on SD, retry later |
| Duplicate filenames | Not possible — device-id + UUID keys |
| Wrong gallery password | Generic rejection, rate-limited |
| Expired session | Frontend redirects to login |
| Expired pre-signed URL | Link goes stale; re-fetch list for a fresh one |
| No photos yet | Friendly empty state, not an error |
| Lambda/API Gateway errors | Standard 4xx/5xx JSON; CloudWatch logs on both Lambdas |

## Phase 2 hooks (designed for, not built)

- Auth Lambda → real per-user accounts (Cognito or custom), same session
  contract to the frontend.
- List Lambda's event/tenant filter param → real per-event gallery
  filtering.
- S3 key prefix (`events/{event-id}/...`) → multi-tenant isolation without
  a data migration.
- Watermarking/paywall insertable as a transform step between list and
  serve (pre-signed URLs would point at a processed copy).

## Testing

- **Dev tooling uploader** seeds the bucket without hardware.
- **Integration tests**: upload fixture images via the uploader script,
  call list Lambda (locally or against a deployed dev stack), assert
  correct count/URLs returned and that they're fetchable.
- **Local deployment testing**: TBD in implementation plan — likely
  SAM/LocalStack or a disposable dev CloudFormation stack, decided during
  planning.
