from flask import Flask, render_template, request, session, jsonify
# from Account import Account  ← uncomment when your friend is done

app = Flask(__name__)
app.secret_key = "polysekunda_secret_123"  # needed for sessions to work

# =====================
# DATA
# =====================

# Temporary fake accounts until Account.py is ready
# Replace this with real Account objects later
accounts = {
    "adam":  { "password": "1234", "balance": 1000 },
    "petra": { "password": "abcd", "balance": 1200 },
    "marek": { "password": "pass", "balance": 600  },
}

# Markets list - add more questions here
from market import Market

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
# LOGIN / LOGOUT
# =====================

@app.route("/login", methods=["POST"])
def login():
    data     = request.get_json()
    username = data.get("username", "").lower()
    password = data.get("password", "")

    # Check if account exists and password is correct
    if username in accounts and accounts[username]["password"] == password:
        session["user"] = username          # remember who is logged in
        return jsonify({
            "success":  True,
            "username": username,
            "balance":  accounts[username]["balance"]
        })
    else:
        return jsonify({ "success": False, "error": "Wrong username or password." })


@app.route("/logout", methods=["POST"])
def logout():
    session.pop("user", None)               # forget who was logged in
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
    # Must be logged in
    if "user" not in session:
        return jsonify({ "success": False, "error": "Not logged in." })

    data       = request.get_json()
    market_id  = data.get("market_id")
    choice     = data.get("choice")       # "yes" or "no"
    amount     = data.get("amount")

    username = session["user"]
    account  = accounts[username]

    # Validate
    if amount <= 0:
        return jsonify({ "success": False, "error": "Amount must be greater than 0." })
    if amount > account["balance"]:
        return jsonify({ "success": False, "error": "Not enough coins." })
    if market_id is None or market_id >= len(markets):
        return jsonify({ "success": False, "error": "Market not found." })

    market = markets[market_id]

    if market.resolved:
        return jsonify({ "success": False, "error": "Market is already closed." })

    # Place the bet
    account["balance"] -= amount
    market.bets[choice].append((username, amount))

    return jsonify({
        "success": True,
        "new_balance": account["balance"],
        "odds": market.get_odds(),
    })


# =====================
# LEADERBOARD
# =====================

@app.route("/leaderboard", methods=["GET"])
def leaderboard():
    players = [
        { "name": name, "coins": acc["balance"] }
        for name, acc in accounts.items()
    ]
    players.sort(key=lambda p: p["coins"], reverse=True)
    return jsonify(players)


# =====================
# RUN
# =====================

if __name__ == "__main__":
    app.run(debug=True)
