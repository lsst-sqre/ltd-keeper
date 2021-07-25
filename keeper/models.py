"""Flask-SQLAlchemy-based database ORM models.

Copyright 2016 AURA/LSST.
Copyright 2014 Miguel Grinberg.
"""

from __future__ import annotations

import enum
import urllib.parse
import uuid
from datetime import datetime
from typing import Any, Dict, Optional, Type, Union

from flask import current_app
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from structlog import get_logger
from werkzeug.security import check_password_hash, generate_password_hash

from keeper import s3
from keeper.editiontracking import EditionTrackingModes
from keeper.exceptions import ValidationError
from keeper.taskrunner import append_task_to_chain, mock_registry
from keeper.utils import (
    JSONEncodedVARCHAR,
    MutableList,
    split_url,
    validate_path_slug,
)

__all__ = [
    "mock_registry",
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

# Register imports of celery task chain launchers
mock_registry.extend(["keeper.models.append_task_to_chain"])


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

    fastly_encrypted_api_key = db.Column(db.String(255), nullable=True)
    """Fastly API key for this organization.

    The key is persisted as a fernet token.
    """

    fastly_service_id = db.Column(db.Unicode(255), nullable=True)
    """Fastly service ID."""

    bucket_name = db.Column(db.Unicode(255), nullable=True)
    """Name of the S3 bucket hosting builds."""

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

    root_fastly_domain = db.Column(db.Unicode(255), nullable=False)
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

    @classmethod
    def from_url(cls, product_url: str) -> "Product":
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
        if product_endpoint != "api.get_product" or "slug" not in product_args:
            logger.debug(
                "Invalid product_url",
                product_endpoint=product_endpoint,
                product_args=product_args,
            )
            raise ValidationError(
                "Invalid product_url: {}".format(product_url)
            )
        slug = product_args["slug"]
        product = cls.query.filter_by(slug=slug).first_or_404()

        return product

    @property
    def domain(self) -> str:
        """Domain where docs for this product are served from.

        (E.g. ``product.lsst.io`` if ``product`` is the slug and ``lsst.io``
        is the ``root_domain``.)
        """
        return ".".join((self.slug, self.root_domain))

    @property
    def fastly_domain(self) -> str:
        """Domain where Fastly serves content from for this product."""
        # Note that in non-ssl contexts fastly wants you to prepend the domain
        # to fastly's origin domain. However we don't do this with TLS.
        # return '.'.join((self.domain, self.root_fastly_domain))
        return self.root_fastly_domain

    @property
    def published_url(self) -> str:
        """URL where this product is published to the end-user."""
        parts = ("https", self.domain, "", "", "", "")
        return urllib.parse.urlunparse(parts)


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

    @classmethod
    def from_url(cls, build_url: str) -> "Build":
        """Get a Build given its API URL.

        Parameters
        ----------
        build_url : `str`
            External API URL of the build.

        Returns
        -------
        build : `Build`
            The Build instance corresponding to the URL.
        """
        # Get new Build ID from the build resource's URL
        build_endpoint, build_args = split_url(build_url)
        if build_endpoint != "api.get_build" or "id" not in build_args:
            raise ValidationError("Invalid build_url: {}".format(build_url))
        build = cls.query.get(build_args["id"])
        if build is None:
            raise ValidationError("Invalid build_url: " + build_url)

        return build

    @property
    def bucket_root_dirname(self) -> str:
        """Directory in the bucket where the build is located."""
        return "/".join((self.product.slug, "builds", self.slug))

    @property
    def published_url(self) -> str:
        """URL where this build is published to the end-user."""
        parts = (
            "https",
            self.product.domain,
            "/builds/{0}".format(self.slug),
            "",
            "",
            "",
        )
        return urllib.parse.urlunparse(parts)

    def patch_data(self, data: Dict[str, Any]) -> None:
        """Modify build via PATCH.

        Only allowed modification is to set 'uploaded' field to True to
        acknowledge a build upload to the bucket.
        """
        if "uploaded" in data:
            if data["uploaded"] is True:
                self.register_uploaded_build()

    def register_uploaded_build(self) -> None:
        """Hook for when a build has been uploaded."""
        self.uploaded = True

        editions = (
            Edition.query.autoflush(False)
            .filter(Edition.product == self.product)
            .all()
        )

        for edition in editions:
            if edition.should_rebuild(build=self):
                edition.set_pending_rebuild(build=self)

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

    @classmethod
    def from_url(cls, edition_url: str) -> "Edition":
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
        if edition_endpoint != "api.get_edition" or "id" not in endpoint_args:
            logger.debug(
                "Invalid edition_url",
                edition_endpoint=edition_endpoint,
                endpoint_args=endpoint_args,
            )
            raise ValidationError(
                "Invalid edition_url: {}".format(edition_url)
            )
        edition = cls.query.get(endpoint_args["id"])

        return edition

    @property
    def bucket_root_dirname(self) -> str:
        """Directory in the bucket where the edition is located."""
        return "/".join((self.product.slug, "v", self.slug))

    @property
    def published_url(self) -> str:
        """URL where this edition is published to the end-user."""
        if self.slug == "main":
            # Special case for main; published at product's root
            parts = ("https", self.product.domain, "", "", "", "")
        else:
            parts = (
                "https",
                self.product.domain,
                "/v/{0}".format(self.slug),
                "",
                "",
                "",
            )
        return urllib.parse.urlunparse(parts)

    def patch_data(self, data: Dict[str, Any]) -> None:
        """Partial update of the Edition."""
        # shim during refactoring
        from keeper.api._urls import url_for_edition

        logger = get_logger(__name__)

        if "tracked_refs" in data:
            tracked_refs = data["tracked_refs"]
            if isinstance(tracked_refs, str):
                raise ValidationError(
                    "Invalid Edition: tracked_refs must "
                    "be an array of strings"
                )
            self.tracked_refs = data["tracked_refs"]

        if "mode" in data:
            self.set_mode(data["mode"])

        if "title" in data:
            self.title = data["title"]

        if "build_url" in data:
            self.set_pending_rebuild(build_url=data["build_url"])

        if "slug" in data:
            self.update_slug(data["slug"])

        if "pending_rebuild" in data:
            logger.warning(
                "Manual reset of Edition.pending_rebuild",
                edition=url_for_edition(self),
                prev_pending_rebuild=self.pending_rebuild,
                new_pending_rebuild=data["pending_rebuild"],
            )
            self.pending_rebuild = data["pending_rebuild"]

    def should_rebuild(
        self, build_url: Optional[str] = None, build: Optional[Build] = None
    ) -> bool:
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
        # shim during refactoring
        from keeper.api._urls import url_for_edition

        logger = get_logger(__name__)

        logger.debug(
            "Edition {!r} in should_rebuild".format(url_for_edition(self))
        )

        if build is not None:
            candidate_build = build
        elif build_url is not None:
            candidate_build = Build.from_url(build_url)
        else:
            raise RuntimeError("Provide either a build or build_url arg.")

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
                "Edition {!r} has an unknown tracking"
                "mode".format(url_for_edition(self))
            )

        return tracking_mode.should_update(self, candidate_build)

    def set_pending_rebuild(
        self, build_url: Optional[str] = None, build: Optional["Build"] = None
    ) -> None:
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
            if build_url is None:
                raise RuntimeError("Provide a build_url if build is None")
            build = Build.from_url(build_url)

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

        # Add the rebuild_edition task
        # Lazy load the task because it references the db/Edition model
        # shim for refactoring
        from keeper.api._urls import url_for_edition

        from .tasks.editionrebuild import rebuild_edition

        edition_url = url_for_edition(self)

        append_task_to_chain(rebuild_edition.si(edition_url, self.id))

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
        return "git_refs"

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

    def update_slug(self, new_slug: str) -> None:
        """Update the edition's slug by migrating files on S3."""
        # Check that this slug does not already exist
        self._validate_slug(new_slug)

        old_bucket_root_dir = self.bucket_root_dirname

        self.slug = new_slug
        new_bucket_root_dir = self.bucket_root_dirname

        AWS_ID = current_app.config["AWS_ID"]
        AWS_SECRET = current_app.config["AWS_SECRET"]
        if (
            AWS_ID is not None
            and AWS_SECRET is not None
            and self.build is not None
        ):
            s3.copy_directory(
                self.product.bucket_name,
                old_bucket_root_dir,
                new_bucket_root_dir,
                AWS_ID,
                AWS_SECRET,
                surrogate_key=self.surrogate_key,
            )
            s3.delete_directory(
                self.product.bucket_name,
                old_bucket_root_dir,
                AWS_ID,
                AWS_SECRET,
            )

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
