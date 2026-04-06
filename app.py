from flask import Flask, request, session, jsonify, render_template, redirect, url_for
from config import Config
from datetime import datetime,timedelta
from auth import authenticate_user
from user import get_all_users
from werkzeug.utils import secure_filename

from csv_upload import process_csv_upload, get_upload_batches, delete_batch
from ppi_analytics import (
    get_ppi_likelihood_table,
    get_dashboard_summary,
    get_branch_poverty_analysis,
    get_ppi_question_analysis,
    get_client_poverty_prediction,
    get_ppi_trend_monitoring,
    get_top_poverty_risk_factors,
    get_poverty_movement_dashboard,
    get_client_poverty_profiles,
    get_current_poverty_overview
)

from scholarship_analytics import (
    get_scholarship_dashboard,
    get_scholarship_recommendations
)

from risk_analytics import (
    get_risk_dashboard,
    get_risk_trend,
    get_top_high_risk_clients
)

from at_risk_analytics import get_client_at_risk_dashboard

from risk_factor_analytics import get_risk_factors_overview

import os
import logging

#@app.before_request
#def make_session_permanent():
  #  if "user" in session:
  #      session.permanent = True
  #      session.modified = True

# ===========================
#        CONFIG
# ===========================

UPLOAD_FOLDER = "data/ppi"
ALLOWED_EXTENSIONS = {"csv"}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

logging.basicConfig(
    filename="login.log",
    level=logging.INFO,
    format="%(asctime)s - %(message)s"
)

app = Flask(__name__)
app.config.from_object(Config)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.permanent_session_lifetime = timedelta(minutes=5)


# ===========================
#      HELPER FUNCTIONS
# ===========================

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def require_login_api():
    if "user" not in session:
        return jsonify({
            "success": False,
            "message": "Unauthorized"
        }), 401
    return None


# ===========================
#        PAGE ROUTES
# ===========================

@app.route("/")
def home():
    if "user" in session:
        return redirect(url_for("analytics_dashboard"))
    return redirect(url_for("login"))


@app.route("/login")
def login():
    return render_template("login.html")


@app.route("/analytics/dashboard")
def analytics_dashboard():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("main2.html", user=session["user"])


@app.route("/pages/<page>")
def serve_page(page):
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template(f"pages/{page}")


@app.route("/dashboard.html")
def dashboard_section():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("dashboard.html", user=session["user"])


@app.route("/cardprograms.html")
def cardprograms_section():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("cardprograms.html", user=session["user"])


@app.route("/povertyinsights.html")
def povertyinsights_section():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("povertyinsights.html", user=session["user"])


@app.route("/usermanagement.html")
def usermanagement_section():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("usermanagement.html", user=session["user"])


# ===========================================
# CATCH-ALL ROUTE TO FIX PAGE REFRESH 404
# ===========================================

@app.route("/analytics/<path:subpath>")
def analytics_router(subpath):
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("main2.html", user=session["user"])


# ===========================
#        AUTH API ROUTES
# ===========================

@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.get_json(silent=True) or {}
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({
            "status": "error",
            "message": "Username and password required"
        }), 400

    ip = request.remote_addr
    user = authenticate_user(username, password)

    if user:
        session.permanent = True
        session["user"] = {
            "userid": user["userid"],
            "username": user["username"],
            "firstname": user["firstname"],
            "staffid": user["staffid"],
            "position": user["position"]
        }

        logging.info(f"LOGIN SUCCESS username={username} user_id={user['userid']} ip={ip}")

        return jsonify({
            "status": "success",
            "message": "Login successful",
            "user": session["user"]
        }), 200

    logging.info(f"LOGIN FAILED username={username} ip={ip}")
    return jsonify({
        "status": "error",
        "message": "Invalid credentials"
    }), 401


@app.route("/api/check-session", methods=["GET"])
def check_session():
    if "user" in session:
        return jsonify({
            "active": True,
            "user": session["user"]
        }), 200

    return jsonify({
        "active": False
    }), 401


@app.route("/api/logout", methods=["POST"])
def api_logout():
    session.clear()
    return jsonify({
        "status": "success",
        "message": "Logged out successfully"
    }), 200


# ===========================
#        USER API ROUTES
# ===========================

