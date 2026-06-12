from flask import Flask, render_template, request, session, jsonify
from user_data import Database
from Market import Market

app = Flask(__name__)
app.secret_key = "polysekunda_secret_123"  # needed for sessions to work

# =====================
# DATA
# =====================

db = Database()

# Create some starting accounts (later this could come from a signup page)
db.add_user("adam", "1234")
db.add_user("petra", "abcd")
db.add_user("marek", "pass")

markets = [
    Market("Will Slovakia beat Czechia?"),
    Market("Will our class pass the math test?"),
    Market("Will it rain in Prievidza this weekend?"),
]


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
        return jsonify({
            "logged_in": True,
            "username": username,
            "balance": user["balance"]
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
            "balance":  user["balance"]
        })
    else:
        return jsonify({ "success": False, "error": "Wrong username or password." })


@app.route("/logout", methods=["POST"])
def logout():
    session.pop("user", None)
    return jsonify({ "success": True })


# =====================
# MARKETS
# =====================

@app.route("/markets", methods=["GET"])
def get_markets():
    result = []
    for i, market in enumerate(markets):
        odds = market.get_odds()
        result.append({
            "id":       i,
            "question": market.question,
            "yes_pct":  odds["yes"],
            "no_pct":   odds["no"],
            "resolved": market.resolved,
            "winner":   market.winner,
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

    if amount <= 0:
        return jsonify({ "success": False, "error": "Amount must be greater than 0." })
    if amount > user["balance"]:
        return jsonify({ "success": False, "error": "Not enough coins." })
    if market_id is None or market_id >= len(markets):
        return jsonify({ "success": False, "error": "Market not found." })

    market = markets[market_id]

    if market.resolved:
        return jsonify({ "success": False, "error": "Market is already closed." })

    user["balance"] -= amount
    market.bets[choice].append((username, amount))

    return jsonify({
        "success": True,
        "new_balance": user["balance"],
        "odds": market.get_odds(),
    })


# =====================
# LEADERBOARD
# =====================

@app.route("/leaderboard", methods=["GET"])
def leaderboard():
    players = [
        { "name": user["username"], "coins": user["balance"] }
        for user in db.userlist
    ]
    players.sort(key=lambda p: p["coins"], reverse=True)
    return jsonify(players)


# =====================
# RUN
# =====================

if __name__ == "__main__":
    app.run(debug=True)
