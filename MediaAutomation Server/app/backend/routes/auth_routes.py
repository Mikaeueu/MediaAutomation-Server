from flask import Blueprint, render_template, request, redirect, session

auth_bp = Blueprint('auth', __name__)

USER = "midiadm"
PASS = "123321"

@auth_bp.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = request.form.get("user")
        password = request.form.get("password")

        if user == USER and password == PASS:
            session["logged"] = True
            return redirect("/dashboard")

    return render_template("login.html")