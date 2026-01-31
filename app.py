from flask import Flask, render_template, request, redirect, url_for, session, flash
from config import Config
from extensions import db
from models import User, Donation, NGO, NGONeed
from datetime import datetime
import random
import string
import re
from flask import current_app
import os
import time
import secrets


def create_app():
    app = Flask(
        __name__,
        static_folder="static",
        template_folder="templates"
    )
    app.config.from_object(Config)
    app.config["SERVER_INSTANCE_ID"] = secrets.token_hex(16)
    SESSION_TIMEOUT_SECONDS = 10 * 60  # 10 minutes

    db.init_app(app)

    with app.app_context():
        db.create_all()
        seed_ngos_if_empty()
        seed_default_admin()

    @app.before_request
    def enforce_session_security():
        user_id = session.get("user_id")
        if not user_id:
            return

        if session.get("server_instance_id") != app.config["SERVER_INSTANCE_ID"]:
            session.clear()
            return 

        # Inactivity timeout
        now = int(time.time())
        last_seen = session.get("last_seen", now)

        if now - last_seen > SESSION_TIMEOUT_SECONDS:
            session.clear()
            return

        session["last_seen"] = now

    # -------------- Helper functions ----------------

    def current_user():
        uid = session.get("user_id")
        if not uid:
            return None
        return User.query.get(uid)
    
    @app.context_processor
    def inject_user():
        return {"user": current_user()}

    def login_required(role=None):
        def decorator(fn):
            from functools import wraps

            @wraps(fn)
            def wrapper(*args, **kwargs):
                user = current_user()
                if not user:
                    flash("Please login first.", "warning")
                    # If this is an admin-only route, send to admin login
                    if role == "admin":
                        return redirect(url_for("admin_login"))
                    return redirect(url_for("login"))

                if role and user.role != role:
                    flash("You do not have permission.", "danger")

                    # If user is admin but trying to access donor-only page
                    if user.role == "admin":
                        return redirect(url_for("admin_dashboard"))

                    # If user is donor but trying to access admin-only page
                    return redirect(url_for("donor_home"))

                return fn(*args, **kwargs)

            return wrapper

        return decorator

    def generate_tracking_id() -> str:
        """
        Generate IDs like DN-001, DN-002, ...
        Based on the last donation's ID.
        """
        last = Donation.query.order_by(Donation.id.desc()).first()
        next_number = 1 if not last else last.id + 1
        return f"DN-{next_number:03d}"


    # -------------- Routes ----------------

    @app.route("/")
    def donor_home():
        user = current_user()
        # If admin is logged in, push them to admin dashboard instead of donor home
        if user and user.role == "admin":
            return redirect(url_for("admin_dashboard"))
        return render_template("donor_home.html", user=user, hide_navbar=True)

    
    @app.route("/ngos")
    def public_ngos():
        ngos = NGO.query.order_by(NGO.name.asc()).all()

        needs_map = {}
        for ngo in ngos:
            need = (
                NGONeed.query
                .filter(
                    NGONeed.ngo_id == ngo.id,
                    NGONeed.is_active == True
                )
                .order_by(NGONeed.created_at.desc())
                .first()
            )
            needs_map[ngo.id] = need

        return render_template("list_ngos.html", ngos=ngos, needs_map=needs_map)

    @app.route("/register", methods=["GET", "POST"])
    def register():
        # default empty values for GET
        full_name = ""
        email = ""
        phone = ""
        zone = ""

        if request.method == "POST":
            full_name = request.form.get("full_name", "").strip()
            email = request.form.get("email", "").strip().lower()
            phone = request.form.get("phone", "").strip()
            password = request.form.get("password", "")
            confirm_password = request.form.get("confirm_password", "")
            zone = request.form.get("zone", "").strip()

            errors = []
            field_errors = {}

            # Required fields
            if not full_name:
                errors.append("Full name is required.")
                field_errors["full_name"] = True

            if not email:
                errors.append("Email is required.")
                field_errors["email"] = True

            if not phone:
                errors.append("Phone number is required.")
                field_errors["phone"] = True

            if not zone:
                errors.append("Zone (Area in Karachi) is required.")
                field_errors["zone"] = True

            if not password:
                errors.append("Password is required.")
                field_errors["password"] = True

            if not confirm_password:
                errors.append("Confirm Password is required.")
                field_errors["confirm_password"] = True

            # Email format (must start with a letter)
            email_pattern = r'^[A-Za-z][A-Za-z0-9._%+-]*@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'
            if email and not re.match(email_pattern, email):
                errors.append("Email must start with a letter and be valid (e.g. name@example.com).")
                field_errors["email"] = True


            # Phone format
            phone_pattern = r'^\d{4}-\d{7}$'
            if phone and not re.match(phone_pattern, phone):
                errors.append("Phone must be in format xxxx-xxxxxxx (e.g. 0301-2345678).")
                field_errors["phone"] = True

            # Password rules
            if full_name and len(full_name) < 5:
                errors.append("Enter Your Full Name.")
                field_errors["full_name"] = True

            # Password rules
            if password and len(password) < 8:
                errors.append("Password must be at least 8 characters long.")
                field_errors["password"] = True

            if password and not re.search(r'[^A-Za-z0-9]', password):
                errors.append("Password must include at least one special character (e.g. @, #, !, %).")
                field_errors["password"] = True

            # Match confirm password
            if password and confirm_password and password != confirm_password:
                errors.append("Password and Confirm Password do not match.")
                field_errors["confirm_password"] = True
                field_errors["password"] = True  # optional: highlight both

            # Email unique
            if email and User.query.filter_by(email=email).first():
                errors.append("This email is already registered.")
                field_errors["email"] = True

            # Phone Number unique
            if phone and User.query.filter_by(phone=phone).first():
                errors.append("This phone number is already registered.")
                field_errors["phone"] = True

            # If errors -> flash and render SAME PAGE (keep values via request.form in HTML)
            if errors:
                for e in errors:
                    flash(e, "danger")
                return render_template("register.html", field_errors=field_errors), 400

            # Create user (success)
            user = User(full_name=full_name, email=email, phone=phone, zone=zone)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()

            flash("Registration successful. Please login.", "success")
            return redirect(url_for("login"))

        # GET
        return render_template("register.html", field_errors={}, hide_navbar=True)

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")

            user = User.query.filter_by(email=email).first()
            if not user or not user.check_password(password):
                flash("Invalid credentials.", "danger")
                return redirect(url_for("login"))

            # Block admins here – tell them to use admin login
            if user.role == "admin":
                flash("Please use the admin login page.", "warning")
                return redirect(url_for("admin_login"))

            # Donor login
            session["user_id"] = user.id
            session["server_instance_id"] = app.config["SERVER_INSTANCE_ID"]
            session["last_seen"] = int(time.time())

            flash("Logged in successfully.", "success")
            return redirect(url_for("donate"))

        return render_template("login.html", hide_navbar=True)

    
    @app.route("/admin/login", methods=["GET", "POST"])
    def admin_login():
        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")

            user = User.query.filter_by(email=email).first()
            if not user or not user.check_password(password):
                flash("Invalid credentials.", "danger")
                return redirect(url_for("admin_login"))

            if user.role != "admin":
                flash("This login is for admin users only.", "danger")
                return redirect(url_for("admin_login"))

            # login admin
            session["user_id"] = user.id
            session["server_instance_id"] = app.config["SERVER_INSTANCE_ID"]
            session["last_seen"] = int(time.time())

            flash("Logged in as admin.", "success")
            return redirect(url_for("admin_dashboard"))

        return render_template("admin_login.html", hide_admin_navbar=True, show_admin_header=True)


    @app.route("/logout")
    def logout():
        if not session.get("user_id"):
            flash("You are not logged in.", "danger")
            return redirect(url_for("donor_home"))

        session.clear()
        flash("Logged out.", "info")
        return redirect(url_for("donor_home"))


    @app.route("/donate/new", methods=["GET", "POST"])
    @login_required(role="donor")
    def donate():
        user = current_user()
        if not user:
            return redirect(url_for("login"))

        if request.method == "POST":
            item_name = request.form.get("item_name", "").strip()
            quantity = request.form.get("quantity", "").strip()
            condition = request.form.get("condition", "").strip()
            description = request.form.get("description", "").strip()  # optional now
            category_hint = request.form.get("category_hint", "").strip()

            errors = []

            # ---- Basic required fields ----
            if not item_name:
                errors.append("Item name is required.")

            # item name must be at least 3 characters and contain some letters
            elif len(item_name) < 3 or not re.search(r"[A-Za-z]", item_name):
                errors.append(
                    "Please enter a meaningful item name (e.g. '10kg potatoes' or 'school bags and books'), not random characters."
                )

            if not quantity:
                errors.append("Quantity is required.")
            else:
                if not quantity.isdigit() or int(quantity) <= 0:
                    errors.append("Quantity must be a positive whole number (e.g. 5, 10, 100).")

            if not condition:
                errors.append("Please select the condition of the item.")
            if not category_hint:
                errors.append("Please select a donation category (e.g. Food, Clothes, Education).")

            # ---- Block cash/money donations ----
            combined_text = f"{item_name} {description}".lower()
            forbidden_cash_words = [
                "cash", "money", "zakat", "sadqa", "sadaqa", "donation amount", "fund", "amount"
            ]
            if any(word in combined_text for word in forbidden_cash_words):
                errors.append(
                    "Our system does not process cash/monetary donations. Please donate physical items like food, clothes, books, etc."
                )

            combined_text = f"{item_name} {description}".lower()
            forbidden_blood_words = [
                "blood", "khoon", "blood donate", "O Positive"
            ]
            if any(word in combined_text for word in forbidden_blood_words):
                errors.append(
                    "Our system does not process blood donations. Please donate physical items like food, clothes, books, etc."
                )

            if errors:
                for e in errors:
                    flash(e, "danger")
                return redirect(url_for("donate"))

            # Convert quantity after validation
            quantity_int = int(quantity)

            tracking_id = generate_tracking_id()

            donation = Donation(
                tracking_id=tracking_id,
                item_name=item_name,
                quantity=quantity_int,
                condition=condition,
                description=description or "",
                donor_zone=user.zone,
                status="pending",
                donor_id=user.id,
            )

            db.session.add(donation)
            db.session.commit()

            flash("Donation submitted successfully.", "success")
            return redirect(url_for("donation_success", tracking_id=tracking_id))

        return render_template("donation_form.html")

    @app.route("/donation/success/<tracking_id>")
    @login_required(role="donor")
    def donation_success(tracking_id):
        return render_template("donation_success.html", tracking_id=tracking_id)

    # ---------- Tracking ----------
    @app.route("/track", methods=["GET", "POST"])
    @login_required(role="donor")
    def track():
        user = current_user()
        if not user:
            return redirect(url_for("login"))

        if request.method == "POST":
            tracking_id = request.form.get("tracking_id", "").strip()
            if not tracking_id:
                flash("Please enter your tracking ID.", "danger")
                return redirect(url_for("track"))

            # Only allow tracking of donations belonging to this logged-in user
            donation = Donation.query.filter_by(
                tracking_id=tracking_id,
                donor_id=user.id
            ).first()

            if not donation:
                flash("No donation found with this tracking ID for your account.", "danger")
                return redirect(url_for("track"))

            return render_template("track_result.html", donation=donation)

        # GET -> just show tracking form
        return render_template("track_form.html")

    # ---------- Admin ----------

    @app.route("/admin/dashboard")
    @login_required(role="admin")
    def admin_dashboard():
    
        pending = Donation.query.filter_by(status="pending") \
            .order_by(Donation.created_at.asc()).all()

        assigned = Donation.query.filter_by(status="assigned") \
            .order_by(Donation.assigned_at.desc()).all()
        
        rejected = Donation.query.filter_by(status="rejected") \
            .order_by(Donation.rejected_at.desc()).all()
        
        ngos = NGO.query.order_by(NGO.name.asc()).all()
        
        return render_template(
            "admin_dashboard.html",
            pending=pending,
            assigned=assigned,
            rejected=rejected,
            ngos=ngos,
            show_admin_header=True,
            hide_admin_navbar=False, 
        )
    
    @app.route("/admin/donations/pending")
    @login_required(role="admin")
    def admin_pending_donations():
        donations = (
            Donation.query
            .filter_by(status="pending")
            .order_by(Donation.created_at.asc())
            .all()
        )
        return render_template(
            "admin_donations_list.html",
            donations=donations,
            page_title="Pending Donations",
            status_label="Pending",
            show_admin_header=True,
            hide_admin_navbar=False,
        )

    @app.route("/admin/donations/assigned")
    @login_required(role="admin")
    def admin_assigned_donations():
        donations = (
            Donation.query
            .filter_by(status="assigned")
            .order_by(Donation.assigned_at.desc())
            .all()
        )
        return render_template(
            "admin_donations_list.html",
            donations=donations,
            page_title="Assigned Donations",
            status_label="Assigned",
            show_admin_header=True,
            hide_admin_navbar=False,
        )

    @app.route("/admin/donations/rejected")
    @login_required(role="admin")
    def admin_rejected_donations():
        donations = (
            Donation.query
            .filter_by(status="rejected")
            .order_by(Donation.rejected_at.desc())
            .all()
        )
        return render_template(
            "admin_donations_list.html",
            donations=donations,
            page_title="Rejected Donations",
            status_label="Rejected",
            show_admin_header=True,
            hide_admin_navbar=False,
        )

    
    @app.route("/admin/donation/<int:donation_id>", methods=["GET", "POST"])
    @login_required(role="admin")
    def admin_donation_detail(donation_id):
        donation = Donation.query.get_or_404(donation_id)

        if request.method == "POST":
            action = request.form.get("action")

            if action == "reject":
                reason = request.form.get("reject_reason", "").strip()

                if not reason:
                    flash("Reject reason is required.", "danger")
                    return redirect(url_for("admin_donation_detail", donation_id=donation_id))

                donation.status = "rejected"
                donation.rejected_reason = reason
                donation.rejected_at = datetime.utcnow()

                db.session.commit()
                flash("Donation rejected.", "info")
                return redirect(url_for("admin_dashboard"))

            if action == "assign":
                ngo_id = request.form.get("ngo_id")
                need_id = request.form.get("need_id")

                ngo = NGO.query.get(int(ngo_id)) if ngo_id else None
                if not ngo:
                    flash("Please choose a valid NGO.", "danger")
                    return redirect(url_for("admin_donation_detail", donation_id=donation_id))

                # link donation to NGO
                donation.ngo_id = ngo.id
                donation.status = "assigned"
                donation.assigned_at = datetime.utcnow()
                ngo.current_load = (ngo.current_load or 0) + 1

                # if admin selected a specific need, update that need
                if need_id:
                    need = NGONeed.query.get(int(need_id))
                    if need:
                        donation.need_id = need.id

                        increment = donation.quantity or 0
                        if increment > 0:
                            # increase fulfilled quantity
                            need.qty_fulfilled = (need.qty_fulfilled or 0) + increment
                            # do not exceed required
                            if need.qty_fulfilled > need.qty_required:
                                need.qty_fulfilled = need.qty_required

                db.session.commit()

                flash(f"Donation assigned to {ngo.name}.", "success")
                return redirect(url_for("admin_dashboard"))

        # also show all NGOs as fallback
        all_ngos = NGO.query.order_by(NGO.name.asc()).all()
        all_needs = NGONeed.query.filter_by(is_active=True).order_by(NGONeed.created_at.desc()).all()

        return render_template(
            "admin_donation_detail.html",
            donation=donation,
            all_ngos=all_ngos,
            all_needs=all_needs,
            show_admin_header=True,
            hide_admin_navbar=True, 
        )

    @app.route("/admin/ngos")
    @login_required(role="admin")
    def admin_ngos_list():
        ngos = NGO.query.order_by(NGO.name.asc()).all()

        needs_map = {}
        for ngo in ngos:
            need = (
                NGONeed.query
                .filter(
                    NGONeed.ngo_id == ngo.id,
                    NGONeed.is_active == True
                )
                .order_by(NGONeed.created_at.desc())
                .first()
            )
            needs_map[ngo.id] = need

        return render_template("admin_ngos_list.html", ngos=ngos, needs_map=needs_map,  show_admin_header=True, hide_admin_navbar=False)

    
    @app.route("/admin/ngos/<int:ngo_id>/needs", methods=["GET", "POST"])
    @login_required(role="admin")
    def admin_manage_ngo_needs(ngo_id):
        ngo = NGO.query.get_or_404(ngo_id)

        if request.method == "POST":
            item_name = request.form.get("item_name", "").strip()
            category = request.form.get("category", "").strip()
            condition_needed = request.form.get("condition_needed", "").strip()
            details = request.form.get("details", "").strip()

            qty_required_raw = request.form.get("qty_required", "0").strip()
            try:
                qty_required = int(qty_required_raw)
            except ValueError:
                qty_required = -1

            if not item_name:
                flash("Item name is required.", "danger")
                return redirect(url_for("admin_manage_ngo_needs", ngo_id=ngo_id))

            if qty_required < 1:
                flash("Required quantity must be a positive number.", "danger")
                return redirect(url_for("admin_manage_ngo_needs", ngo_id=ngo_id))

            need = NGONeed(
                ngo_id=ngo.id,
                item_name=item_name,
                category=category or None,
                condition_needed=condition_needed or None,
                details=details or None,
                qty_required=qty_required,
                qty_fulfilled=0,
                is_active=True
            )
            db.session.add(need)
            db.session.commit()

            flash("Need added successfully.", "success")
            return redirect(url_for("admin_manage_ngo_needs", ngo_id=ngo_id))

        needs = NGONeed.query.filter_by(ngo_id=ngo.id).order_by(NGONeed.created_at.desc()).all()
        return render_template("admin_ngo_needs.html", ngo=ngo, needs=needs)


    @app.route("/admin/needs/<int:need_id>/toggle", methods=["POST"])
    @login_required(role="admin")
    def admin_toggle_need(need_id):
        need = NGONeed.query.get_or_404(need_id)
        need.is_active = not need.is_active
        db.session.commit()
        flash("Need status updated.", "success")
        return redirect(url_for("admin_manage_ngo_needs", ngo_id=need.ngo_id))

    return app



