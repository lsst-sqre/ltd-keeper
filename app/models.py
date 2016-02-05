"""Flask-SQLAlchemy-based database ORM models."""
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from flask import url_for, current_app

from . import db
from .exceptions import ValidationError
from .utils import split_url, format_utc_datetime


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
    eups_package = db.Column(db.Unicode(256), nullable=False, unique=True)
    doc_repo = db.Column(db.String(256), nullable=False)
    name = db.Column(db.Unicode(256), nullable=False)
    domain = db.Column(db.String(256), nullable=False)
    build_bucket = db.Column(db.String(256), nullable=True)
    # TODO add
    # - build_bucket_domain
    # - http_schema

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
            'eups_package': self.eups_package,
            'doc_repo': self.doc_repo,
            'name': self.name,
            'domain': self.domain,
            'build_bucket': self.build_bucket
        }

    def import_data(self, data):
        """Convert a dict `data` into a table row."""
        try:
            self.eups_package = data['eups_package']
            self.doc_repo = data['doc_repo']
            self.name = data['name']
            self.domain = data['domain']
            self.build_bucket = data['build_bucket']
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
    creation_date = db.Column(db.DateTime, default=datetime.now(),
                              nullable=False)
    end_date = db.Column(db.DateTime, nullable=True)
    # FIXME add build metadata

    def get_url(self):
        """API URL for this entity."""
        return url_for('api.get_build', id=self.id, _external=True)

    def export_data(self):
        """Export entity as JSON-compatible dict."""
        return {
            'self_url': self.get_url(),
            'product_url': self.product.get_url(),
            'name': self.name,
            'creation_date': format_utc_datetime(self.creation_date),
            'end_date': format_utc_datetime(self.end_date)
        }

    def import_data(self, data):
        """Convert a dict `data` into a table row."""
        try:
            self.name = data['name']
        except KeyError as e:
            raise ValidationError('Invalid Build: missing ' + e.args[0])

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
    build_id = db.Column(db.Integer, db.ForeignKey('build.id'),
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
    creation_date = db.Column(db.DateTime, default=datetime.now(),
                              nullable=False)
    # Date when the edition was updated (e.g., new build)
    rebuilt_date = db.Column(db.DateTime, default=datetime.now(),
                             nullable=False)
    # set only when the Edition is deprecated (ready for deletion)
    end_date = db.Column(db.DateTime, nullable=True)

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
            'creation_date': self.creation_date,
            'rebuilt_date': self.rebuilt_date,
            'end_date': self.end_date
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

        return self
