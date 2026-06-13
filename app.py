from flask import Flask, render_template, request, session, jsonify
from user_data import Database

app = Flask(__name__)
app.secret_key = "polysekunda_secret_123"  # needed for sessions to work

# =====================
# DATA
# =====================

db = Database()

# Create starting accounts only if they don't exist yet
# if db.find_user("adam") is None:
#     db.add_user("adam", "1234")
# if db.find_user("petra") is None:
#     db.add_user("petra", "abcd")
# if db.find_user("marek") is None:
#     db.add_user("marek", "pass")

# Admin account - change this password!
if db.find_user("admin") is None:
    db.add_user("admin", "admin123", is_admin=True)

# Markets - only inserted if they don't already exist (won't duplicate on restart)
# db.add_market(0, "Will Slovakia beat Czechia?")


# =====================
# HELPER: calculate odds from bets
# =====================

def calculate_odds(bets):
    yes_total = sum(b["amount"] for b in bets if b["choice"] == "yes")
    no_total  = sum(b["amount"] for b in bets if b["choice"] == "no")
    total = yes_total + no_total

    if total == 0:
        return {"yes": 50, "no": 50}

    yes_pct = round((yes_total / total) * 100)
    return {"yes": yes_pct, "no": 100 - yes_pct}


# =====================
# PAGES
# =====================

@app.route("/")
def home():
    return render_template("index.html")


# =====================
# SESSION CHECK
# =====================

@app.route("/check-session")
def check_session():
    if "user" in session:
        username = session["user"]
        user = db.find_user(username)
        if user is None:
            session.pop("user", None)
            return jsonify({ "logged_in": False })
        return jsonify({
            "logged_in": True,
            "username": username,
            "balance": user["balance"],
            "is_admin": bool(user["is_admin"])
        })
    return jsonify({ "logged_in": False })


# =====================
# LOGIN / LOGOUT
# =====================

@app.route("/login", methods=["POST"])
def login():
    data     = request.get_json()
    username = data.get("username", "").lower()
    password = data.get("password", "")

    user = db.find_user(username)

    if user is not None and user["password"] == password:
        session["user"] = username
        return jsonify({
            "success":  True,
            "username": username,
            "balance":  user["balance"],
            "is_admin": bool(user["is_admin"])
        })
    else:
        return jsonify({ "success": False, "error": "Wrong username or password." })


@app.route("/logout", methods=["POST"])
def logout():
    session.pop("user", None)
    return jsonify({ "success": True })


@app.route("/create-account", methods=["POST"])
def create_account():
    data     = request.get_json()
    username = data.get("username", "").lower().strip()
    password = data.get("password", "")

    if username == "" or password == "":
        return jsonify({ "success": False, "error": "Username and password required." })

    created = db.add_user(username, password)
    if not created:
        return jsonify({ "success": False, "error": "Username already taken." })

    session["user"] = username

    return jsonify({
        "success": True,
        "username": username,
        "balance": 1000,
        "is_admin": False
    })


# =====================
# MARKETS
# =====================

@app.route("/markets", methods=["GET"])
def get_markets():
    result = []
    for market in db.get_all_markets():
        bets = db.get_bets_for_market(market["id"])
        odds = calculate_odds(bets)

        # Find the current user's bets on this market (if logged in)
        my_bets = []
        if "user" in session:
            my_bets = [b for b in bets if b["username"] == session["user"]]

        result.append({
            "id":       market["id"],
            "question": market["question"],
            "yes_pct":  odds["yes"],
            "no_pct":   odds["no"],
            "resolved": bool(market["resolved"]),
            "winner":   market["winner"],
            "my_bets":  [{"choice": b["choice"], "amount": b["amount"]} for b in my_bets]
        })
    return jsonify(result)


# =====================
# BETTING
# =====================

