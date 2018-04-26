"""Flask-SQLAlchemy-based database ORM models.

Copyright 2016 AURA/LSST.
Copyright 2014 Miguel Grinberg.
"""
from datetime import datetime
import uuid
import urllib.parse
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from flask import url_for, current_app
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from structlog import get_logger

from . import s3
from . import route53
from . import fastly
from .exceptions import ValidationError
from .utils import split_url, format_utc_datetime, \
    JSONEncodedVARCHAR, MutableList, validate_product_slug, validate_path_slug
from .gitrefutils import LsstDocVersionTag


db = SQLAlchemy()
"""Database connection.

This is initialized in `keeper.appfactory.create_flask_app`.
"""

migrate = Migrate()
"""Flask-SQLAlchemy extension instance.

This is initialized in `keeper.appfactory.create_flask_app`.
"""


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
    username = db.Column(db.Unicode(255), index=True, unique=True)
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
        except Exception:
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
    slug = db.Column(db.Unicode(255), nullable=False, unique=True)
    # URL of the Git documentation repo (i.e., on GitHub)
    doc_repo = db.Column(db.Unicode(255), nullable=False)
    # Human-readlable product title
    title = db.Column(db.Unicode(255), nullable=False)
    # Root domain name serving docs (e.g., lsst.io)
    root_domain = db.Column(db.Unicode(255), nullable=False)
    # Fastly CDN domain name (without doc's domain prepended)
    root_fastly_domain = db.Column(db.Unicode(255), nullable=False)
    # Name of the S3 bucket hosting builds
    bucket_name = db.Column(db.Unicode(255), nullable=True)
    # surrogate_key for Fastly quick purges of dashboards
    # Editions and Builds have independent surrogate keys.
    surrogate_key = db.Column(db.String(32))

    # One-to-many relationships to builds and editions
    # are defined in those classes
    builds = db.relationship('Build', backref='product', lazy='dynamic')
    editions = db.relationship('Edition', backref='product', lazy='dynamic')

    @classmethod
    def from_url(cls, product_url):
        """Get a Product given its API URL.

        Parameters
        ----------
        product_url : `str`
            API URL of the product. This is the same as `Product.get_url`.

        Returns
        -------
        product : `Product`
            The `Product` instance corresponding to the URL.
        """
        logger = get_logger(__name__)

        # Get new Product ID from the product resource's URL
        product_endpoint, product_args = split_url(product_url)
        if product_endpoint != 'api.get_product' or 'slug' not in product_args:
            logger.debug('Invalid product_url',
                         product_endpoint=product_endpoint,
                         product_args=product_args)
            raise ValidationError('Invalid product_url: {}'
                                  .format(product_url))
        slug = product_args['slug']
        product = cls.query.filter_by(slug=slug).first_or_404()

        return product

    @property
    def domain(self):
        """Domain where docs for this product are served from.

        (E.g. ``product.lsst.io`` if ``product`` is the slug and ``lsst.io``
        is the ``root_domain``.)
        """
        return '.'.join((self.slug, self.root_domain))

    @property
    def fastly_domain(self):
        """Domain where Fastly serves content from for this product.
        """
        # Note that in non-ssl contexts fastly wants you to prepend the domain
        # to fastly's origin domain. However we don't do this with TLS.
        # return '.'.join((self.domain, self.root_fastly_domain))
        return self.root_fastly_domain

    @property
    def published_url(self):
        """URL where this product is published to the end-user."""
        parts = ('https', self.domain, '', '', '', '')
        return urllib.parse.urlunparse(parts)

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
            'root_domain': self.root_domain,
            'root_fastly_domain': self.root_fastly_domain,
            'domain': self.domain,
            'fastly_domain': self.fastly_domain,
            'bucket_name': self.bucket_name,
            'published_url': self.published_url,
            'surrogate_key': self.surrogate_key
        }

    def import_data(self, data):
        """Convert a dict `data` into a table row."""
        try:
            self.slug = data['slug']
            self.doc_repo = data['doc_repo']
            self.title = data['title']
            self.root_domain = data['root_domain']
            self.root_fastly_domain = data['root_fastly_domain']
            self.bucket_name = data['bucket_name']
        except KeyError as e:
            raise ValidationError('Invalid Product: missing ' + e.args[0])

        # clean any full stops pre-pended on inputted fully qualified domains
        self.root_domain = self.root_domain.lstrip('.')
        self.root_fastly_domain = self.root_fastly_domain.lstrip('.')

        # Validate slug; raises ValidationError
        validate_product_slug(self.slug)

        # Create a surrogate key on demand
        if self.surrogate_key is None:
            self.surrogate_key = uuid.uuid4().hex

        # Setup Fastly CNAME with Route53
        AWS_ID = current_app.config['AWS_ID']
        AWS_SECRET = current_app.config['AWS_SECRET']
        if AWS_ID is not None and AWS_SECRET is not None:
            route53.create_cname(self.domain, self.fastly_domain,
                                 AWS_ID, AWS_SECRET)

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
    slug = db.Column(db.Unicode(255), nullable=False)
    # auto-assigned date build was created
    date_created = db.Column(db.DateTime, default=datetime.now(),
                             nullable=False)
    # set only when the build is deprecated (ready for deletion)
    date_ended = db.Column(db.DateTime, nullable=True)
    # json-persisted list of Git refs that determine the version of Product
    git_refs = db.Column(MutableList.as_mutable(JSONEncodedVARCHAR(2048)))
    # github handle of person requesting the build (optional)
    github_requester = db.Column(db.Unicode(255), nullable=True)
    # Flag to indicate the doc has been uploaded to S3.
    uploaded = db.Column(db.Boolean, default=False)
    # The surrogate-key header for Fastly (quick purges); 32-char hex
    surrogate_key = db.Column(db.String(32), nullable=False)

    # Relationships
    # product - from Product class

    @classmethod
    def from_url(cls, build_url):
        """Get a Build given its API URL.

        Parameters
        ----------
        build_url : `str`
            API URL of the build. This is the same as `Build.get_url`.

        Returns
        -------
        build : `Build`
            The Build instance corresponding to the URL.
        """
        # Get new Build ID from the build resource's URL
        build_endpoint, build_args = split_url(build_url)
        if build_endpoint != 'api.get_build' or 'id' not in build_args:
            raise ValidationError('Invalid build_url: {}'.format(build_url))
        build = cls.query.get(build_args['id'])
        if build is None:
            raise ValidationError('Invalid build_url: ' + build_url)

        return build

    @property
    def bucket_root_dirname(self):
        """Directory in the bucket where the build is located."""
        return '/'.join((self.product.slug, 'builds', self.slug))

    @property
    def published_url(self):
        """URL where this build is published to the end-user."""
        parts = ('https',
                 self.product.domain,
                 '/builds/{0}'.format(self.slug),
                 '', '', '')
        return urllib.parse.urlunparse(parts)

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
            'github_requester': self.github_requester,
            'published_url': self.published_url,
            'surrogate_key': self.surrogate_key
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

        validate_path_slug(self.slug)

        self.date_created = datetime.now()

        return self

    def patch_data(self, data):
        """Modify build via PATCH.

        Only allowed modification is to set 'uploaded' field to True to
        acknowledge a build upload to the bucket.
        """
        if 'uploaded' in data:
            if data['uploaded'] is True:
                self.register_uploaded_build()

    def register_uploaded_build(self):
        """Hook for when a build has been uploaded."""
        self.uploaded = True

        editions = Edition.query.autoflush(False)\
            .filter(Edition.product == self.product)\
            .all()

        for edition in editions:
            if edition.should_rebuild(build=self):
                edition.rebuild(build=self)

    def deprecate_build(self):
        """Trigger a build deprecation.

        Sets the `date_ended` field.
        """
        self.date_ended = datetime.now()


