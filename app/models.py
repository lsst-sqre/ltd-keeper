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
    builds = db.relationship('Build', backref='product', lazy='dynamic')
    eups_package = db.Column(db.Unicode(256), nullable=False, unique=True)
    doc_repo = db.Column(db.String(256), nullable=False)
    name = db.Column(db.Unicode(256), nullable=False)
    domain = db.Column(db.String(256), nullable=False)
    build_bucket = db.Column(db.String(256), nullable=True)
    # TODO add
    # - build_bucket_domain
    # - http_schema

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
