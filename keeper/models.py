"""Flask-SQLAlchemy-based database ORM models.

Copyright 2016 AURA/LSST.
Copyright 2014 Miguel Grinberg.
"""

from __future__ import annotations

import enum
import urllib.parse
import uuid
from datetime import datetime
from typing import Any, List, Optional, Type, Union

from cryptography.fernet import Fernet
from flask import current_app
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from pydantic import SecretStr
from structlog import get_logger
from werkzeug.security import check_password_hash, generate_password_hash

from keeper.editiontracking import EditionTrackingModes
from keeper.exceptions import ValidationError
from keeper.utils import JSONEncodedVARCHAR, MutableList, validate_path_slug

__all__ = [
    "db",
    "migrate",
    "edition_tracking_modes",
    "Permission",
    "User",
    "Organization",
    "DashboardTemplate",
    "Tag",
    "Product",
    "product_tags",
    "Build",
    "Edition",
]

db = SQLAlchemy()
"""Database connection.

This is initialized in `keeper.appfactory.create_flask_app`.
"""

migrate = Migrate()
"""Flask-SQLAlchemy extension instance.

This is initialized in `keeper.appfactory.create_flask_app`.
"""

edition_tracking_modes = EditionTrackingModes()
"""Tracking modes for editions."""


class IntEnum(db.TypeDecorator):  # type: ignore
    """A custom column type that persists enums as their value, rather than
    the name.

    Notes
    -----
    This code is based on
    https://michaelcho.me/article/using-python-enums-in-sqlalchemy-models
    """

    impl = db.Integer

    def __init__(
        self, enumtype: Type[enum.IntEnum], *args: Any, **kwargs: Any
    ) -> None:
        super().__init__(*args, **kwargs)
        self._enumtype = enumtype

    def process_bind_param(
        self, value: Union[int, enum.IntEnum], dialect: Any
    ) -> int:
        if isinstance(value, enum.IntEnum):
            return value.value
        else:
            return value

    def process_result_value(self, value: int, dialect: Any) -> enum.IntEnum:
        return self._enumtype(value)


class Permission:
    """User permission definitions.

    These permissions can be added to the ``permissions`` column of a
    `User`. For example, to give a user permission to both
    administer products *and* editions::

        p = Permission
        user = User(username='test-user',
                    permissions=p.ADMIN_PRODUCT | p.ADMIN_EDITION)

    You can give a user permission to do everything with the
    `User.full_permissions` helper method::

        p = Permission
        user = User(username='admin-user',
                    permission=p.full_permissions())

    See `User.has_permission` for how to use these permission
    bits to test user authorization.
    """

    ADMIN_USER = 0b1
    """Permission to create a new API user, view API users, and modify API user
    permissions.
    """

    ADMIN_PRODUCT = 0b10
    """Permission to add, modify and deprecate Products."""

    ADMIN_EDITION = 0b100
    """Permission to add, modify and deprecate Editions."""

    UPLOAD_BUILD = 0b1000
    """Permission to create a new Build."""

    DEPRECATE_BUILD = 0b10000
    """Permission to deprecate a Build."""

    @classmethod
    def full_permissions(self) -> int:
        """Helper method to create a bit mask with all permissions enabled.

        Returns
        -------
        permissions : int
            Bit mask with all permissions enabled.
        """
        return (
            self.ADMIN_USER
            | self.ADMIN_PRODUCT
            | self.ADMIN_EDITION
            | self.UPLOAD_BUILD
            | self.DEPRECATE_BUILD
        )


class User(db.Model):  # type: ignore
    """DB model for authenticated API users."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    """Primary key for this User."""

    username = db.Column(db.Unicode(255), index=True, unique=True)
    """Username (must be unique)."""

    password_hash = db.Column(db.String(128))
    """Password hash."""

    permissions = db.Column(db.Integer)
    """Permissions for this user, as a bit.

    See also
    --------
    Permission
    """

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def generate_auth_token(self, expires_in: int = 3600) -> str:
        s = Serializer(current_app.config["SECRET_KEY"], expires_in=expires_in)
        return s.dumps({"id": self.id}).decode("utf-8")

    @staticmethod
    def verify_auth_token(token: str) -> Optional["User"]:
        s = Serializer(current_app.config["SECRET_KEY"])
        try:
            data = s.loads(token)
        except Exception:
            return None
        return User.query.get(data["id"])

    def has_permission(self, permissions: int) -> bool:
        """Verify that a user has a given set of permissions.

        Permissions are defined in the `Permission` class. To check
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


