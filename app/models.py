"""Flask-SQLAlchemy-based database ORM models."""

from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from flask import url_for, current_app

from . import db
from .exceptions import ValidationError


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
    eups_package = db.Column(db.Unicode(256))
    doc_repo = db.Column(db.String(256))
    name = db.Column(db.Unicode(256))
    domain = db.Column(db.String(256))
    build_bucket = db.Column(db.String(256))

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
