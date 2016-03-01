#!/usr/bin/env sh

# This script drives httpie to interact with a local development ltd-keeper
# instance. The output can be be used for examples in the docs.
#
# Development server prep
# 1. Delete any existing ltd-keeper-dev.sqlite
# 2. Run the dev server ./run.py
# 3. Get an auth token
#        http --auth user:pass GET http://localhost/token
#        export KEEPER_TOKEN=<token>
# In a separate session, run ./doc_example_driver.sh
# Shut down the dev server and clean-up and sqlite DB

if [ -e "ltd_keeper_doc_examples.txt" ]; then
    rm "ltd_keeper_doc_examples.txt"
    touch "ltd_keeper_doc_examples.txt"
fi

http -p hbHB --pretty=format --auth $KEEPER_TOKEN: \
    POST http://localhost:5000/products/ \
    bucket_name="an-s3-bucket" \
    doc_repo="https://github.com/lsst/pipelines_docs.git" \
    domain="pipelines.lsst.io" \
    slug="lsst_apps" \
    title="LSST Science Pipelines" \
    >> ltd_keeper_doc_examples.txt

echo "\n\n---\n" >> ltd_keeper_doc_examples.txt

http -p hbHB --pretty=format --auth $KEEPER_TOKEN: \
    POST http://localhost:5000/products/ \
    bucket_name="an-s3-bucket" \
    doc_repo="https://github.com/lsst/qserv.git" \
    domain="qserv.lsst.io" \
    slug="qserv_distrib" \
    title="Qserv" \
    >> ltd_keeper_doc_examples.txt

echo "\n\n---\n" >> ltd_keeper_doc_examples.txt

http -p hbHB --pretty=format --auth $KEEPER_TOKEN: \
    GET http://localhost:5000/products/lsst_apps \
    >> ltd_keeper_doc_examples.txt

echo "\n\n---\n" >> ltd_keeper_doc_examples.txt

http -p hbHB --pretty=format --auth $KEEPER_TOKEN: \
    GET http://localhost:5000/products/ \
    >> ltd_keeper_doc_examples.txt

echo "\n\n---\n" >> ltd_keeper_doc_examples.txt

http -p hbHB --pretty=format --auth $KEEPER_TOKEN: \
    PATCH http://localhost:5000/products/qserv_distrib \
    title="Qserv Data Access" \
    >> ltd_keeper_doc_examples.txt

echo "\n\n---\n" >> ltd_keeper_doc_examples.txt

http -p hbHB --pretty=format --auth $KEEPER_TOKEN: \
    POST http://localhost:5000/products/lsst_apps/builds/ \
    slug='b1' \
    github_requester='jonathansick' \
    git_refs:='["master"]' \
    >> ltd_keeper_doc_examples.txt

echo "\n\n---\n" >> ltd_keeper_doc_examples.txt

http -p hbHB --pretty=format --auth $KEEPER_TOKEN: \
    POST http://localhost:5000/products/lsst_apps/builds/ \
    slug='b2' \
    github_requester='jonathansick' \
    git_refs:='["master"]' \
    >> ltd_keeper_doc_examples.txt

echo "\n\n---\n" >> ltd_keeper_doc_examples.txt

http -p hbHB --pretty=format --auth $KEEPER_TOKEN: \
    POST http://localhost:5000/builds/1/uploaded \
    >> ltd_keeper_doc_examples.txt

echo "\n\n---\n" >> ltd_keeper_doc_examples.txt

http -p hbHB --pretty=format --auth $KEEPER_TOKEN: \
    GET http://localhost:5000/products/lsst_apps/builds/ \
    >> ltd_keeper_doc_examples.txt

echo "\n\n---\n" >> ltd_keeper_doc_examples.txt

http -p hbHB --pretty=format --auth $KEEPER_TOKEN: \
    GET http://localhost:5000/builds/1 \
    >> ltd_keeper_doc_examples.txt

echo "\n\n---\n" >> ltd_keeper_doc_examples.txt

http -p hbHB --pretty=format --auth $KEEPER_TOKEN: \
    POST http://localhost:5000/products/lsst_apps/editions/ \
    slug="latest" \
    title="Latest" \
    build_url="http://localhost:5000/builds/1" \
    tracked_refs:='["master"]' \
    published_url="pipelines.lsst.io" \
    >> ltd_keeper_doc_examples.txt

echo "\n\n---\n" >> ltd_keeper_doc_examples.txt

http -p hbHB --pretty=format --auth $KEEPER_TOKEN: \
    PATCH http://localhost:5000/editions/1 \
    title="Development master" \
    >> ltd_keeper_doc_examples.txt

echo "\n\n---\n" >> ltd_keeper_doc_examples.txt

http -p hbHB --pretty=format --auth $KEEPER_TOKEN: \
    GET http://localhost:5000/editions/1 \
    >> ltd_keeper_doc_examples.txt

echo "\n\n---\n" >> ltd_keeper_doc_examples.txt

http -p hbHB --pretty=format --auth $KEEPER_TOKEN: \
    GET http://localhost:5000/products/lsst_apps/editions/ \
    >> ltd_keeper_doc_examples.txt

echo "\n\n---\n" >> ltd_keeper_doc_examples.txt

http -p hbHB --pretty=format --auth $KEEPER_TOKEN: \
    POST http://localhost:5000/editions/1/rebuild \
    build_url="http://localhost:5000/builds/2" \
    >> ltd_keeper_doc_examples.txt

echo "\n\n---\n" >> ltd_keeper_doc_examples.txt

http -p hbHB --pretty=format --auth $KEEPER_TOKEN: \
    DELETE http://localhost:5000/builds/1 \
    >> ltd_keeper_doc_examples.txt

echo "\n\n---\n" >> ltd_keeper_doc_examples.txt

http -p hbHB --pretty=format --auth $KEEPER_TOKEN: \
    DELETE http://localhost:5000/editions/1 \
    >> ltd_keeper_doc_examples.txt
