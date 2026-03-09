"""
Flask web app — subscribe/unsubscribe interface for Westway Tennis Alerts.
"""

from __future__ import annotations

import re
from flask import Flask, request, redirect, render_template, url_for

from app.db import init_db, subscribe, unsubscribe, count

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

app = Flask(__name__, template_folder="templates", static_folder="static")


@app.before_request
def setup():
    init_db()


@app.route("/")
def index():
    message      = request.args.get("msg")
    message_type = request.args.get("type", "info")
    MSG_MAP = {
        "subscribed":        ("You're subscribed! You'll receive alerts when consecutive slots open up.", "success"),
        "already_subscribed":("That email is already subscribed.", "info"),
        "invalid_email":     ("Please enter a valid email address.", "error"),
    }
    if message in MSG_MAP:
        message, message_type = MSG_MAP[message]
    elif message:
        pass
    else:
        message = None

    return render_template(
        "index.html",
        message=message,
        message_type=message_type,
        subscriber_count=count(),
    )


@app.route("/subscribe", methods=["POST"])
def subscribe_route():
    email = request.form.get("email", "").strip()
    if not EMAIL_RE.match(email):
        return redirect(url_for("index", msg="invalid_email"))

    _, result = subscribe(email)
    return redirect(url_for("index", msg=result))


@app.route("/unsubscribe")
def unsubscribe_route():
    token = request.args.get("token", "")
    ok, payload = unsubscribe(token)

    if ok:
        return render_template(
            "result.html",
            icon="👋",
            title="Unsubscribed",
            body=f"{payload} has been removed from the alerts list.",
            sub_body="You won't receive any more notifications. You can re-subscribe any time.",
        )
    else:
        return render_template(
            "result.html",
            icon="🤔",
            title="Link not found",
            body="This unsubscribe link is invalid or has already been used.",
            sub_body=None,
        ), 404
