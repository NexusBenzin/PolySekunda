class Market:
    def __init__(self, question):
        self.question = question
        self.bets = {"yes": [], "no": []}
        self.resolved = False
        self.winner = None

    def place_bet(self, account, choice, amount):
        choice = choice.lower()

        if choice not in ("yes", "no"):
            print("Invalid choice. Please bet 'yes' or 'no'.")
            return

        if self.resolved:
            print("This market is already closed.")
            return

        if amount <= 10:
            print("Bet amount must be greater than 0.")
            return

        if account.bal < amount:
            print(f"Not enough balance! You have {account.bal} coins.")
            return

        account.bal -= amount
        self.bets[choice].append((account, amount))
        print(f"{account.name} bet {amount} coins on '{choice}' for: {self.question}")

    def get_odds(self):
        yes_total = sum(amount for _, amount in self.bets["yes"])
        no_total = sum(amount for _, amount in self.bets["no"])
        total = yes_total + no_total

        if total == 0:
            return {"yes": 50, "no": 50}

        yes_pct = round((yes_total / total) * 100)
        no_pct = 100 - yes_pct
        return {"yes": yes_pct, "no": no_pct}

    def resolve(self, outcome):
        outcome = outcome.lower()

        if outcome not in ("yes", "no"):
            print("Outcome must be 'yes' or 'no'.")
            return

        if self.resolved:
            print("Market already resolved.")
            return

        self.resolved = True
        self.winner = outcome


        winning_bets = self.bets[outcome]
        losing_bets = self.bets["yes" if outcome == "no" else "no"]

        losing_pool = sum(amount for _, amount in losing_bets)
        winning_pool = sum(amount for _, amount in winning_bets)

        print(f"\nMarket resolved! Answer: '{outcome}'")
        print(f"Question: {self.question}")

        if winning_pool == 0:
            print("Nobody bet on the winning side. No payouts.")
            return

        for account, amount in winning_bets:
            share = amount / winning_pool
            payout = round(amount + share * losing_pool)
            account.bal += payout
            print(f"  {account.name} wins {payout} coins! (new balance: {account.bal})")

    def show(self):
        odds = self.get_odds()
        status = "CLOSED" if self.resolved else "OPEN"
        yes_total = sum(amount for _, amount in self.bets["yes"])
        no_total = sum(amount for _, amount in self.bets["no"])

        print(f"\n[{status}] {self.question}")
        print(f"  YES: {odds['yes']}%  ({yes_total} coins bet)")
        print(f"  NO:  {odds['no']}%  ({no_total} coins bet)")
        if self.resolved:
            print(f"  Winner: {self.winner.upper()}")
