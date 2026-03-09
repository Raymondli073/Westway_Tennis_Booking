"""
Flask web app — subscribe/unsubscribe for Westway Tennis Alerts.
Serves both:
  - HTML pages for browser users
  - JSON API for WeChat Mini Program
"""

from __future__ import annotations

import re
from flask import Flask, request, redirect, render_template, url_for, jsonify

from app.db import init_db, subscribe, unsubscribe, count

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

app = Flask(__name__, template_folder="templates", static_folder="static")


@app.before_request
def setup():
    init_db()


# ── HTML routes (browser) ────────────────────────────────────────────────────

@app.route("/")
def index():
    message      = request.args.get("msg")
    message_type = request.args.get("type", "info")
    MSG_MAP = {
        "subscribed":         ("You're subscribed! You'll receive alerts when consecutive slots open up.", "success"),
        "already_subscribed": ("That email is already subscribed.", "info"),
        "invalid_email":      ("Please enter a valid email address.", "error"),
    }
    if message in MSG_MAP:
        message, message_type = MSG_MAP[message]
    elif not message:
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
            sub_body="You won't receive any more notifications. Re-subscribe any time.",
        )
    return render_template(
        "result.html",
        icon="🤔",
        title="Link not found",
        body="This unsubscribe link is invalid or has already been used.",
        sub_body=None,
    ), 404


# ── JSON API (WeChat Mini Program) ───────────────────────────────────────────

def _cors(response):
    response.headers["Access-Control-Allow-Origin"]  = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


@app.route("/api/subscribe", methods=["POST", "OPTIONS"])
def api_subscribe():
    if request.method == "OPTIONS":
        return _cors(app.make_response(""))

    data  = request.get_json(silent=True) or {}
    email = data.get("email", "").strip()

    if not EMAIL_RE.match(email):
        return _cors(jsonify({"ok": False, "code": "invalid_email",
                              "message": "请输入有效的邮箱地址"}))

    ok, result = subscribe(email)
    messages = {
        "subscribed":         "订阅成功！有连续空档时我们会发邮件通知您。",
        "already_subscribed": "该邮箱已订阅。",
    }
    return _cors(jsonify({
        "ok":      ok or result == "already_subscribed",
        "code":    result,
        "message": messages.get(result, result),
        "count":   count(),
    }))


@app.route("/api/unsubscribe", methods=["POST", "OPTIONS"])
def api_unsubscribe():
    if request.method == "OPTIONS":
        return _cors(app.make_response(""))

    data  = request.get_json(silent=True) or {}
    token = data.get("token", "").strip()
    if not token:
        return _cors(jsonify({"ok": False, "message": "缺少 token"}))

    ok, payload = unsubscribe(token)
    if ok:
        return _cors(jsonify({"ok": True,  "message": f"{payload} 已取消订阅"}))
    return _cors(jsonify({"ok": False, "message": "链接无效或已使用"}))


@app.route("/api/stats")
def api_stats():
    return _cors(jsonify({"count": count()}))