class DashboardTemplate(db.Model):  # type: ignore
    """DB model for an edition dashboard template."""

    __tablename__ = "dashboardtemplates"

    id = db.Column(db.Integer, primary_key=True)
    """Primary key for this dashboard template."""

    organization_id = db.Column(db.Integer, db.ForeignKey("organizations.id"))
    """ID of the organization associated with this template."""

    comment = db.Column(db.UnicodeText(), nullable=True)
    """A note about this dashboard template."""

    bucket_prefix = db.Column(db.Unicode(255), nullable=False, unique=True)
    """S3 bucket prefix where all assets related to this template are
    persisted.
    """

    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    """ID of user who created this template."""

    date_created = db.Column(db.DateTime, default=datetime.now, nullable=False)
    """DateTime when this template was created."""

    deleted_by_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=True
    )
    """ID of user who deleted this template."""

    date_deleted = db.Column(db.DateTime, default=None, nullable=True)
    """DateTime when this template was deleted (or null if the template has
    not been deleted.
    """

    created_by = db.relationship(
        "User",
        primaryjoin="DashboardTemplate.created_by_id == User.id",
    )
    """User who created this template."""

    deleted_by = db.relationship(
        "User", primaryjoin="DashboardTemplate.deleted_by_id == User.id"
    )
    """User who deleted this template."""

    organization = db.relationship(
        "Organization",
        back_populates="dashboard_templates",
        foreign_keys=[organization_id],
    )


class OrganizationLayoutMode(enum.IntEnum):
    """Layout mode (enum) for organizations."""

    subdomain = 1
    """Layout based on a subdomain for each project."""

    path = 2
    """Layout based on a path prefix for each project."""


class Organization(db.Model):  # type: ignore
    """DB model for an organization resource.

    Organizations own products (`Product`).
    """

    __tablename__ = "organizations"

    id = db.Column(db.Integer, primary_key=True)
    """Primary key for this organization."""

    default_dashboard_template_id = db.Column(db.Integer, nullable=True)
    """ID of the organization's default dashboard template
    (`DashboardTemplate`), if one is set.
    """

    slug = db.Column(db.Unicode(255), nullable=False, unique=True)
    """URL-safe identifier for this organization (unique)."""

    title = db.Column(db.Unicode(255), nullable=False)
    """Presentational title for this organization."""

    layout = db.Column(
        IntEnum(OrganizationLayoutMode),
        nullable=False,
        default=OrganizationLayoutMode.subdomain,
    )
    """Layout mode.

    See also
    --------
    OrganizationLayoutMode
    """

    fastly_support = db.Column(db.Boolean, nullable=False, default=True)
    """Flag Fastly CDN support."""

    root_domain = db.Column(db.Unicode(255), nullable=False)
    """Root domain name serving docs (e.g., lsst.io)."""

    root_path_prefix = db.Column(db.Unicode(255), nullable=False, default="/")
    """Root path prefix for serving products."""

    fastly_domain = db.Column(db.Unicode(255), nullable=True)
    """Fastly CDN domain name."""

    fastly_encrypted_api_key = db.Column(db.LargeBinary, nullable=True)
    """Fastly API key for this organization.

    The key is persisted as a fernet token.
    """

    fastly_service_id = db.Column(db.Unicode(255), nullable=True)
    """Fastly service ID."""

    bucket_name = db.Column(db.Unicode(255), nullable=True)
    """Name of the S3 bucket hosting builds."""

    # FIXME nullable for migration
    aws_id = db.Column(db.Unicode(255), nullable=True)
    """The AWS key identity (this replaced the Kubernetes configuration-based
    key.
    """

    # FIXME nullable for migration
    aws_encrypted_secret_key = db.Column(db.LargeBinary, nullable=True)
    """The AWS secret key."""

    # FIXME nullable for migration
    aws_region = db.Column(db.Unicode(255), nullable=True, default="us-east-1")
    """The AWS region of the S3 bucket."""

    # FIXME nullable for migration
    bucket_public_read = db.Column(db.Boolean, nullable=True, default=False)
    """If True, objects in the S3 bucket will have the ``public-read`` ACL.

    For objects using a proxy, this can be False.
    """

    products = db.relationship(
        "Product", back_populates="organization", lazy="dynamic"
    )
    """Relationship to `Product` objects owned by this organization."""

    tags = db.relationship("Tag", backref="organization", lazy="dynamic")
    """One-to-many relationship to all `Tag` objects related to this
    organization.
    """

    dashboard_templates = db.relationship(
        DashboardTemplate,
        primaryjoin=id == DashboardTemplate.organization_id,
        back_populates="organization",
    )

    def get_aws_region(self) -> str:
        """Get the AWS region (adapter while column is nullable for
        migration).
        """
        if self.aws_region is None:
            return "us-east-1"
        else:
            return self.aws_region

    def get_bucket_public_read(self) -> bool:
        """Get the S3 public public-read ACL configuration (adapter while
        column is nullable for migration.
        """
        if self.bucket_public_read is None:
            return False
        else:
            return self.bucket_public_read

    def set_fastly_api_key(self, api_key: Optional[SecretStr]) -> None:
        """Encrypt and set the Fastly API key."""
        if api_key is None:
            return
        self.fastly_encrypted_api_key = self._encrypt_secret_str(api_key)

    def get_fastly_api_key(self) -> Optional[SecretStr]:
        """Get the decrypted Fastly API key."""
        encrypted_key = self.fastly_encrypted_api_key
        if encrypted_key is None:
            return None
        return self._decrypt_to_secret_str(encrypted_key)

    def set_aws_secret_key(self, secret_key: Optional[SecretStr]) -> None:
        """Encrypt and set the AWS secret key."""
        if secret_key is None:
            return
        self.aws_encrypted_secret_key = self._encrypt_secret_str(secret_key)

    def get_aws_secret_key(self) -> Optional[SecretStr]:
        """Get the decrypted Fastly API key."""
        encrypted_key = self.aws_encrypted_secret_key
        if encrypted_key is None:
            return None
        return self._decrypt_to_secret_str(encrypted_key)

    def _encrypt_secret_str(self, secret: SecretStr) -> bytes:
        fernet_key = current_app.config["FERNET_KEY"]
        f = Fernet(fernet_key)
        token = f.encrypt(secret.get_secret_value().encode("utf-8"))
        return token

    def _decrypt_to_secret_str(self, token: bytes) -> SecretStr:
        fernet_key = current_app.config["FERNET_KEY"]
        f = Fernet(fernet_key)
        return SecretStr(f.decrypt(token).decode("utf-8"))


