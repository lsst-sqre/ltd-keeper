"""Flask-SQLAlchemy-based database ORM models.

Copyright 2016 AURA/LSST.
Copyright 2014 Miguel Grinberg.
"""
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from flask import url_for, current_app

from . import db
from .exceptions import ValidationError
from .utils import split_url, format_utc_datetime, \
    JSONEncodedVARCHAR, MutableList


class Permission(object):
    """User permission definitions.

    These permissions can be added to the ``permissions`` column of a
    :class:`User`. For example, to give a user permission to both
    administer products *and* editions::

        p = Permission
        user = User(username='test-user',
                    permissions=p.ADMIN_PRODUCT | p.ADMIN_EDITION)

    You can give a user permission to do everything with the
    :meth:`User.full_permissions` helper method:

        p = Permission
        user = User(username='admin-user',
                    permission=p.full_permissions())

    See :class:`User.has_permission` for how to use these permission
    bits to test user authorization.

    Attributes
    ----------
    ADMIN_USER
        Permission to create a new API user, view API users, and modify
        API user permissions.
    ADMIN_PRODUCT
        Permission to add, modify and deprecate Products.
    ADMIN_EDITION
        Permission to add, modify and deprecate Editions.
    UPLOAD_BUILD
        Permission to create a new Build.
    DEPRECATE_BUILD
        Permission to deprecate a Build.
    """

    ADMIN_USER = 0b1
    ADMIN_PRODUCT = 0b10
    ADMIN_EDITION = 0b100
    UPLOAD_BUILD = 0b1000
    DEPRECATE_BUILD = 0b10000

    @classmethod
    def full_permissions(self):
        """Helper method to create a bit mask with all permissions enabled.

        Returns
        -------
        permissions : int
            Bit mask with all permissions enabled.
        """
        return self.ADMIN_USER | self.ADMIN_PRODUCT | self.ADMIN_EDITION \
            | self.UPLOAD_BUILD | self.DEPRECATE_BUILD