@app.route("/api/users", methods=["GET"])
def api_get_users():
    auth = require_login_api()
    if auth:
        return auth

    users = get_all_users()
    return jsonify({
        "success": True,
        "data": users
    }), 200


# ===========================
#        CSV UPLOAD API
# ===========================

@app.route("/api/uploads/csv", methods=["POST"])
def upload_csv_to_database():
    auth = require_login_api()
    if auth:
        return auth

    try:
        if "file" not in request.files:
            return jsonify({
                "success": False,
                "message": "No file part in request"
            }), 400

        file = request.files["file"]

        if file.filename == "":
            return jsonify({
                "success": False,
                "message": "No file selected"
            }), 400

        if not allowed_file(file.filename):
            return jsonify({
                "success": False,
                "message": "Invalid file type. Only CSV files are allowed."
            }), 400

        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(file_path)

        reporting_date = request.form.get("reportingDate")
        uploaded_by = session.get("user", {}).get("username")

        result = process_csv_upload(
            file_path=file_path,
            file_name=filename,
            reporting_date=reporting_date if reporting_date else None,
            uploaded_by=uploaded_by
        )

        return jsonify({
            "success": True,
            "message": "CSV uploaded and imported successfully.",
            "data": result
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Failed to upload and import CSV.",
            "error": str(e)
        }), 500


@app.route("/api/uploads/batches", methods=["GET"])
def api_get_upload_batches():
    auth = require_login_api()
    if auth:
        return auth

    try:
        return jsonify({
            "success": True,
            "data": get_upload_batches()
        }), 200
    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Failed to fetch upload batches.",
            "error": str(e)
        }), 500


@app.route("/api/uploads/batches/<int:batch_id>", methods=["DELETE"])
def api_delete_upload_batch(batch_id):
    auth = require_login_api()
    if auth:
        return auth

    try:
        deleted = delete_batch(batch_id)

        if not deleted:
            return jsonify({
                "success": False,
                "message": "Batch not found."
            }), 404

        return jsonify({
            "success": True,
            "message": "Batch deleted successfully."
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Failed to delete batch.",
            "error": str(e)
        }), 500


# ===========================
#        PPI ANALYTICS APIs
# ===========================

#sa first page
@app.route("/api/dashboard/summary", methods=["GET"])
def dashboard_summary():
    auth = require_login_api()
    if auth:
        return auth

    try:
        batch_id = request.args.get("batchId", type=int)
        result = get_dashboard_summary(batch_id=batch_id)

        return jsonify({
            "success": True,
            "message": "Dashboard summary generated successfully",
            "data": result
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Failed to compute dashboard summary",
            "error": str(e)
        }), 500

#ppi progess out of poverty index
@app.route("/api/ppi/branch-analysis", methods=["GET"])
def ppi_branch_analysis():
    auth = require_login_api()
    if auth:
        return auth

    try:
        branch_level = request.args.get("branchLevel", "unit_office")
        batch_id = request.args.get("batchId", type=int)

        result = get_branch_poverty_analysis(
            branch_level=branch_level,
            batch_id=batch_id
        )

        return jsonify({
            "success": True,
            "message": "Branch poverty analysis generated successfully",
            "data": result
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Failed to compute branch poverty analysis",
            "error": str(e)
        }), 500


@app.route("/api/ppi/question-analysis", methods=["GET"])
def ppi_question_analysis():
    auth = require_login_api()
    if auth:
        return auth

    try:
        batch_id = request.args.get("batchId", type=int)
        result = get_ppi_question_analysis(batch_id=batch_id)

        return jsonify({
            "success": True,
            "message": "PPI question analysis generated successfully",
            "data": result
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Failed to compute PPI question analysis",
            "error": str(e)
        }), 500


@app.route("/api/ppi/prediction", methods=["GET"])
def ppi_prediction():
    auth = require_login_api()
    if auth:
        return auth

    try:
        batch_id = request.args.get("batchId", type=int)
        result = get_client_poverty_prediction(batch_id=batch_id)

        return jsonify({
            "success": True,
            "message": "Poverty likelihood prediction generated successfully",
            "data": result
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Failed to compute poverty likelihood prediction",
            "error": str(e)
        }), 500


