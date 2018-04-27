#!/bin/sh

# Demo/integration test for creating a product and uploading a build.
# This exercises the celery task queue by rebuilding the edition.
#
# Set up:
#
# make db-init
# make worker  # in a separate terminal
# make run  # in a separate terminal
# bash integration_tests/edition-rebuild-demo.sh

# Request, parse, and set the auth token
TOKEN=`http --auth user:pass GET :5000/token | jq '.token'`

# Create a product
http --auth $TOKEN: POST :5000/products/ slug="demo" doc_repo="https://example.com/repo" title="Demo" root_domain="lsst.io" root_fastly_domain="https://fastly.example.com" bucket_name="bucket-name"

# Register a new build
http --auth $TOKEN: POST :5000/products/demo/builds/ git_refs:='["master"]'

# Confirm the build is uploaded. This also rebuilds the default edition for 'demo'
http --auth $TOKEN: PATCH :5000/builds/1 uploaded:=true

echo "Done"
