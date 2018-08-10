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
from .exceptions import ValidationError
from .editiontracking import EditionTrackingModes
from .utils import (split_url, format_utc_datetime, JSONEncodedVARCHAR,
                    MutableList, validate_product_slug, validate_path_slug)
from .taskrunner import append_task_to_chain


db = SQLAlchemy()
"""Database connection.

This is initialized in `keeper.appfactory.create_flask_app`.
"""

migrate = Migrate()
"""Flask-SQLAlchemy extension instance.

This is initialized in `keeper.appfactory.create_flask_app`.
"""

edition_tracking_modes = EditionTrackingModes()
"""Tracking modes for editions.
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
    :meth:`User.full_permissions` helper method::

        p = Permission
        user = User(username='admin-user',
                    permission=p.full_permissions())

    See :class:`User.has_permission` for how to use these permission
    bits to test user authorization.
    """

    ADMIN_USER = 0b1
    """Permission to create a new API user, view API users, and modify API user
    permissions.
    """

    ADMIN_PRODUCT = 0b10
    """Permission to add, modify and deprecate Products.
    """

    ADMIN_EDITION = 0b100
    """Permission to add, modify and deprecate Editions.
    """

    UPLOAD_BUILD = 0b1000
    """Permission to create a new Build.
    """

    DEPRECATE_BUILD = 0b10000
    """Permission to deprecate a Build.
    """

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
    """DB model for authenticated API users.
    """

    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    """Primary key for this User.
    """

    username = db.Column(db.Unicode(255), index=True, unique=True)
    """Username (must be unique).
    """

    password_hash = db.Column(db.String(128))
    """Password hash.
    """

    permissions = db.Column(db.Integer)
    """Permissions for this user, as a bit.

    See also
    --------
    Permission
    """

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
    """Primary key for this product.
    """

    slug = db.Column(db.Unicode(255), nullable=False, unique=True)
    """URL/path-safe identifier for this product (unique).
    """

    doc_repo = db.Column(db.Unicode(255), nullable=False)
    """URL of the Git documentation repo (i.e., on GitHub).
    """

    title = db.Column(db.Unicode(255), nullable=False)
    """Title of this product.
    """

    root_domain = db.Column(db.Unicode(255), nullable=False)
    """Root domain name serving docs (e.g., lsst.io).
    """

    root_fastly_domain = db.Column(db.Unicode(255), nullable=False)
    """Fastly CDN domain name (without doc's domain prepended).
    """

    bucket_name = db.Column(db.Unicode(255), nullable=True)
    """Name of the S3 bucket hosting builds.
    """

    surrogate_key = db.Column(db.String(32))
    """surrogate_key for Fastly quick purges of dashboards.

    Editions and Builds have independent surrogate keys.
    """

    builds = db.relationship('Build', backref='product', lazy='dynamic')
    """One-to-many relationship to all `Build` objects related to this Product.
    """

    editions = db.relationship('Edition', backref='product', lazy='dynamic')
    """One-to-many relationship to all `Edition` objects related to this
    Product.
    """

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
        """URL where this product is published to the end-user.
        """
        parts = ('https', self.domain, '', '', '', '')
        return urllib.parse.urlunparse(parts)

    def get_url(self):
        """API URL for this entity.
        """
        return url_for('api.get_product', slug=self.slug, _external=True)

    def export_data(self):
        """Export entity as JSON-compatible dict.
        """
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
        """Convert a dict `data` into a table row.
        """
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
    """Primary key of the build.
    """

    product_id = db.Column(db.Integer, db.ForeignKey('products.id'),
                           index=True)
    """ID of the `Product` this `Build` belongs to.
    """

    slug = db.Column(db.Unicode(255), nullable=False)
    """URL-safe slug for this build.

    This slug is also used as a pseudo-POSIX directory prefix in the S3 bucket.
    """

    date_created = db.Column(db.DateTime, default=datetime.now(),
                             nullable=False)
    """DateTime when this build was created.
    """

    # set only when the build is deprecated (ready for deletion)
    date_ended = db.Column(db.DateTime, nullable=True)
    """DateTime when this build was marked as deprecated (ready for deletion).

    This field is `None` when the Build is **not** deprecated.
    """

    git_refs = db.Column(MutableList.as_mutable(JSONEncodedVARCHAR(2048)))
    """List of git ref strings that describe the version of the content.

    A git ref is typically a branch or tag name. For single Git repository
    documentation projects this field is a list with a single item. Multi-
    repository products may have multiple git refs.

    This field is encoded as JSON (`JSONEndedVARCHAR`).
    """

    github_requester = db.Column(db.Unicode(255), nullable=True)
    """github handle of person requesting the build (optional).
    """

    uploaded = db.Column(db.Boolean, default=False)
    """Flag to indicate the doc has been uploaded to S3.
    """

    surrogate_key = db.Column(db.String(32), nullable=False)
    """surrogate-key header for Fastly (quick purges); 32-char hex.
    """

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
        """Directory in the bucket where the build is located.
        """
        return '/'.join((self.product.slug, 'builds', self.slug))

    @property
    def published_url(self):
        """URL where this build is published to the end-user.
        """
        parts = ('https',
                 self.product.domain,
                 '/builds/{0}'.format(self.slug),
                 '', '', '')
        return urllib.parse.urlunparse(parts)

    def get_url(self):
        """API URL for this entity.
        """
        return url_for('api.get_build', id=self.id, _external=True)

    def export_data(self):
        """Export entity as JSON-compatible dict.
        """
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
        """Convert a dict `data` into a table row.
        """
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
        """Hook for when a build has been uploaded.
        """
        self.uploaded = True

        editions = Edition.query.autoflush(False)\
            .filter(Edition.product == self.product)\
            .all()

        for edition in editions:
            if edition.should_rebuild(build=self):
                edition.set_pending_rebuild(build=self)

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
    """Primary key of this Edition.
    """

    product_id = db.Column(db.Integer, db.ForeignKey('products.id'),
                           index=True)
    """ID of the product being used by this Edition.
    """

    build_id = db.Column(db.Integer, db.ForeignKey('builds.id'),
                         index=True)
    """ID of the build being used by this edition.

    See also
    --------
    Edition.build
    """

    mode = db.Column(db.Integer, nullable=True)
    """Tracking mode

    Tracking modes are algorithms for updating this Edition when a new build
    appears for a product.

    Integer values are defined in EditionTrackingModes. Null is the default
    mode: ``git_refs``.
    """

    tracked_refs = db.Column(MutableList.as_mutable(JSONEncodedVARCHAR(2048)))
    """The list of Git refs this Edition tracks and publishes if the tracking
    mode is ``git_refs``.

    For other tracking modes, this field may be `None`.
    """

    slug = db.Column(db.Unicode(255), nullable=False)
    """URL-safe slug for edition.
    """

    title = db.Column(db.Unicode(256), nullable=False)
    """Human-readable title for edition.
    """

    date_created = db.Column(db.DateTime, default=datetime.now(),
                             nullable=False)
    """DateTime when this edition was initially created.
    """

    date_rebuilt = db.Column(db.DateTime, default=datetime.now(),
                             nullable=False)
    """DateTime when the Edition was last rebuild.
    """

    date_ended = db.Column(db.DateTime, nullable=True)
    """DateTime when the Edition is deprecated (ready for deletion). Null
    otherwise.
    """

    surrogate_key = db.Column(db.String(32))
    """surrogate-key header for Fastly (quick purges); 32-char hex.
    """

    pending_rebuild = db.Column(db.Boolean, default=False, nullable=False)
    """Flag indicating if a rebuild is pending work by the rebuild task.
    """

    # Relationships
    build = db.relationship('Build', uselist=False)
    """One-to-one relationship with the `Build` resource.
    """

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
        """Directory in the bucket where the edition is located.
        """
        return '/'.join((self.product.slug, 'v', self.slug))

    @property
    def published_url(self):
        """URL where this edition is published to the end-user.
        """
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
        """API URL for this entity.
        """
        return url_for('api.get_edition', id=self.id, _external=True)

    def export_data(self):
        """Export entity as JSON-compatible dict.
        """
        if self.build is not None:
            build_url = self.build.get_url()
        else:
            build_url = None

        data = {
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

        if self.mode_name != 'git_refs':
            # Force tracked_refs to None/null if it is not applicable.
            data['tracked_refs'] = None
        else:
            data['tracked_refs'] = self.tracked_refs

        return data

    def import_data(self, data):
        """Initialize the edition on POST.

        The Product is set on object initialization.
        """
        # Set up the edition's slug and title (either automatic or manually
        # set)
        if 'autoincrement' in data and data['autoincrement']:
            self.slug = self._compute_autoincremented_slug()
            self.title = self.slug
        else:
            try:
                self.slug = data['slug']
                self.title = data['title']
            except KeyError as e:
                raise ValidationError('Invalid Product: missing ' + e.args[0])
        self._validate_slug(self.slug)

        # Set up the edition's build tracking mode
        if 'mode' in data:
            self.set_mode(data['mode'])
        else:
            # Set default
            self.set_mode(self.default_mode_name)

        # git_refs is only required for git_refs tracking mode
        if self.mode == edition_tracking_modes.name_to_id('git_refs'):
            try:
                tracked_refs = data['tracked_refs']
            except KeyError as e:
                raise ValidationError('Invalid Edition: missing ' + e.args[0])

            if isinstance(tracked_refs, str):
                raise ValidationError('Invalid Edition: tracked_refs must be '
                                      'an array of strings')

            self.tracked_refs = tracked_refs

        if self.surrogate_key is None:
            self.surrogate_key = uuid.uuid4().hex

        # Indicate rebuild it needed
        if 'build_url' in data:
            self.set_pending_rebuild(build_url=data['build_url'])

        self.date_created = datetime.now()

        return self

    def patch_data(self, data):
        """Partial update of the Edition.
        """
        logger = get_logger(__name__)

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
            self.set_pending_rebuild(build_url=data['build_url'])

        if 'slug' in data:
            self.update_slug(data['slug'])

        if 'pending_rebuild' in data:
            logger.warning('Manual reset of Edition.pending_rebuild',
                           edition=self.get_url(),
                           prev_pending_rebuild=self.pending_rebuild,
                           new_pending_rebuild=data['pending_rebuild'])
            self.pending_rebuild = data['pending_rebuild']

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
        logger = get_logger(__name__)

        logger.debug('Edition {!r} in should_rebuild'.format(self.get_url()))

        if build is not None:
            candidate_build = build
        else:
            candidate_build = Build.from_url(build_url)

        # Prefilter
        if candidate_build.product != self.product:
            return False
        if candidate_build.uploaded is False:
            return False

        try:
            tracking_mode = edition_tracking_modes[self.mode]
        except (KeyError, ValidationError):

            tracking_mode = edition_tracking_modes[self.default_mode_id]
            logger.warning('Edition {!r} has an unknown tracking'
                           'mode'.format(self.get_url()))

        return tracking_mode.should_update(self, candidate_build)

    def set_pending_rebuild(self, build_url=None, build=None):
        """Update the build this edition is declared to point to and set it
        to a pending state.

        The caller must separately initial a
        `keeper.tasks.editionrebuild.rebuild_edition` task to implement the
        declared change (after this DB change is committed).

        Parameters
        ----------
        build_url : `str`, optional
            API URL of the build resource. Optional if ``build`` is provided
            instead.
        build : `Build`, optional
            `Build` object. Optional if ``build_url`` is provided instead.

        See also
        --------
        Edition.set_rebuild_complete

        Notes
        -----
        This method does the following things:

        1. Sets the Edition's surrogate-key for Fastly (for forward migration
           purposes).

        2. Validates the state

           - The edition cannot have an already-pending rebuild.
           - The build cannot be deprecated.
           - The build must be uploaded.

        3. Sets the desired state (update the build reference and sets
           ``pending_rebuild`` field to `True`).

        The ``rebuild_edition`` celery task, separately, implements the rebuild
        and calls the `Edition.set_rebuild_complete` method to confirm that
        the rebuild is complete.
        """
        if build is None:
            build = Build.from_url(build_url)

        # Create a surrogate-key for the edition if it doesn't have one
        if self.surrogate_key is None:
            self.surrogate_key = uuid.uuid4().hex

        # State validation
        if self.pending_rebuild:
            raise ValidationError(
                'This edition already has a pending rebuild, this request '
                'will not be accepted.')
        if build.uploaded is False:
            raise ValidationError('Build has not been uploaded: ' + build_url)
        if build.date_ended is not None:
            raise ValidationError('Build was deprecated: ' + build_url)

        # Set the desired state
        self.build = build
        self.pending_rebuild = True

        # Add the rebuild_edition task
        # Lazy load the task because it references the db/Edition model
        from .tasks.editionrebuild import rebuild_edition
        append_task_to_chain(rebuild_edition.si(self.get_url(), self.id))

    def set_rebuild_complete(self):
        """Confirm that the rebuild is complete and the declared state is
        correct.

        Notes
        -----
        This method does two things:

        1. Sets the ``pending_rebuild`` field to False.
        2. Updates the ``date_rebuild`` field's timestamp to now.

        See also
        --------
        Edition.set_pending_rebuild
        """
        self.pending_rebuild = False
        self.date_rebuilt = datetime.now()

    def set_mode(self, mode):
        """Set the ``mode`` attribute.

        Parameters
        ----------
        mode : `int`
            Mode identifier. Validated to be one defined in
            `keeper.editiontracking.EditionTrackingModes`.

        Raises
        ------
        ValidationError
            Raised if `mode` is unknown.
        """
        self.mode = edition_tracking_modes.name_to_id(mode)

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
        return edition_tracking_modes.name_to_id(self.default_mode_name)

    @property
    def mode_name(self):
        """Name of the mode (`str`).

        See also
        --------
        EditionMode
        """
        if self.mode is not None:
            return edition_tracking_modes.id_to_name(self.mode)
        else:
            return self.default_mode_name

    def update_slug(self, new_slug):
        """Update the edition's slug by migrating files on S3.
        """
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

    def _compute_autoincremented_slug(self):
        """Compute an autoincremented integer slug for this edition.

        Returns
        -------
        slug : `str`
            The next available integer slug for this Edition.

        Notes
        -----
        This uses the following algorithm:

        1. Queries all slugs associated with this Edition.
        2. Converts eligible slugs to integers.
        3. Computes the maximum existing integer slug.
        4. Returns the 1+the maximum existing slug, or 1.
        """
        # Find existing edition slugs
        slugs = db.session.query(Edition.slug)\
            .autoflush(False)\
            .filter(Edition.product == self.product)\
            .all()

        # Convert to integers
        integer_slugs = []
        for slug in slugs:
            try:
                # slugs is actual a sequence of result tuples, hence getting
                # the first item.
                int_slug = int(slug[0])
            except ValueError:
                # not an integer-like slug, so we can ignore it
                continue
            integer_slugs.append(int_slug)

        if len(integer_slugs) == 0:
            return '1'
        else:
            return str(max(integer_slugs) + 1)

    def _validate_slug(self, slug):
        """Ensure that the slug is both unique to the product and meets the
        slug format regex.

        Raises
        ------
        ValidationError
        """
        # Check against slug regex
        validate_path_slug(slug)

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
        """Deprecate the Edition; sets the `date_ended` field.
        """
        self.date_ended = datetime.now()