@app.route("/api/ppi/trends", methods=["GET"])
def ppi_trends():
    auth = require_login_api()
    if auth:
        return auth

    try:
        current_batch_id = request.args.get("currentBatchId", type=int)
        previous_batch_id = request.args.get("previousBatchId", type=int)

        result = get_ppi_trend_monitoring(
            current_batch_id=current_batch_id,
            previous_batch_id=previous_batch_id
        )

        return jsonify({
            "success": True,
            "message": "PPI trend monitoring generated successfully",
            "data": result
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Failed to compute PPI trends",
            "error": str(e)
        }), 500


@app.route("/api/ppi/poverty-movement", methods=["GET"])
def ppi_poverty_movement():
    auth = require_login_api()
    if auth:
        return auth

    try:
        current_batch_id = request.args.get("currentBatchId", type=int)
        previous_batch_id = request.args.get("previousBatchId", type=int)

        result = get_poverty_movement_dashboard(
            current_batch_id=current_batch_id,
            previous_batch_id=previous_batch_id
        )

        return jsonify({
            "success": True,
            "message": "Poverty movement monitoring generated successfully",
            "data": result
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Failed to compute poverty movement monitoring",
            "error": str(e)
        }), 500

#right table sa ppi likelihood
@app.route("/api/ppi/top-risk-factors", methods=["GET"])
def ppi_top_risk_factors():
    auth = require_login_api()
    if auth:
        return auth

    try:
        batch_id = request.args.get("batchId", type=int)
        top_n = request.args.get("top", default=10, type=int)

        result = get_top_poverty_risk_factors(
            batch_id=batch_id,
            top_n=top_n
        )

        return jsonify({
            "success": True,
            "message": "Top poverty risk factors generated successfully",
            "data": result
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Failed to compute top poverty risk factors",
            "error": str(e)
        }), 500
    
#Left table ng pppilikelihood
@app.route("/api/ppi/likelihood-table", methods=["GET"])
def ppi_likelihood_table():
    auth = require_login_api()
    if auth:
        return auth

    try:
        limit = request.args.get("limit", default=1000, type=int)
        search = request.args.get("search")
        branch_level = request.args.get("branchLevel")
        branch_value = request.args.get("branchValue")
        batch_id = request.args.get("batchId", type=int)

        result = get_ppi_likelihood_table(
            limit=limit,
            search=search,
            branch_level=branch_level,
            branch_value=branch_value,
            batch_id=batch_id
        )

        return jsonify({
            "success": True,
            "message": "PPI likelihood table generated successfully",
            "data": result
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Failed to load PPI likelihood table",
            "error": str(e)
        }), 500
    


@app.route("/api/ppi/client-profiles", methods=["GET"])
def ppi_client_profiles():
    auth = require_login_api()
    if auth:
        return auth

    try:
        limit = request.args.get("limit", default=1000, type=int)
        search = request.args.get("search")
        branch_level = request.args.get("branchLevel")
        branch_value = request.args.get("branchValue")

        result = get_client_poverty_profiles(
            limit=limit,
            search=search,
            branch_level=branch_level,
            branch_value=branch_value
        )

        return jsonify({
            "success": True,
            "message": "Client poverty profiles generated successfully",
            "data": result
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Failed to compute client poverty profiles",
            "error": str(e)
        }), 500

@app.route("/api/ppi/current-overview", methods=["GET"])
def ppi_current_overview():
    auth = require_login_api()
    if auth:
        return auth

    try:
        result = get_current_poverty_overview()

        return jsonify({
            "success": True,
            "message": "Current poverty overview generated successfully",
            "data": result
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Failed to compute current poverty overview",
            "error": str(e)
        }), 500       
    




# ===========================
#           SCHOLAR
# ===========================
@app.route("/api/scholarship/dashboard", methods=["GET"])
def scholarship_dashboard():
    auth = require_login_api()
    if auth:
        return auth

    try:
        batch_id = request.args.get("batchId", type=int)
        branch_level = request.args.get("branchLevel")
        branch_value = request.args.get("branchValue")
        limit = request.args.get("limit", default=100, type=int)

        result = get_scholarship_dashboard(
            batch_id=batch_id,
            branch_level=branch_level,
            branch_value=branch_value,
            limit=limit
        )

        return jsonify({
            "success": True,
            "message": "Scholarship dashboard generated successfully",
            "data": result
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Failed to generate scholarship dashboard",
            "error": str(e)
        }), 500