def seed_default_admin():
    """
    Seed a fixed default Admin user if not already created.
    """
    admin_email = "admin@donation.com"
    admin_password = "Admin@123"

    existing = User.query.filter_by(email=admin_email).first()
    if not existing:
        admin = User(full_name="System Admin", email=admin_email, phone=None, zone=None, role="admin")
        admin.set_password(admin_password)
        db.session.add(admin)
        db.session.commit()
        print("✅ Default admin created")
    else:
        print("🔹 Default admin already exists")

def seed_ngos_if_empty():
    """Seed ~20 Karachi NGOs for testing (only if table is empty)."""
    if NGO.query.first():
        return

    ngos = [
        NGO(
            name="Edhi Foundation - Karachi (Mithadar)",
            city="Karachi",
            zone="Mithadar",
            accepted_categories="Clothes,Food,Medical",
            has_pickup=True,
            is_verified=True,
        ),
        NGO(
            name="Saylani Welfare Trust - Bahadurabad",
            city="Karachi",
            zone="Bahadurabad",
            accepted_categories="Food,Clothes,Education",
            has_pickup=True,
            is_verified=True,
        ),
        NGO(
            name="Chhipa Welfare Association - Gulshan",
            city="Karachi",
            zone="Gulshan-e-Iqbal",
            accepted_categories="Clothes,Food,Medical",
            has_pickup=True,
            is_verified=True,
        ),
        NGO(
            name="Aman Foundation - Korangi",
            city="Karachi",
            zone="Korangi",
            accepted_categories="Medical,Education",
            has_pickup=True,
            is_verified=True,
        ),
        NGO(
            name="Alkhidmat Foundation - North Karachi",
            city="Karachi",
            zone="North Karachi",
            accepted_categories="Food,Clothes",
            has_pickup=True,
            is_verified=True,
        ),
        NGO(
            name="The Citizens Foundation - Clifton",
            city="Karachi",
            zone="Clifton",
            accepted_categories="Education",
            has_pickup=True,
            is_verified=True,
        ),
        NGO(
            name="HANDS Pakistan - Saddar",
            city="Karachi",
            zone="Saddar",
            accepted_categories="Medical,Food,Clothes",
            has_pickup=True,
            is_verified=True,
        ),
        NGO(
            name="SIUT - Civil Lines",
            city="Karachi",
            zone="Civil Lines",
            accepted_categories="Medical",
            has_pickup=True,
            is_verified=True,
        ),
        NGO(
            name="LRBT Free Eye Hospital - Landhi",
            city="Karachi",
            zone="Landhi",
            accepted_categories="Medical",
            has_pickup=True,
            is_verified=True,
        ),
        NGO(
            name="JDC Welfare Organization - Johar",
            city="Karachi",
            zone="Gulistan-e-Johar",
            accepted_categories="Food,Clothes,Medical",
            has_pickup=True,
            is_verified=True,
        ),
        NGO(
            name="Karachi Down Syndrome Program - PECHS",
            city="Karachi",
            zone="PECHS",
            accepted_categories="Education,Medical",
            has_pickup=True,
            is_verified=True,
        ),
        NGO(
            name="Dar-ul-Sukun - Kashmir Road",
            city="Karachi",
            zone="Kashmir Road",
            accepted_categories="Clothes,Medical,Education",
            has_pickup=True,
            is_verified=True,
        ),
        NGO(
            name="Lyari Community Development Project",
            city="Karachi",
            zone="Lyari",
            accepted_categories="Education,Clothes,Food",
            has_pickup=True,
            is_verified=True,
        ),
        NGO(
            name="Sindh Institute of Physical Medicine & Rehabilitation",
            city="Karachi",
            zone="Gulshan-e-Hadid",
            accepted_categories="Medical",
            has_pickup=True,
            is_verified=True,
        ),
        NGO(
            name="Memon Medical Institute Welfare",
            city="Karachi",
            zone="Safoora",
            accepted_categories="Medical",
            has_pickup=True,
            is_verified=True,
        ),
        NGO(
            name="Marie Stopes Society - Garden",
            city="Karachi",
            zone="Garden",
            accepted_categories="Medical,Education",
            has_pickup=True,
            is_verified=True,
        ),
        NGO(
            name="Legal Aid Society - Shahrah-e-Faisal",
            city="Karachi",
            zone="Shahrah-e-Faisal",
            accepted_categories="Education",
            has_pickup=True,
            is_verified=True,
        ),
        NGO(
            name="DOHS Welfare Trust - Malir Cantt",
            city="Karachi",
            zone="Malir Cantt",
            accepted_categories="Food,Clothes",
            has_pickup=True,
            is_verified=True,
        ),
        NGO(
            name="Patients' Aid Foundation - JPMC",
            city="Karachi",
            zone="JPMC",
            accepted_categories="Medical",
            has_pickup=True,
            is_verified=True,
        ),
        NGO(
            name="Anjuman-e-Behbood-e-Samaji Gulberg",
            city="Karachi",
            zone="Gulberg",
            accepted_categories="Clothes,Food,Education",
            has_pickup=True,
            is_verified=True,
        ),
    ]

    for ngo in ngos:
        db.session.add(ngo)
    db.session.commit()

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)

