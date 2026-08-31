.PHONY: test lint local-up local-down local-deploy seed integration-test

test:
	PYTHONPATH=. pytest tests/unit -v

lint:
	black --check src pi scripts tests
	flake8 src pi scripts tests

local-up:
	docker compose -f docker-compose.localstack.yml up -d

local-down:
	docker compose -f docker-compose.localstack.yml down

local-deploy:
	AWS_ACCESS_KEY_ID=test AWS_SECRET_ACCESS_KEY=test AWS_DEFAULT_REGION=us-east-1 \
	sam deploy \
	  --template-file infra/template.yaml \
	  --stack-name photo-booth-local \
	  --capabilities CAPABILITY_NAMED_IAM \
	  --parameter-overrides GalleryPassword=localtest \
	  --resolve-s3 \
	  --no-confirm-changeset \
	  --region us-east-1 \
	  --endpoint-url http://localhost:4566
	AWS_ACCESS_KEY_ID=test AWS_SECRET_ACCESS_KEY=test AWS_DEFAULT_REGION=us-east-1 \
	aws --endpoint-url=http://localhost:4566 s3 sync frontend/ \
	  s3://kinetic-photo-booth-frontend-000000000000/

seed:
	PYTHONPATH=. AWS_ACCESS_KEY_ID=test AWS_SECRET_ACCESS_KEY=test AWS_DEFAULT_REGION=us-east-1 \
	python scripts/upload_test_photo.py --count 3 --endpoint-url http://localhost:4566

integration-test:
	PYTHONPATH=. pytest tests/integration -v