product_tags = db.Table(
    "producttags",
    db.Column(
        "tag_id", db.Integer, db.ForeignKey("tags.id"), primary_key=True
    ),
    db.Column(
        "product_id",
        db.Integer,
        db.ForeignKey("products.id"),
        primary_key=True,
    ),
)
"""A table that associates the `Product` and `Tag` models."""


class Tag(db.Model):  # type: ignore
    """DB model for tags in an `Organization`."""

    __tablename__ = "tags"

    __table_args__ = (
        db.UniqueConstraint("slug", "organization_id"),
        db.UniqueConstraint("title", "organization_id"),
    )

    id = db.Column(db.Integer, primary_key=True)
    """Primary key for this tag."""

    organization_id = db.Column(
        db.Integer, db.ForeignKey("organizations.id"), index=True
    )
    """ID of the organization that this tag belongs to."""

    slug = db.Column(
        db.Unicode(255),
        nullable=False,
    )
    """URL-safe identifier for this tag."""

    title = db.Column(
        db.Unicode(255),
        nullable=False,
    )
    """Presentational title or label for this tag."""

    comment = db.Column(db.UnicodeText(), nullable=True)
    """A note about this tag."""

    products = db.relationship(
        "Product", secondary=product_tags, back_populates="tags"
    )


class Product(db.Model):  # type: ignore
    """DB model for software products.

    A software product maps to a top-level Eups package and has a single
    product documentation repository associated with it.
    """

    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    """Primary key for this product."""

    organization_id = db.Column(
        db.Integer, db.ForeignKey("organizations.id"), nullable=False
    )
    """Foreign key of the organization that owns this product."""

    slug = db.Column(db.Unicode(255), nullable=False, unique=True)
    """URL/path-safe identifier for this product (unique)."""

    doc_repo = db.Column(db.Unicode(255), nullable=False)
    """URL of the Git documentation repo (i.e., on GitHub)."""

    title = db.Column(db.Unicode(255), nullable=False)
    """Title of this product."""

    root_domain = db.Column(db.Unicode(255), nullable=False)
    """Root domain name serving docs (e.g., lsst.io)."""

    root_fastly_domain = db.Column(db.Unicode(255), nullable=True)
    """Fastly CDN domain name (without doc's domain prepended)."""

    bucket_name = db.Column(db.Unicode(255), nullable=True)
    """Name of the S3 bucket hosting builds."""

    surrogate_key = db.Column(db.String(32))
    """surrogate_key for Fastly quick purges of dashboards.

    Editions and Builds have independent surrogate keys.
    """

    organization = db.relationship(
        "Organization",
        back_populates="products",
    )
    """Relationship to the parent organization."""

    builds = db.relationship("Build", backref="product", lazy="dynamic")
    """One-to-many relationship to all `Build` objects related to this Product.
    """

    editions = db.relationship("Edition", backref="product", lazy="dynamic")
    """One-to-many relationship to all `Edition` objects related to this
    Product.
    """

    tags = db.relationship(
        "Tag", secondary=product_tags, back_populates="products"
    )
    """Tags associated with this product."""

    @property
    def domain(self) -> str:
        """Domain where docs for this product are served from.

        (E.g. ``product.lsst.io`` if ``product`` is the slug and ``lsst.io``
        is the ``root_domain``.)
        """
        root_domain = self.organization.root_domain
        if self.organization.layout == OrganizationLayoutMode.subdomain:
            return ".".join((self.slug, self.root_domain))
        else:
            return root_domain

    @property
    def fastly_domain(self) -> Optional[str]:
        """Domain where Fastly serves content from for this product."""
        # Note that in non-ssl contexts fastly wants you to prepend the domain
        # to fastly's origin domain. However we don't do this with TLS.
        # return '.'.join((self.domain, self.root_fastly_domain))
        return self.root_fastly_domain

    @property
    def published_url(self) -> str:
        """URL where this product is published to the end-user.

        This domain *does not* end with a trailing /.
        """
        layout_mode = self.organization.layout
        if layout_mode == OrganizationLayoutMode.path:
            # Sub-path based layout
            if self.organization.root_path_prefix.endswith("/"):
                path = f"{self.organization.root_path_prefix}{self.slug}"
            else:
                path = f"{self.organization.root_path_prefix}/{self.slug}"
            parts = ("https", self.domain, path, "", "", "")
        else:
            # Domain-based layout
            parts = ("https", self.domain, "", "", "", "")
        return urllib.parse.urlunparse(parts)

    @property
    def default_edition(self) -> Edition:
        """Get the default edition."""
        edition = (
            Edition.query.join(Product, Product.id == Edition.product_id)
            .filter(Product.id == self.id)
            .filter(Edition.slug == "__main")
            .one_or_none()
        )
        if edition is None:
            raise RuntimeError(
                f"Cannot find default edition for product {self.slug} "
                f"in organization {self.organization.slug}"
            )
        return edition


