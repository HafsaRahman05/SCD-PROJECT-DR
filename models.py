from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(30), nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default="donor")  # 'donor' or 'admin'
    # optional: rough area inside Karachi for donors, used for zone match
    zone = db.Column(db.String(50), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    donations = db.relationship("Donation", backref="donor", lazy=True)

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class NGO(db.Model):
    __tablename__ = "ngos"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    city = db.Column(db.String(100), nullable=False, default="Karachi")
    zone = db.Column(db.String(50), nullable=True)  # e.g. "Gulshan", "North Karachi"
    address = db.Column(db.String(255), nullable=True)
    contact_email = db.Column(db.String(120), nullable=True)
    contact_phone = db.Column(db.String(50), nullable=True)

    accepted_categories = db.Column(db.String(255), nullable=True)  # comma separated
    is_verified = db.Column(db.Boolean, default=True)
    has_pickup = db.Column(db.Boolean, default=False)

    current_load = db.Column(db.Integer, default=0)  # for basic load balancing

    donations = db.relationship("Donation", backref="ngo", lazy=True)

class NGONeed(db.Model):
    __tablename__ = "ngo_needs"

    id = db.Column(db.Integer, primary_key=True)

    ngo_id = db.Column(db.Integer, db.ForeignKey("ngos.id"), nullable=False)

    # what is needed
    item_name = db.Column(db.String(200), nullable=False)  # e.g. "Books"
    category = db.Column(db.String(100), nullable=True)    # e.g. "Education"
    details = db.Column(db.Text, nullable=True)            # e.g. "Class 8 Math, new preferred"
    condition_needed = db.Column(db.String(50), nullable=True)  # "New", "Used", "Any"

    qty_required = db.Column(db.Integer, nullable=False, default=0)
    qty_fulfilled = db.Column(db.Integer, nullable=False, default=0)

    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    ngo = db.relationship("NGO", backref=db.backref("needs", lazy=True))

    @property
    def qty_remaining(self):
        remaining = (self.qty_required or 0) - (self.qty_fulfilled or 0)
        return max(0, remaining)


class Donation(db.Model):
    __tablename__ = "donations"

    id = db.Column(db.Integer, primary_key=True)
    tracking_id = db.Column(db.String(20), unique=True, nullable=False)

    item_name = db.Column(db.String(200), nullable=False)
    category_manual = db.Column(db.String(100), nullable=True)  # optional manual
    quantity = db.Column(db.Integer, nullable=True)
    condition = db.Column(db.String(50), nullable=True)  # e.g. "New", "Used"
    description = db.Column(db.Text, nullable=False)

    donor_zone = db.Column(db.String(50), nullable=True)  # snapshot of donor’s zone

    status = db.Column(db.String(20), default="pending")
    # pending -> assigned -> received

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    assigned_at = db.Column(db.DateTime, nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    rejected_reason = db.Column(db.Text, nullable=True)
    rejected_at = db.Column(db.DateTime, nullable=True)

    donor_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    ngo_id = db.Column(db.Integer, db.ForeignKey("ngos.id"), nullable=True)
    need_id = db.Column(db.Integer, db.ForeignKey("ngo_needs.id"), nullable=True)
    need = db.relationship("NGONeed", backref="donations", lazy=True)