class User(db.Model):
    """DB model for authenticated API users."""

    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True)
    password_hash = db.Column(db.String(128))
    permissions = db.Column(db.Integer)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def generate_auth_token(self, expires_in=3600):
        s = Serializer(current_app.config['SECRET_KEY'], expires_in=expires_in)
        return s.dumps({'id': self.id}).decode('utf-8')

    @staticmethod
    def verify_auth_token(token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return None
        return User.query.get(data['id'])

    def has_permission(self, permissions):
        """Verify that a user has a given set of permissions.

        Permissions are defined in the :class:`Permission` class. To check
        authorization for a user against a specific permissions::

            user.has_permission(Permission.ADMIN_PRODUCT)

        You can also check authorization against multiple permissions::

            user.has_permission(
                Permission.ADMIN_PRODUCT | PERMISSION.ADMIN_EDITION)

        Arguments
        ---------
        permissions : int
            The permission bits to test. Use attributes from
            :class:`Permission`.

        Returns
        -------
        authorized : bool
            `True` if a user is authorized with the requested permissions.
        """
        return (self.permissions & permissions) == permissions


class Product(db.Model):
    """DB model for software products.

    A software product maps to a top-level Eups package and has a single
    product documentation repository associated with it.
    """

    __tablename__ = 'products'
    id = db.Column(db.Integer, primary_key=True)
    # URL/path-safe identifier for this product
    slug = db.Column(db.Unicode(256), nullable=False, unique=True)
    # URL of the Git documentation repo (i.e., on GitHub)
    doc_repo = db.Column(db.String(256), nullable=False)
    # Human-readlable product title
    title = db.Column(db.Unicode(256), nullable=False)
    # Domain name, without protocol or path
    domain = db.Column(db.String(256), nullable=False)
    # Name of the S3 bucket hosting builds
    bucket_name = db.Column(db.String(256), nullable=True)

    # One-to-many relationships to builds and editions
    # are defined in those classes
    builds = db.relationship('Build', backref='product', lazy='dynamic')
    editions = db.relationship('Edition', backref='product', lazy='dynamic')

    def get_url(self):
        """API URL for this entity."""
        return url_for('api.get_product', slug=self.slug, _external=True)

    def export_data(self):
        """Export entity as JSON-compatible dict."""
        return {
            'self_url': self.get_url(),
            'slug': self.slug,
            'doc_repo': self.doc_repo,
            'title': self.title,
            'domain': self.domain,
            'bucket_name': self.bucket_name
        }

    def import_data(self, data):
        """Convert a dict `data` into a table row."""
        try:
            self.slug = data['slug']
            self.doc_repo = data['doc_repo']
            self.title = data['title']
            self.domain = data['domain']
            self.bucket_name = data['bucket_name']
        except KeyError as e:
            raise ValidationError('Invalid Product: missing ' + e.args[0])
        return self

    def patch_data(self, data):
        """Partial update of fields from PUT requests on an existing product.

        Currently only updates to doc_repo and title are supported.
        """
        if 'doc_repo' in data:
            self.doc_repo = data['doc_repo']

        if 'title' in data:
            self.title = data['title']


class Build(db.Model):
    """DB model for documentation builds."""

    __tablename__ = 'builds'
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'),
                           index=True)
    # name of build; URL-safe slug used as directory in build bucket
    slug = db.Column(db.String(256), nullable=False)
    # auto-assigned date build was created
    date_created = db.Column(db.DateTime, default=datetime.now(),
                             nullable=False)
    # set only when the build is deprecated (ready for deletion)
    date_ended = db.Column(db.DateTime, nullable=True)
    # json-persisted list of Git refs that determine the version of Product
    git_refs = db.Column(MutableList.as_mutable(JSONEncodedVARCHAR(2048)))
    # github handle of person requesting the build (optional)
    github_requester = db.Column(db.String(256), nullable=True)
    # Flag to indicate the doc has been uploaded to S3.
    uploaded = db.Column(db.Boolean, default=False)

    # Relationships
    # product - from Product class

    @property
    def bucket_root_dirname(self):
        """Directory in the bucket where the build is located."""
        return '/'.join((self.product.slug, 'builds', self.slug))

    def get_url(self):
        """API URL for this entity."""
        return url_for('api.get_build', id=self.id, _external=True)

    def export_data(self):
        """Export entity as JSON-compatible dict."""
        return {
            'self_url': self.get_url(),
            'product_url': self.product.get_url(),
            'slug': self.slug,
            'date_created': format_utc_datetime(self.date_created),
            'date_ended': format_utc_datetime(self.date_ended),
            'uploaded': self.uploaded,
            'bucket_name': self.product.bucket_name,
            'bucket_root_dir': self.bucket_root_dirname,
            'git_refs': self.git_refs,
            'github_requester': self.github_requester
        }

    def import_data(self, data):
        """Convert a dict `data` into a table row."""
        try:
            git_refs = data['git_refs']
            if isinstance(git_refs, str):
                raise ValidationError('Invalid Build: git_refs must be an '
                                      'array of strings')
            self.git_refs = git_refs
        except KeyError as e:
            raise ValidationError('Invalid Build: missing ' + e.args[0])

        if 'github_requester' in data:
            self.github_requester = data['github_requester']

        if 'slug' in data:
            identical_slugs = len(
                Build.query.autoflush(False)
                .filter(Build.product == self.product)
                .filter(Build.slug == data['slug'])
                .all())
            if identical_slugs > 0:
                raise ValidationError('Invalid Build, slug already exists')
            self.slug = data['slug']
        else:
            # auto-create a slug
            all_builds = Build.query.autoflush(False)\
                .filter(Build.product == self.product)\
                .all()
            slugs = [b.slug for b in all_builds]
            trial_slug_n = 1
            while str(trial_slug_n) in slugs:
                trial_slug_n += 1
            self.slug = str(trial_slug_n)

        self.date_created = datetime.now()

        return self

    def patch_data(self, data):
        """Modify build via PATCH.

        Only allowed modification is to set 'uploaded' field to True to
        acknowledge a build upload to the bucket.
        """
        if 'uploaded' in data:
            self.uploaded = data['uploaded']

    def deprecate_build(self):
        """Trigger a build deprecation.

        Sets the `date_ended` field.
        """
        self.date_ended = datetime.now()


