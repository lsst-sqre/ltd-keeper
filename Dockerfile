FROM python:3.5.1

MAINTAINER Jonathan Sick <jsick@lsst.org>
LABEL description="API server for LSST the Docs" \
      name="lsstsqre/ltd-keeper"

ENV APPDIR /ltd-keeper

# Supply on CL as --build-arg VERSION=<version> (or run `make image`).
ARG VERSION
LABEL version="$VERSION"

# Must run python setup.py sdist first before building the Docker image.
# RUN mkdir -p $APPDIR
COPY migrations \
     uwsgi.ini \
     dist/lsst-the-docs-keeper-$VERSION.tar.gz \
     bin/run-celery-worker.bash \
     $APPDIR/
# Recreate the directory structure of alembic's migrations directory
COPY migrations/alembic.ini \
     migrations/env.py \
     migrations/script.py.mako \
     $APPDIR/migrations/
COPY migrations/versions/* $APPDIR/migrations/versions/

WORKDIR $APPDIR

RUN pip install lsst-the-docs-keeper-$VERSION.tar.gz && \
    rm lsst-the-docs-keeper-$VERSION.tar.gz && \
    groupadd -r uwsgi_grp && useradd -r -g uwsgi_grp uwsgi && \
    chown -R uwsgi:uwsgi_grp $APPDIR

USER uwsgi

EXPOSE 3031

CMD ["uwsgi", "uwsgi.ini"]
