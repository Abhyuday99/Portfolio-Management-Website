import os
import datetime
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    uni = session["user_id"]
    Shares = db.execute("SELECT StockTicker,NumberofStocks FROM Portfolios WHERE CustomerId=:u", u = uni )
    User_PF = list()
    for row in Shares:
        Ticker = row["StockTicker"]
        Number = row["NumberofStocks"]
        Quote = lookup(row["StockTicker"])
        Price = Quote["price"]
        temp = (Ticker,Number,Price,Price * Number)
        User_PF.append(temp)
    Equity = 0
    for row in User_PF:
        Equity += row[3]
    C = db.execute("SELECT cash FROM users WHERE id = :u",u = uni)
    cash = C[0]["cash"]
    Equity += cash
    return render_template("index.html" , X = User_PF , cash = usd(cash) , Equity = usd(Equity))



@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""

    if request.method == "POST" :
        Stock = request.form.get("symbol")
        if not Stock or not lookup(Stock) :
            return apology("Invalid StockSymbol.Please try again")
        try :
            Number = float(request.form.get("shares"))
        except ValueError :
            return apology("Please input numerical value")
        if not Number :
            return apology("Please input desired number of stocks")

        elif Number < 1 or ((Number*10) % 10) != 0 :
            return apology("Invalid number of stocks")
        uni = session["user_id"]
        Buyer_cash = db.execute("SELECT cash FROM users WHERE id = :u",u = uni)
        cash = Buyer_cash[0]["cash"]
        Price = lookup(Stock)["price"]
        if  cash <  Price * Number :
            return apology("Insufficient funds.Sorry")
        a = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        db.execute("INSERT INTO Transactions (StockTicker,StockPrice,NumberofStocks,Time,CustomerId,BUYorSELL) VALUES(:x,:y,:z,:t,:b,:c)",x=Stock,y=usd(Price),z=Number,t= a,b=uni , c = "BUY")
        db.execute("UPDATE users SET cash = :c WHERE id = :u",c = cash - Price * Number , u=uni)
        P = db.execute("SELECT StockTicker FROM Portfolios WHERE CustomerId = :u ",u = uni)
        for row in P :
            if Stock == row["StockTicker"] :
                db.execute("UPDATE Portfolios SET NumberofStocks = NumberofStocks + :n WHERE StockTicker = :o AND CustomerId = :u",n = Number , o =Stock,u=uni)
                return redirect("/")

        db.execute("INSERT INTO Portfolios (CustomerId,StockTicker,NumberofStocks) VALUES(:u,:o,:n)",u = uni , o = Stock , n=Number )
        flash(f"You successfully bought {Number} shares of {Stock}")
        return redirect("/")

    else :
        return render_template("/buy.html")

@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():

        uni = session["user_id"]
        if request.method == "POST" :

            Stock = request.form.get("symbol")
            Check = db.execute("SELECT * FROM Portfolios WHERE CustomerId = :u AND StockTicker = :v",u = uni , v = Stock)
            if not Stock or not Check :
                return apology("Invalid StockSymbol.Please try again")
            try :
                Number = float(request.form.get("shares"))
            except ValueError :
                return apology("Please input numerical value")
            if not Number :
                return apology("Please input desired number of stocks")

            elif Number < 1 or ((Number*10) % 10) != 0 :
                return apology("Invalid number of stocks")

            elif Check[0]["NumberofStocks"] < Number :
                return apology("You do not own sufficient number of shares")
            Buyer_cash = db.execute("SELECT cash FROM users WHERE id = :u",u = uni)
            cash = Buyer_cash[0]["cash"]
            Price = lookup(Stock)["price"]
            DollarPrice = usd(Price)
            Datetime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            db.execute("INSERT INTO Transactions(StockTicker,StockPrice,NumberofStocks,Time,CustomerId,BUYorSELL) VALUES(:a,:b,:c,:d,:u,:t)",a = Stock,b=usd(Price),c=Number,d=Datetime,u = uni , t = "SELL")
            db.execute("UPDATE users SET cash = :p WHERE id = :u",p = cash + Price * Number , u = uni )
            db.execute("UPDATE Portfolios SET NumberofStocks = :n WHERE CustomerId = :u AND StockTicker = :v", n =Check[0]["NumberofStocks"] - Number,u = uni,v = Stock)

            flash(f"You successfully sold {Number} shares of {Stock} for {DollarPrice}")
            return redirect("/")

        else :
            List = db.execute("SELECT StockTicker FROM Portfolios WHERE CustomerId = :u " , u = uni )
            return render_template("/sell.html",List = List)

@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    History = db.execute("SELECT StockTicker,StockPrice,NumberofStocks,Time,BUYorSELL FROM Transactions WHERE CustomerId = :u " , u = session["user_id"] )
    return render_template("/history.html",History = History)

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

@app.route("/changepassword", methods=["GET", "POST"])
@login_required
def changepassword():
    """Register user"""

    uni = session["user_id"]
    if request.method == "POST" :


        OldPassword = request.form.get("oldpassword")
        Password = request.form.get("newpassword")
        Users = db.execute("SELECT * FROM users WHERE id = :u " , u = uni)

        if not OldPassword  or  not check_password_hash(Users[0]["hash"], OldPassword):
            return apology("Cannot proceed without oldpassword")
        elif not Password or not Password == request.form.get("confirmation") :
            return apology("Please check your password")

        db.execute("UPDATE users SET hash = :h WHERE id = :u ",h = generate_password_hash(Password) , u = uni)
        return redirect("/")

    else :
        return render_template("/changepassword.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "POST" :
        Ticker = request.form.get("symbol")
        if not Ticker :
            return apology("Please input a stock symbol")
        Stockdata = lookup(Ticker)
        if not Stockdata :
            return apology("Invalid stock symbol")

        return render_template("/quoted.html",name = Stockdata["name"] , symbol = Stockdata["symbol"] , price = usd(float(Stockdata["price"])))

    else :
        return render_template("/quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    session.clear()
    if request.method == "POST" :

        Username = request.form.get("username")
        Password = request.form.get("password")

        Users = db.execute("SELECT * FROM users WHERE username = :x " , x = Username)
        if not Username  or  len(Users) != 0 :
            return apology("Didnt provide username or already exists")
        elif not Password or not Password == request.form.get("confirmation") :
            return apology("Please check your password")

        db.execute("INSERT INTO users (username,hash) VALUES(:Username,:hash)",Username = Username,hash = generate_password_hash(Password))
        return redirect("/")

    else :
        return render_template("register.html")




def errorhandler(e):
    """Handle error"""
    return apology(e.name, e.code)


# listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