@app.route("/bet", methods=["POST"])
def place_bet():
    if "user" not in session:
        return jsonify({ "success": False, "error": "Not logged in." })

    data       = request.get_json()
    market_id  = data.get("market_id")
    choice     = data.get("choice")
    amount     = data.get("amount")

    username = session["user"]
    user     = db.find_user(username)
    market   = db.get_market(market_id)

    if market is None:
        return jsonify({ "success": False, "error": "Market not found." })
    if amount <= 0:
        return jsonify({ "success": False, "error": "Amount must be greater than 0." })
    if amount > user["balance"]:
        return jsonify({ "success": False, "error": "Not enough coins." })
    if market["resolved"]:
        return jsonify({ "success": False, "error": "Market is already closed." })
    if choice not in ("yes", "no"):
        return jsonify({ "success": False, "error": "Invalid choice." })

    new_balance = user["balance"] - amount
    db.update_balance(username, new_balance)
    db.add_bet(market_id, username, choice, amount)

    bets = db.get_bets_for_market(market_id)
    odds = calculate_odds(bets)

    return jsonify({
        "success": True,
        "new_balance": new_balance,
        "odds": odds,
    })


# =====================
# RESOLVE MARKET (admin only)
# =====================

@app.route("/resolve", methods=["POST"])
def resolve_market():
    if "user" not in session:
        return jsonify({ "success": False, "error": "Not logged in." })

    user = db.find_user(session["user"])
    if not user["is_admin"]:
        return jsonify({ "success": False, "error": "Admin only." })

    data      = request.get_json()
    market_id = data.get("market_id")
    outcome   = data.get("outcome")  # "yes" or "no"

    market = db.get_market(market_id)
    if market is None:
        return jsonify({ "success": False, "error": "Market not found." })
    if market["resolved"]:
        return jsonify({ "success": False, "error": "Already resolved." })
    if outcome not in ("yes", "no"):
        return jsonify({ "success": False, "error": "Outcome must be yes or no." })

    bets = db.get_bets_for_market(market_id)
    winning_bets = [b for b in bets if b["choice"] == outcome]
    losing_bets  = [b for b in bets if b["choice"] != outcome]

    losing_pool  = sum(b["amount"] for b in losing_bets)
    winning_pool = sum(b["amount"] for b in winning_bets)

    for bet in winning_bets:
        bettor = db.find_user(bet["username"])
        if winning_pool > 0:
            share = bet["amount"] / winning_pool
            payout = round(bet["amount"] + share * losing_pool)
        else:
            payout = bet["amount"]
        db.update_balance(bet["username"], bettor["balance"] + payout)

    db.resolve_market(market_id, outcome)

    return jsonify({ "success": True })


# =====================
# ADMIN: CREATE / DELETE MARKET
# =====================

@app.route("/create-market", methods=["POST"])
def create_market():
    if "user" not in session:
        return jsonify({ "success": False, "error": "Not logged in." })

    user = db.find_user(session["user"])
    if not user["is_admin"]:
        return jsonify({ "success": False, "error": "Admin only." })

    data     = request.get_json()
    question = data.get("question", "").strip()

    if question == "":
        return jsonify({ "success": False, "error": "Question cannot be empty." })

    new_id = db.create_market(question)
    return jsonify({ "success": True, "id": new_id })


@app.route("/delete-market", methods=["POST"])
def delete_market():
    if "user" not in session:
        return jsonify({ "success": False, "error": "Not logged in." })

    user = db.find_user(session["user"])
    if not user["is_admin"]:
        return jsonify({ "success": False, "error": "Admin only." })

    data      = request.get_json()
    market_id = data.get("market_id")

    market = db.get_market(market_id)
    if market is None:
        return jsonify({ "success": False, "error": "Market not found." })

    db.delete_market(market_id)
    return jsonify({ "success": True })


# =====================
# LEADERBOARD
# =====================

@app.route("/leaderboard", methods=["GET"])
def leaderboard():
    users = db.get_all_users()
    players = [
        { "name": u["username"], "coins": u["balance"] }
        for u in users
    ]
    players.sort(key=lambda p: p["coins"], reverse=True)
    return jsonify(players)


# =====================
# RUN
# =====================

if __name__ == "__main__":
    app.run(debug=True)
