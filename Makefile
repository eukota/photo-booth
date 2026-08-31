.PHONY: venv test lint local-up local-down local-build local-deploy local-api-url \
        local-serve-frontend seed integration-test

LOCALSTACK_CREDS = AWS_ACCESS_KEY_ID=test AWS_SECRET_ACCESS_KEY=test AWS_DEFAULT_REGION=us-east-1
LOCALSTACK_ENDPOINT = http://localhost:4566
# SAM needs a python3.12 interpreter on PATH (Lambda runtime version);
# the system default may be newer. All dev tools (sam, samlocal, pytest,
# black, flake8) live in .venv, not necessarily on the caller's PATH -
# every target below runs through this same PATH so `make <target>` works
# whether or not you've activated the venv yourself.
PY312_PATH = /opt/homebrew/opt/python@3.12/libexec/bin
VENV_BIN = $(CURDIR)/.venv/bin
RUN_PATH = PATH="$(VENV_BIN):$(PY312_PATH):$$PATH"

venv: .venv/.installed

.venv/.installed: requirements-dev.txt
	@test -d .venv || python3 -m venv .venv
	@$(VENV_BIN)/pip install -q -r requirements-dev.txt
	@$(VENV_BIN)/pip install -q aws-sam-cli-local
	@touch .venv/.installed

test: venv
	@$(RUN_PATH) PYTHONPATH=. pytest tests/unit -v

lint: venv
	@$(RUN_PATH) black --check src pi scripts tests
	@$(RUN_PATH) flake8 src pi scripts tests

local-up:
	docker compose -f docker-compose.localstack.yml up -d

local-down:
	docker compose -f docker-compose.localstack.yml down

local-build: venv
	@$(RUN_PATH) sam build --template-file infra/template.yaml

local-deploy: local-build
	@$(LOCALSTACK_CREDS) $(RUN_PATH) \
	samlocal deploy \
	  --template-file .aws-sam/build/template.yaml \
	  --stack-name photo-booth-local \
	  --capabilities CAPABILITY_NAMED_IAM \
	  --parameter-overrides GalleryPassword=localtest DeployCloudFront=false \
	    PresignEndpointUrl=$(LOCALSTACK_ENDPOINT) \
	  --resolve-s3 \
	  --no-confirm-changeset \
	  --region us-east-1

# LocalStack doesn't route the real-AWS-style ApiBaseUrl CFN output
# locally; this derives the local `_user_request_` test-invoke URL instead.
local-api-url: venv
	@$(LOCALSTACK_CREDS) $(RUN_PATH) aws --endpoint-url=$(LOCALSTACK_ENDPOINT) \
	  cloudformation describe-stack-resource \
	  --stack-name photo-booth-local --logical-resource-id GalleryApi \
	  --query 'StackResourceDetail.PhysicalResourceId' --output text \
	  | xargs -I{} echo "$(LOCALSTACK_ENDPOINT)/restapis/{}/prod/_user_request_"

local-serve-frontend: venv
	@API_URL=$$($(MAKE) -s local-api-url); \
	mkdir -p /tmp/photo-booth-frontend; \
	sed "s|__API_BASE_URL__|$$API_URL|" frontend/index.html > /tmp/photo-booth-frontend/index.html; \
	cp frontend/app.js frontend/style.css /tmp/photo-booth-frontend/; \
	echo "Serving gallery at http://localhost:8080 (API: $$API_URL)"; \
	cd /tmp/photo-booth-frontend && $(VENV_BIN)/python -m http.server 8080

seed: venv
	@$(LOCALSTACK_CREDS) $(RUN_PATH) PYTHONPATH=. \
	python scripts/upload_test_photo.py \
	  --bucket kinetic-photo-booth-photos-000000000000 \
	  --count 3 --endpoint-url $(LOCALSTACK_ENDPOINT)

integration-test: venv
	@API_URL=$$($(MAKE) -s local-api-url); \
	LOCAL_API_BASE_URL=$$API_URL $(LOCALSTACK_CREDS) $(RUN_PATH) PYTHONPATH=. \
	pytest tests/integration -v