class EditionMode(object):
    """Definitions for `Edition.mode`.

    These modes determine how an edition should be updated with new builds.
    """

    _modes = {
        'git_refs': {
            'id': 1,
            'doc': ('Default tracking mode where an edition tracks an array '
                    'of Git refs. This is the default mode if Edition.mode '
                    'is None.')
        },
        'lsst_doc': {
            'id': 2,
            'doc': ('LSST document-specific tracking mode where an edition '
                    'publishes the most recent vN.M tag.')
        }
    }

    _reverse_map = {mode['id']: mode_name
                    for mode_name, mode in _modes.items()}

    @staticmethod
    def name_to_id(mode):
        """Convert a mode name (string used by the web API) to a mode ID
        (integer) used by the DB.

        Parameters
        ----------
        mode : `str`
            Mode name.

        Returns
        -------
        mode_id : `int`
            Mode ID.

        Raises
        ------
        ValidationError
            Raised if ``mode`` is unknown.
        """
        try:
            mode_id = EditionMode._modes[mode]['id']
        except KeyError:
            message = 'Edition mode {!r} unknown. Valid values are {!r}'
            raise ValidationError(message.format(mode, EditionMode.keys()))
        return mode_id

    @staticmethod
    def id_to_name(mode_id):
        """Convert a mode ID (integer used by the DB) to a name used by the
        web API.

        Parameters
        ----------
        mode_id : `int`
            Mode ID.

        Returns
        -------
        mode : `str`
            Mode name.

        Raises
        ------
        ValidationError
            Raised if ``mode`` is unknown.
        """
        try:
            mode = EditionMode._reverse_map[mode_id]
        except KeyError:
            message = 'Edition mode ID {!r} unknown. Valid values are {!r}'
            raise ValidationError(
                message.format(mode_id, EditionMode._reverse_map.keys()))
        return mode


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
    # Algorithm for updating this edition with a new build.
    # Integer values are defined in EditionMode.
    # Null is the default mode: EditionMode.GIT_REFS.
    mode = db.Column(db.Integer, nullable=True)
    # What product Git refs this Edition tracks and publishes
    tracked_refs = db.Column(MutableList.as_mutable(JSONEncodedVARCHAR(2048)))
    # url-safe slug for edition
    slug = db.Column(db.Unicode(255), nullable=False)
    # Human-readable title for edition
    title = db.Column(db.Unicode(256), nullable=False)
    # Date when this edition was initially created
    date_created = db.Column(db.DateTime, default=datetime.now(),
                             nullable=False)
    # Date when the edition was updated (e.g., new build)
    date_rebuilt = db.Column(db.DateTime, default=datetime.now(),
                             nullable=False)
    # set only when the Edition is deprecated (ready for deletion)
    date_ended = db.Column(db.DateTime, nullable=True)
    # The surrogate-key header for Fastly (quick purges); 32-char hex
    surrogate_key = db.Column(db.String(32))

    # Relationships
    build = db.relationship('Build', uselist=False)  # one-to-one

    @classmethod
    def from_url(cls, edition_url):
        """Get an Edition given its API URL.

        Parameters
        ----------
        edition_url : `str`
            API URL of the edition. This is the same as `Edition.get_url`.

        Returns
        -------
        edition : `Edition`
            The `Edition` instance corresponding to the URL.
        """
        logger = get_logger(__name__)

        # Get new Product ID from the product resource's URL
        edition_endpoint, endpoint_args = split_url(edition_url)
        if edition_endpoint != 'api.get_edition' or 'id' not in endpoint_args:
            logger.debug('Invalid edition_url',
                         edition_endpoint=edition_endpoint,
                         endpoint_args=endpoint_args)
            raise ValidationError('Invalid edition_url: {}'
                                  .format(edition_url))
        edition = cls.query.get(endpoint_args['id'])

        return edition

    @property
    def bucket_root_dirname(self):
        """Directory in the bucket where the edition is located."""
        return '/'.join((self.product.slug, 'v', self.slug))

    @property
    def published_url(self):
        """URL where this edition is published to the end-user."""
        if self.slug == 'main':
            # Special case for main; published at product's root
            parts = ('https',
                     self.product.domain,
                     '', '', '', '')
        else:
            parts = ('https',
                     self.product.domain,
                     '/v/{0}'.format(self.slug),
                     '', '', '')
        return urllib.parse.urlunparse(parts)

    def get_url(self):
        """API URL for this entity."""
        return url_for('api.get_edition', id=self.id, _external=True)

    def export_data(self):
        """Export entity as JSON-compatible dict."""
        if self.build is not None:
            build_url = self.build.get_url()
        else:
            build_url = None

        return {
            'self_url': self.get_url(),
            'product_url': self.product.get_url(),
            'build_url': build_url,
            'mode': self.mode_name,
            'tracked_refs': self.tracked_refs,
            'slug': self.slug,
            'title': self.title,
            'published_url': self.published_url,
            'date_created': format_utc_datetime(self.date_created),
            'date_rebuilt': format_utc_datetime(self.date_rebuilt),
            'date_ended': format_utc_datetime(self.date_ended),
            'surrogate_key': self.surrogate_key,
            'pending_rebuild': self.pending_rebuild
        }

    def import_data(self, data):
        """Initialize the edition on POST.

        The Product is set on object initialization.
        """
        try:
            tracked_refs = data['tracked_refs']
            self.slug = data['slug']
            self.title = data['title']
        except KeyError as e:
            raise ValidationError('Invalid Edition: missing ' + e.args[0])

        if isinstance(tracked_refs, str):
            raise ValidationError('Invalid Edition: tracked_refs must be an '
                                  'array of strings')
        self.tracked_refs = tracked_refs

        if 'mode' in data:
            self.set_mode(data['mode'])
        else:
            # Set default
            self.set_mode(self.default_mode_name)

        # Validate the slug
        self._validate_slug(data['slug'])

        if self.surrogate_key is None:
            self.surrogate_key = uuid.uuid4().hex

        # Set initial build pointer
        if 'build_url' in data:
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

        if 'mode' in data:
            self.set_mode(data['mode'])

        if 'title' in data:
            self.title = data['title']

        if 'build_url' in data:
            self.rebuild(data['build_url'])

        if 'slug' in data:
            self.update_slug(data['slug'])

    def should_rebuild(self, build_url=None, build=None):
        """Determine whether the edition should be rebuilt to show a certain
        build given the tracking mode.

        Parameters
        ----------
        build_url : `str`, optional
            API URL of the build resource. Optional if ``build`` is provided
            instead.
        build : `Build`, optional
            `Build` object. Optional if ``build_url`` is provided instead.

        Returns
        -------
        decision : `bool`
            `True` if the edition should be rebuilt using this Build, or
            `False` otherwise.
        """
        if build is not None:
            candidate_build = build
        else:
            candidate_build = Build.from_url(build_url)

        # Prefilter
        if candidate_build.product != self.product:
            return False
        if candidate_build.uploaded is False:
            return False

        if self.mode == EditionMode.name_to_id('git_refs') \
                or self.mode is None:
            # Default tracking mode that follows an array of Git refs.
            if (candidate_build.product == self.product) \
                    and (candidate_build.git_refs == self.tracked_refs):
                return True

        elif self.mode == EditionMode.name_to_id('lsst_doc'):
            # LSST document tracking mode.

            # If the edition is unpublished or showing `master`, and the
            # build is tracking `master`, then allow this rebuild.
            # This is used in the period before a semantic version is
            # available.
            if candidate_build.git_refs[0] == 'master':
                if self.build_id is None or \
                        self.build.git_refs[0] == 'master':
                    return True

            # Does the build have the vN.M tag?
            try:
                candidate_version = LsstDocVersionTag(
                    candidate_build.git_refs[0])
            except ValueError:
                return False

            # Does the edition's current build have a LSST document version
            # as its Git ref?
            try:
                current_version = LsstDocVersionTag(
                    self.build.git_refs[0])
            except ValueError:
                # Not currently tracking a version, so automatically accept
                # the candidate.
                return True

            # Is the candidate version newer than the existing version?
            if candidate_version >= current_version:
                # Accept >= in case a replacement of the same version is
                # somehow required.
                return True

        else:
            # Mode is unknown
            return False

    def rebuild(self, build_url=None, build=None):
        """Modify the build this edition points to.

        Parameters
        ----------
        build_url : `str`, optional
            API URL of the build resource. Optional if ``build`` is provided
            instead.
        build : `Build`, optional
            `Build` object. Optional if ``build_url`` is provided instead.

        Notes
        -----
        This method accomplishes the following:

        1. Gets surrogate key from existing build used by edition
        2. Gets and validates new build
        3. Copys new build into edition's directory in S3 bucket
        4. Purge Fastly's cache for this edition.
        """
        FASTLY_SERVICE_ID = current_app.config['FASTLY_SERVICE_ID']
        FASTLY_KEY = current_app.config['FASTLY_KEY']
        AWS_ID = current_app.config['AWS_ID']
        AWS_SECRET = current_app.config['AWS_SECRET']

        # Create a surrogate-key for the edition if it doesn't have one
        if self.surrogate_key is None:
            self.surrogate_key = uuid.uuid4().hex

        # Get and validate the build
        if build is not None:
            self.build = build
        else:
            self.build = Build.from_url(build_url)

        if self.build.uploaded is False:
            raise ValidationError('Build has not been uploaded: ' + build_url)
        if self.build.date_ended is not None:
            raise ValidationError('Build was deprecated: ' + build_url)

        if AWS_ID is not None and AWS_SECRET is not None:
            s3.copy_directory(
                bucket_name=self.product.bucket_name,
                src_path=self.build.bucket_root_dirname,
                dest_path=self.bucket_root_dirname,
                aws_access_key_id=AWS_ID,
                aws_secret_access_key=AWS_SECRET,
                surrogate_key=self.surrogate_key,
                # Force Fastly to cache the edition for 1 year
                surrogate_control='max-age=31536000',
                # Force browsers to revalidate their local cache using ETags.
                cache_control='no-cache')

        if FASTLY_SERVICE_ID is not None and FASTLY_KEY is not None:
            fastly_service = fastly.FastlyService(
                FASTLY_SERVICE_ID,
                FASTLY_KEY)
            fastly_service.purge_key(self.surrogate_key)

        # TODO start a job that will warm the Fastly cache with the new edition

        self.date_rebuilt = datetime.now()

    def set_mode(self, mode):
        """Set the ``mode`` attribute.

        Parameters
        ----------
        mode : `int`
            Mode identifier. Validated to be one in `EditionMode`.

        Raises
        ------
        ValidationError
            Raised if `mode` is unknown.
        """
        self.mode = EditionMode.name_to_id(mode)

        # TODO set tracked_refs to None if mode is LSST_DOC.

    @property
    def default_mode_name(self):
        """Default tracking mode name if ``Edition.mode`` is `None` (`str`).
        """
        return 'git_refs'

    @property
    def default_mode_id(self):
        """Default tracking mode ID if ``Edition.mode`` is `None` (`int`).
        """
        return EditionMode.name_to_id(self.default_mode_name)

    @property
    def mode_name(self):
        """Name of the mode (`str`).

        See also
        --------
        EditionMode
        """
        if self.mode is not None:
            return EditionMode.id_to_name(self.mode)
        else:
            return self.default_mode_name

    def update_slug(self, new_slug):
        """Update the edition's slug by migrating files on S3."""
        # Check that this slug does not already exist
        self._validate_slug(new_slug)

        old_bucket_root_dir = self.bucket_root_dirname

        self.slug = new_slug
        new_bucket_root_dir = self.bucket_root_dirname

        AWS_ID = current_app.config['AWS_ID']
        AWS_SECRET = current_app.config['AWS_SECRET']
        if AWS_ID is not None and AWS_SECRET is not None \
                and self.build is not None:
            s3.copy_directory(self.product.bucket_name,
                              old_bucket_root_dir, new_bucket_root_dir,
                              AWS_ID, AWS_SECRET,
                              surrogate_key=self.surrogate_key)
            s3.delete_directory(self.product.bucket_name,
                                old_bucket_root_dir,
                                AWS_ID, AWS_SECRET)

    def _validate_slug(self, slug):
        """Ensure that the slug is both unique to the product and meets the
        slug format regex.

        Raises
        ------
        ValidationError
        """
        # Check against slug regex
        validate_path_slug(slug)
        print('Valid slug')

        # Check uniqueness
        existing_count = Edition.query.autoflush(False)\
            .filter(Edition.product == self.product)\
            .filter(Edition.slug == slug)\
            .count()
        if existing_count > 0:
            raise ValidationError(
                'Invalid edition: slug ({0}) already exists'.format(slug))

        return True

    def deprecate(self):
        """Deprecate the Edition; sets the `date_ended` field."""
        self.date_ended = datetime.now()
