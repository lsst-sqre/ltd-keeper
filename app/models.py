"""Flask-SQLAlchemy-based database ORM models."""
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from flask import url_for, current_app

from . import db
from .exceptions import ValidationError
from .utils import split_url, format_utc_datetime, parse_utc_datetime


class User(db.Model):
    """DB model for authenticated API users."""

    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True)
    password_hash = db.Column(db.String(128))

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
        return url_for('api.get_product', id=self.id, _external=True)

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


class Build(db.Model):
    """DB model for documentation builds."""

    __tablename__ = 'builds'
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'),
                           index=True)
    # name of build; URL-safe slug used as directory in build bucket
    name = db.Column(db.Unicode(256), nullable=False)
    # auto-assigned date build was created
    date_created = db.Column(db.DateTime, default=datetime.now(),
                             nullable=False)
    # set only when the build is deprecated (ready for deletion)
    date_ended = db.Column(db.DateTime, nullable=True)
    # FIXME add build metadata

    # Relationships
    # product - from Product class

    def get_url(self):
        """API URL for this entity."""
        return url_for('api.get_build', id=self.id, _external=True)

    def export_data(self):
        """Export entity as JSON-compatible dict."""
        return {
            'self_url': self.get_url(),
            'product_url': self.product.get_url(),
            'name': self.name,
            'date_created': format_utc_datetime(self.date_created),
            'date_ended': format_utc_datetime(self.date_ended)
        }

    def import_data(self, data):
        """Convert a dict `data` into a table row."""
        try:
            self.name = data['name']
        except KeyError as e:
            raise ValidationError('Invalid Build: missing ' + e.args[0])

        self.date_created = datetime.now()

        if 'date_ended' in data:
            try:
                self.date_ended = parse_utc_datetime(data['date_ended'])
            except:
                raise ValidationError('Invalid Edition, could not parse '
                                      'date_ended ' + data['date_ended'])

        return self


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
    tracked_refs = db.Column(db.String(1024))
    # Root path in the product's S3 bucket
    bucket_root = db.Column(db.String(256), nullable=False)
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
            'rebuilt_date': format_utc_datetime(self.date_rebuilt),
            'date_ended': format_utc_datetime(self.date_ended)
        }

    def import_data(self, data):
        """Convert a dict `data` into a table row."""
        try:
            prod_endpoint, prod_args = split_url(data['product_url'])
            build_endpoint, build_args = split_url(data['build_url'])
            self.tracked_refs = self.tracked_refs
            self.slug = data['slug']
            self.title = data['title']
            self.published_url = data['published_url']
        except KeyError as e:
            raise ValidationError('Invalid Edition: missing ' + e.args[0])

        if prod_endpoint != 'api.get_product' or 'id' not in prod_args:
            raise ValidationError('Invalid product_url: ' +
                                  data['product_url'])
        self.product = Product.query.get(prod_args['id'])
        if self.product is None:
            raise ValidationError('Invalid product_url: ' +
                                  data['product_url'])

        if build_endpoint != 'api.get_build' or 'id' not in build_args:
            raise ValidationError('Invalid build_url: ' +
                                  data['build_url'])
        self.build = Build.query.get(build_args['id'])
        if self.build is None:
            raise ValidationError('Invalid build_url: ' +
                                  data['build_url'])

        if 'date_ended' in data:
            try:
                self.date_ended = parse_utc_datetime(data['date_ended'])
            except:
                raise ValidationError('Invalid Edition, could not parse '
                                      'date_ended ' + data['date_ended'])

        self.date_rebuilt = datetime.now()

        return self
