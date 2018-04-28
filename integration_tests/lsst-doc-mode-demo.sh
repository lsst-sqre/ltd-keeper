#!/bin/sh

# Demo/integration test for an edition that follows the 'lsst_doc' mode for
# automatically tracking the latest semantic version.
#
# Set up:
#
# make db-init
# make worker  # in a separate terminal
# make run  # in a separate terminal
# bash integration_tests/lsst-doc-mode-demo.sh

# Request, parse, and set the auth token
TOKEN=`http --auth user:pass GET :5000/token | jq '.token'`

# Create a product
http --auth $TOKEN: POST :5000/products/ slug="demo" doc_repo="https://example.com/repo" title="Demo" root_domain="lsst.io" root_fastly_domain="https://fastly.example.com" bucket_name="bucket-name" main_mode="lsst_doc"

# Register a new build
http --auth $TOKEN: POST :5000/products/demo/builds/ git_refs:='["master"]'
# Confirm the build is uploaded. This also rebuilds the default edition for 'demo'
http --auth $TOKEN: PATCH :5000/builds/1 uploaded:=true

# Register a new build for a ticket branch
http --auth $TOKEN: POST :5000/products/demo/builds/ git_refs:='["tickets/DM-1"]'
# Confirm the build is uploaded. This also rebuilds the default edition for 'demo'
http --auth $TOKEN: PATCH :5000/builds/2 uploaded:=true

# Register a new build for a semantic version. This should both create a
# v1-0 edition and update the main edition
http --auth $TOKEN: POST :5000/products/demo/builds/ git_refs:='["v1.0"]'
# Confirm the build is uploaded. This also rebuilds the default edition for 'demo'
http --auth $TOKEN: PATCH :5000/builds/3 uploaded:=true

# Check that the main edition points to /builds/3
http GET :5000/editions/1