class Build(db.Model):  # type: ignore
    """DB model for documentation builds."""

    __tablename__ = "builds"

    id = db.Column(db.Integer, primary_key=True)
    """Primary key of the build.
    """

    product_id = db.Column(
        db.Integer, db.ForeignKey("products.id"), index=True
    )
    """ID of the `Product` this `Build` belongs to.
    """

    slug = db.Column(db.Unicode(255), nullable=False)
    """URL-safe slug for this build.

    This slug is also used as a pseudo-POSIX directory prefix in the S3 bucket.
    """

    date_created = db.Column(db.DateTime, default=datetime.now, nullable=False)
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

    TODO: deprecate this field after deprecation of the v1 API to use git_ref
    (singular) exclusively.
    """

    git_ref = db.Column(db.Unicode(255), nullable=True)
    """The git ref that this build corresponds to.

    A git ref is typically a branch or tag name.

    This column replaces `git_refs`.
    """

    github_requester = db.Column(db.Unicode(255), nullable=True)
    """github handle of person requesting the build (optional).
    """

    uploaded_by_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=True
    )
    """Foreign key of the user that uploaded this build.

    This key is nullable during the transition.
    """

    uploaded = db.Column(db.Boolean, default=False)
    """Flag to indicate the doc has been uploaded to S3.
    """

    surrogate_key = db.Column(db.String(32), nullable=False)
    """surrogate-key header for Fastly (quick purges); 32-char hex.
    """

    # Relationships
    # product - from Product class

    uploaded_by = db.relationship(
        "User", primaryjoin="Build.uploaded_by_id == User.id"
    )
    """User who uploaded this build.
    """

    @property
    def bucket_name(self) -> str:
        """Name of the S3 bucket."""
        if self.product.organization.bucket_name is not None:
            return self.product.organization.bucket_name
        else:
            # Fallback for v1 set up
            return self.product.bucket_name

    @property
    def bucket_root_dirname(self) -> str:
        """Directory in the bucket where the build is located."""
        return "/".join((self.product.slug, "builds", self.slug))

    @property
    def published_url(self) -> str:
        """URL where this build is published to the end-user."""
        product_root_url = self.product.published_url
        if not product_root_url.endswith("/"):
            product_root_url = f"{product_root_url}/"
        return f"{product_root_url}builds/{self.slug}"

    def register_uploaded_build(self) -> None:
        """Register that a build is uploaded and determine what editions should
        be rebuilt with this build.
        """
        self.uploaded = True

    def get_tracking_editions(self) -> List[Edition]:
        """Get the editions that should rebuild to this build."""
        logger = get_logger(__name__)
        editions = (
            Edition.query.autoflush(False)
            .filter(Edition.product == self.product)
            .all()
        )
        logger.debug(
            "In get_tracking_editions found editions for product",
            count=len(editions),
            editions=str(editions),
        )

        return [
            edition
            for edition in editions
            if edition.should_rebuild(build=self)
        ]

    def deprecate_build(self) -> None:
        """Trigger a build deprecation.

        Sets the `date_ended` field.
        """
        self.date_ended = datetime.now()


class EditionKind(enum.IntEnum):
    """Classification of the edition.

    This classification is primarily used by edition dashboards.
    """

    main = 1
    """The main (default) edition."""

    release = 2
    """A release."""

    draft = 3
    """A draft edition (not a release)."""

    major = 4
    """An edition that tracks a major version (for the latest minor or
    patch version).
    """

    minor = 5
    """An edition that tracks a minor version (for the latest patch.)"""


class Edition(db.Model):  # type: ignore
    """DB model for Editions. Editions are fixed-location publications of the
    docs. Editions are updated by new builds; though not all builds are used
    by Editions.
    """

    __tablename__ = "editions"

    id = db.Column(db.Integer, primary_key=True)
    """Primary key of this Edition.
    """

    product_id = db.Column(
        db.Integer, db.ForeignKey("products.id"), index=True
    )
    """ID of the product being used by this Edition."""

    build_id = db.Column(db.Integer, db.ForeignKey("builds.id"), index=True)
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

    tracked_ref = db.Column(db.Unicode(255), nullable=True)
    """The Git ref this Edition tracks and publishes if the tracking mode
    is ``git_ref``.

    For other tracking modes, this field may be `None`.
    """

    tracked_refs = db.Column(MutableList.as_mutable(JSONEncodedVARCHAR(2048)))
    """The list of Git refs this Edition tracks and publishes if the tracking
    mode is ``git_refs``.

    For other tracking modes, this field may be `None`.
    """

    slug = db.Column(db.Unicode(255), nullable=False)
    """URL-safe slug for edition."""

    title = db.Column(db.Unicode(256), nullable=False)
    """Human-readable title for edition."""

    date_created = db.Column(db.DateTime, default=datetime.now, nullable=False)
    """DateTime when this edition was initially created."""

    date_rebuilt = db.Column(db.DateTime, default=datetime.now, nullable=False)
    """DateTime when the Edition was last rebuild.
    """

    date_ended = db.Column(db.DateTime, nullable=True)
    """DateTime when the Edition is deprecated (ready for deletion). Null
    otherwise.
    """

    surrogate_key = db.Column(db.String(32))
    """surrogate-key header for Fastly (quick purges); 32-char hex."""

    pending_rebuild = db.Column(db.Boolean, default=False, nullable=False)
    """Flag indicating if a rebuild is pending work by the rebuild task."""

    kind = db.Column(
        IntEnum(EditionKind), default=EditionKind.draft, nullable=False
    )
    """The edition's kind.

    See also
    --------
    EditionKind
    """

    # Relationships
    build = db.relationship("Build", uselist=False)
    """One-to-one relationship with the `Build` resource."""

    @property
    def bucket_root_dirname(self) -> str:
        """Directory in the bucket where the edition is located."""
        return "/".join((self.product.slug, "v", self.slug))

    @property
    def published_url(self) -> str:
        """URL where this edition is published to the end-user."""
        product_root_url = self.product.published_url
        if self.slug == "__main":
            # Special case for main; published at the product's base path
            return product_root_url
        else:
            if not product_root_url.endswith("/"):
                product_root_url = f"{product_root_url}/"
            return f"{product_root_url}v/{self.slug}"

    def should_rebuild(self, build: Build) -> bool:
        """Determine whether the edition should be rebuilt to show a certain
        build given the tracking mode.

        Parameters
        ----------
        build : `Build`
            `Build` object.

        Returns
        -------
        decision : `bool`
            `True` if the edition should be rebuilt using this Build, or
            `False` otherwise.
        """
        logger = get_logger(__name__)
        logger.debug("Inside Edition.should_rebuild")

        logger = get_logger(__name__)

        candidate_build = build

        # Prefilter
        if candidate_build.product != self.product:
            return False
        if candidate_build.uploaded is False:
            return False

        try:
            tracking_mode = edition_tracking_modes[self.mode]
        except (KeyError, ValidationError):
            tracking_mode = edition_tracking_modes[self.default_mode_id]
            logger.warning(
                "Edition {!r} has an unknown tracking" "mode".format(self.slug)
            )

        return tracking_mode.should_update(self, candidate_build)

    def set_pending_rebuild(self, build: Build) -> None:
        """Update the build this edition is declared to point to and set it
        to a pending state.

        This method should be called from the task that is actively handling
        the rebuild. This method does not perform the rebuild itself.

        Parameters
        ----------
        build : `Build`
            `Build` object.

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

        4. Sets the edition's build to the new build.
        """
        # Create a surrogate-key for the edition if it doesn't have one
        if self.surrogate_key is None:
            self.surrogate_key = uuid.uuid4().hex

        # State validation
        if self.pending_rebuild:
            raise ValidationError(
                "This edition already has a pending rebuild, this request "
                "will not be accepted."
            )
        if build.uploaded is False:
            raise ValidationError(f"Build has not been uploaded: {build.slug}")
        if build.date_ended is not None:
            raise ValidationError(f"Build was deprecated: {build.slug}")

        # Set the desired state
        self.build = build
        self.pending_rebuild = True

    def set_rebuild_complete(self) -> None:
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

    def set_mode(self, mode: str) -> None:
        """Set the ``mode`` attribute.

        Parameters
        ----------
        mode : `str`
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
    def default_mode_name(self) -> str:
        """Default tracking mode name if ``Edition.mode`` is `None` (`str`)."""
        return "git_ref"

    @property
    def default_mode_id(self) -> int:
        """Default tracking mode ID if ``Edition.mode`` is `None` (`int`)."""
        return edition_tracking_modes.name_to_id(self.default_mode_name)

    @property
    def mode_name(self) -> str:
        """Name of the mode (`str`).

        See also
        --------
        EditionMode
        """
        if self.mode is not None:
            return edition_tracking_modes.id_to_name(self.mode)
        else:
            return self.default_mode_name

    @property
    def kind_name(self) -> str:
        """Name of the kind (`str`).

        See also
        --------
        EditionKind
        """
        return self.kind.name

    def update_slug(self, new_slug: str) -> None:
        """Update the edition's slug by migrating files on S3.

        This method only validates the slugs name and sets it on the model.
        The caller is responsible for also migrating the S3 objects.
        """
        # Check that this slug does not already exist
        self._validate_slug(new_slug)
        self.slug = new_slug

    def _compute_autoincremented_slug(self) -> str:
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
        slugs = (
            db.session.query(Edition.slug)
            .autoflush(False)
            .filter(Edition.product == self.product)
            .all()
        )

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
            return "1"
        else:
            return str(max(integer_slugs) + 1)

    def _validate_slug(self, slug: str) -> bool:
        """Ensure that the slug is both unique to the product and meets the
        slug format regex.

        Raises
        ------
        ValidationError
        """
        # Check against slug regex
        validate_path_slug(slug)

        # Check uniqueness.
        # Turning off autoflush so that this object isn't being queried.
        existing_count = (
            Edition.query.autoflush(False)
            .filter(Edition.product == self.product)
            .filter(Edition.slug == slug)
            .count()
        )
        if existing_count > 0:
            raise ValidationError(
                "Invalid edition: slug ({0}) already exists".format(slug)
            )

        return True

    def deprecate(self) -> None:
        """Deprecate the Edition; sets the `date_ended` field."""
        self.date_ended = datetime.now()
