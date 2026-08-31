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