class Edition(db.Model):
    """DB model for Editions. Editions are fixed-location publications of the
    docs. Editions are updated by new builds; though not all builds are used
    by Editions.
    """

    __tablename__ = 'editions'
    id = db.Column(db.Integer, primary_key=True)
    # Product that this Edition belongs do
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'),
                           index=True)
    # Build currently used by this Edition
    build_id = db.Column(db.Integer, db.ForeignKey('builds.id'),
                         index=True)
    # What product Git refs this Edition tracks and publishes
    tracked_refs = db.Column(MutableList.as_mutable(JSONEncodedVARCHAR(2048)))
    # url-safe slug for edition
    slug = db.Column(db.String(256), nullable=False)
    # Human-readable title for edition
    title = db.Column(db.Unicode(256), nullable=False)
    # full url where the documentation is published from
    published_url = db.Column(db.String(256), nullable=False)
    # Date when this edition was initially created
    date_created = db.Column(db.DateTime, default=datetime.now(),
                             nullable=False)
    # Date when the edition was updated (e.g., new build)
    date_rebuilt = db.Column(db.DateTime, default=datetime.now(),
                             nullable=False)
    # set only when the Edition is deprecated (ready for deletion)
    date_ended = db.Column(db.DateTime, nullable=True)

    # Relationships
    build = db.relationship('Build', uselist=False)  # one-to-one

    def get_url(self):
        """API URL for this entity."""
        return url_for('api.get_edition', id=self.id, _external=True)

    def export_data(self):
        """Export entity as JSON-compatible dict."""
        return {
            'self_url': self.get_url(),
            'product_url': self.product.get_url(),
            'build_url': self.build.get_url(),
            'tracked_refs': self.tracked_refs,
            'slug': self.slug,
            'title': self.title,
            'published_url': self.published_url,
            'date_created': format_utc_datetime(self.date_created),
            'date_rebuilt': format_utc_datetime(self.date_rebuilt),
            'date_ended': format_utc_datetime(self.date_ended)
        }

    def import_data(self, data):
        """Initialize the edition on POST.

        The Product is set on object initialization.
        """
        try:
            tracked_refs = data['tracked_refs']
            self.slug = data['slug']
            self.title = data['title']
            self.published_url = data['published_url']
        except KeyError as e:
            raise ValidationError('Invalid Edition: missing ' + e.args[0])

        if isinstance(tracked_refs, str):
            raise ValidationError('Invalid Edition: tracked_refs must be an '
                                  'array of strings')
        self.tracked_refs = tracked_refs

        # Set initial build pointer
        self.rebuild(data['build_url'])

        self.date_created = datetime.now()

        return self

    def patch_data(self, data):
        """Partial update of the Edition."""
        if 'tracked_refs' in data:
            tracked_refs = data['tracked_refs']
            if isinstance(tracked_refs, str):
                raise ValidationError('Invalid Edition: tracked_refs must '
                                      'be an array of strings')
            self.tracked_refs = data['tracked_refs']

        if 'title' in data:
            self.title = data['title']

        if 'build_url' in data:
            self.rebuild(data['build_url'])

        if 'published_url' in data:
            self.published_url = data['published_url']

    def rebuild(self, build_url):
        """Modify the build this edition points to."""
        build_endpoint, build_args = split_url(build_url)
        if build_endpoint != 'api.get_build' or 'id' not in build_args:
            raise ValidationError('Invalid build_url: ' +
                                  'build_url')
        self.build = Build.query.get(build_args['id'])
        if self.build is None:
            raise ValidationError('Invalid build_url: ' + build_url)

        self.date_rebuilt = datetime.now()

    def deprecate(self):
        """Deprecate the Edition; sets the `date_ended` field."""
        self.date_ended = datetime.now()