@app.route("/api/scholarship/recommendations", methods=["GET"])
def scholarship_recommendations():
    auth = require_login_api()
    if auth:
        return auth

    try:
        batch_id = request.args.get("batchId", type=int)
        branch_level = request.args.get("branchLevel")
        branch_value = request.args.get("branchValue")
        limit = request.args.get("limit", default=100, type=int)

        result = get_scholarship_recommendations(
            batch_id=batch_id,
            branch_level=branch_level,
            branch_value=branch_value,
            limit=limit
        )

        return jsonify({
            "success": True,
            "message": "Scholarship recommendations generated successfully",
            "data": result
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Failed to generate scholarship recommendations",
            "error": str(e)
        }), 500




# ===========================
#           RISK
# ===========================
@app.route("/api/risk/dashboard", methods=["GET"])
def risk_dashboard():
    auth = require_login_api()
    if auth:
        return auth

    try:
        batch_id = request.args.get("batchId", type=int)
        branch_level = request.args.get("branchLevel")
        branch_value = request.args.get("branchValue")
        top_limit = request.args.get("top", default=10, type=int)

        result = get_risk_dashboard(
            batch_id=batch_id,
            branch_level=branch_level,
            branch_value=branch_value,
            top_limit=top_limit
        )

        return jsonify({
            "success": True,
            "message": "Risk dashboard generated successfully",
            "data": result
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Failed to generate risk dashboard",
            "error": str(e)
        }), 500


@app.route("/api/risk/trend", methods=["GET"])
def risk_trend():
    auth = require_login_api()
    if auth:
        return auth

    try:
        current_batch_id = request.args.get("currentBatchId", type=int)
        previous_batch_id = request.args.get("previousBatchId", type=int)

        result = get_risk_trend(
            current_batch_id=current_batch_id,
            previous_batch_id=previous_batch_id
        )

        return jsonify({
            "success": True,
            "message": "Risk trend generated successfully",
            "data": result
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Failed to generate risk trend",
            "error": str(e)
        }), 500


@app.route("/api/risk/top-high-risk-clients", methods=["GET"])
def top_high_risk_clients():
    auth = require_login_api()
    if auth:
        return auth

    try:
        batch_id = request.args.get("batchId", type=int)
        branch_level = request.args.get("branchLevel")
        branch_value = request.args.get("branchValue")
        limit = request.args.get("limit", default=20, type=int)

        result = get_top_high_risk_clients(
            batch_id=batch_id,
            branch_level=branch_level,
            branch_value=branch_value,
            limit=limit
        )

        return jsonify({
            "success": True,
            "message": "Top high risk clients generated successfully",
            "data": result
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Failed to generate top high risk clients",
            "error": str(e)
        }), 500

@app.route("/api/risk/client-at-risk", methods=["GET"])
def client_at_risk_dashboard():
    auth = require_login_api()
    if auth:
        return auth

    try:
        batch_id = request.args.get("batchId", type=int)
        search = request.args.get("search")
        branch_level = request.args.get("branchLevel")
        branch_value = request.args.get("branchValue")
        risk_severity = request.args.get("riskSeverity")
        limit = request.args.get("limit", default=1000, type=int)

        result = get_client_at_risk_dashboard(
            batch_id=batch_id,
            search=search,
            branch_level=branch_level,
            branch_value=branch_value,
            risk_severity=risk_severity,
            limit=limit
        )

        return jsonify({
            "success": True,
            "message": "Client at-risk dashboard generated successfully",
            "data": result
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Failed to generate client at-risk dashboard",
            "error": str(e)
        }), 500    
    
@app.route("/api/risk/factors-overview", methods=["GET"])
def risk_factors_overview():
    auth = require_login_api()
    if auth:
        return auth

    try:
        current_batch_id = request.args.get("currentBatchId", type=int)
        previous_batch_id = request.args.get("previousBatchId", type=int)

        result = get_risk_factors_overview(
            current_batch_id=current_batch_id,
            previous_batch_id=previous_batch_id
        )

        return jsonify({
            "success": True,
            "message": "Risk factors overview generated successfully",
            "data": result
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Failed to generate risk factors overview",
            "error": str(e)
        }), 500    

# ===========================
#           RUN
# ===========================

if __name__ == "__main__":
    app.run(debug=True, port=5000)