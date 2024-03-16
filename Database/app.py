import psycopg2
from flask import Flask, render_template, request

app = Flask(__name__)
connect = psycopg2.connect("dbname= user= password=")
cur = connect.cursor()

@app.route('/')
def login():
    return render_template("login.html")

@app.route('/return', methods=['post'])
def return_login():
    return render_template("login.html")

def find_advertise():
    cur.execute("select code, count(code) from trade group by code order by count")
    code = cur.fetchall()
    cur.execute("select seller, count(seller) from trade group by seller order by count")
    sellers = cur.fetchall()
    if len(code) == 0 or len(sellers) == 0:
        return [('there', 'is', 'no', 'items', 'yet')]
    code = code[0][0]
    for seller in sellers:
        cur.execute("select * from items where code = '{}' and seller = '{}'".format(code, seller[0]))
        result = cur.fetchall()
        if len(result) > 0:
            return result

@app.route('/register', methods=['post'])
def register():
    id = request.form["id"]
    password = request.form["password"]
    send = request.form["send"]

    if send == 'login':
        cur.execute("select * from users where id = '{}' and password = '{}'".format(id, password))
        result = cur.fetchall()
        if len(result) == 0:
            return render_template("error_login.html", message='Login Failed!')
        else:
            cur.execute("select * from account where id = '{}'".format(result[0][0]))
            result = cur.fetchall()
            info1 = get_trade_info()
            info2 = get_items_info()
            advertise = find_advertise()
            return render_template("main.html", user_info=result[0], trade_info=info1, items_info=info2, advertise=advertise)

    if send == 'sign up':
        if len(id) < 1:
            return render_template("error_login.html", message='Sign up Failed!', announcement='Too short ID length.')
        cur.execute("select id from users where id = '{}'".format(id))
        result = cur.fetchall()
        if len(result) != 0:
            return render_template("error_login.html", message='Sign up Failed!', announcement='Same ID exists. Try again.')
        cur.execute("insert into users values('{}','{}')".format(id, password))
        cur.execute("insert into account values('{}', 10000, 'beginner')".format(id))
        connect.commit()
        return render_template("error_login.html", message='Sign up Success!')
    return render_template("login.html")

@app.route('/showInfo', methods=['post'])
def show_info():
    send = request.form["send"]
    if send == 'users info':
        cur.execute("select * from users")
    else:
        cur.execute("select * from trade")
    result = cur.fetchall()
    return render_template("show_info.html", type=send, infos=result)

@app.route('/return_home', methods=['post'])
def return_home():
    current_id = request.form["user_id"]
    cur.execute("select * from account where id = '{}'".format(current_id))
    result = cur.fetchall()
    info1 = get_trade_info()
    info2 = get_items_info()
    advertise = find_advertise()
    return render_template("main.html", user_info=result[0], trade_info=info1, items_info=info2, advertise=advertise)

def get_trade_info():
    cur.execute("select type from category "
                "where code in (with count_code as (select code, count(code) from trade group by code) "
                "select count_code.code from count_code "
                "where count_code.count = (select max(count_code.count) from count_code))")
    popular_item = cur.fetchall()
    cur.execute("with sum_buyer as (select buyer, sum(trade_price) from trade group by buyer) "
                " select sum_buyer.buyer from sum_buyer "
                "where sum_buyer.sum = (select max(sum_buyer.sum) from sum_buyer)")
    buyer_info = cur.fetchall()
    cur.execute("with sum_seller as (select seller, sum(trade_price) from trade group by seller) "
                " select sum_seller.seller from sum_seller "
                "where sum_seller.sum = (select max(sum_seller.sum) from sum_seller)")
    seller_info = cur.fetchall()
    infos = list([popular_item[0][0], buyer_info[0][0], seller_info[0][0]])
    return infos

def get_items_info():
    cur.execute("select * from items")
    result = cur.fetchall()
    return result

@app.route('/add_page', methods=['post'])
def show_add_page():
    current_id = request.form["user_id"]
    cur.execute("select * from category")
    category = cur.fetchall()
    return render_template("add_page.html", user=current_id, categories=category)

@app.route('/buy_page', methods=['post'])
def show_buy_page():
    current_id = request.form["user_id"]
    cur.execute("select * from account where id = '{}'".format(current_id))
    result = cur.fetchall()
    code = request.form["code"]
    name = request.form["name"]
    price = request.form["price"]
    stock = request.form["stock"]
    seller = request.form["seller"]
    extra = request.form["extra"]
    info = list([code, name, price, stock, seller])
    return render_template("buy_page.html", user_info=result[0], item_info=info, extra=extra)

@app.route('/add', methods=['post'])
def add_item():
    code = request.form["code"]
    name = request.form["name"]
    price = request.form["price"]
    stock = request.form["stock"]
    seller = request.form["seller"]

    cur.execute("select * from category where code = '{}'".format(code))
    result = cur.fetchall()
    if len(result) == 0:
        return render_template("fail.html", user=seller, tip='invalid code!')
    if name == "":
        return render_template("fail.html", user=seller, tip='invalid name!')
    if int(price) < 0 or int(stock) <= 0:
        return render_template("fail.html", user=seller, tip='invalid price or stock!')
    # price와 stock에 숫자가 아닌 다른 것이 들어갈 때는 고려하지 않았고, name이 없을 때도 예외처리하였다.

    cur.execute("select * from items where code='{}' and name='{}' and price={} and seller = '{}'"
                .format(code, name, price, seller))
    result = cur.fetchall()
    if len(result) != 0:
        cur.execute("update items "
                    "set stock = stock + {} "
                    "where code='{}' and name='{}' and price={} and seller = '{}'"
                    .format(stock, code, name, price, seller))
        connect.commit()
    else:
        cur.execute("insert into items values('{}', '{}', {}, {}, '{}')".format(code, name, price, stock, seller))
        connect.commit()
    return render_template("success.html", mode='add', user=seller)

@app.route("/confirm", methods=['post'])
def confirm():
    num = request.form["num"]
    code = request.form["code"]
    name = request.form["name"]
    price = request.form["price"]
    stock = request.form["stock"]
    seller = request.form["seller"]
    buyer = request.form["buyer"]
    extra = request.form["extra"]
    cur.execute("select * from account where id = '{}'".format(buyer))
    result = cur.fetchall()
    cur.execute("select discount from rating_info where rating = '{}'".format(result[0][2]))
    discount = cur.fetchall()
    totalPrice = int(num)*int(price)
    discountPrice = totalPrice * (float(discount[0][0]) + float(extra)) / 100

    if int(stock) < int(num):
        return render_template("fail.html", user=buyer, tip='not enough stock!')
    if totalPrice-discountPrice > int(result[0][1]):
        return render_template("fail.html", user=buyer, tip='not enough money!')
    if buyer == seller:
        return render_template("fail.html", user=buyer, tip='cannot buy yours!')
    if int(num) <= 0:
        return render_template("fail.html", user=buyer, tip='invalid amount to buy!')

    item = list([code, name, price, stock, seller])
    return render_template("confirm.html", num=num, totalPrice=totalPrice, discountPrice=discountPrice,
                           finalPrice=totalPrice-discountPrice, buyer=result[0], item_info=item, extra=extra)

@app.route("/buy", methods=['post'])
def buy_item():
    code = request.form["code"]
    name = request.form["name"]
    price = request.form["price"]
    stock = request.form["stock"]
    seller = request.form["seller"]
    buyer = request.form["buyer"]
    sellerPrice = request.form["sellerPrice"]
    buyerPrice = request.form["buyerPrice"]
    num = request.form["num"]

    cur.execute("update account set balance = balance - {} where id='{}'".format(buyerPrice, buyer))
    cur.execute("update account set balance = balance + {} where id='{}'".format(sellerPrice, seller))
    for user in [buyer, seller]:
        cur.execute("select balance from account where id = '{}'".format(user))
        balance = cur.fetchall()
        cur.execute("select rating from rating_info where condition <= {} order by condition desc".format(balance[0][0]))
        rating = cur.fetchall()
        cur.execute("update account set rating = '{}' where id = '{}'".format(rating[0][0], user))
    cur.execute("insert into trade values('{}', '{}', '{}', {})".format(buyer, seller, code, sellerPrice))
    newStock = int(stock) - int(num)
    if newStock == 0:
        cur.execute("delete from items where code='{}' and name='{}' and price={} and seller = '{}'"
                .format(code, name, price, seller))
    else:
        cur.execute("update items set stock = {} where code='{}' and name='{}' and price={} and seller = '{}'"
                .format(newStock, code, name, price, seller))
    connect.commit()
    return render_template("success.html", mode='buy', user=buyer)

@app.route("/my_page", methods=["post"])
def my_page():
    user = request.form["user"]
    cur.execute("select * from account where id = '{}'".format(user))
    user_info = cur.fetchall()
    cur.execute("select * from rating_info where condition > {} order by condition".format(user_info[0][1]))
    next_rating = cur.fetchall()
    if len(next_rating) == 0:
        next_rating = ('max level', '0', '2.50')
        need_money = 0
    else:
        next_rating = next_rating[0]
        need_money = int(next_rating[1]) - int(user_info[0][1])
    cur.execute("select * from trade where buyer = '{}'".format(user))
    buy_list = cur.fetchall()
    cur.execute("select count(trade_price), sum(trade_price) from trade where buyer = '{}'".format(user))
    buy_amount = cur.fetchall()
    cur.execute("select seller, count(seller) from trade where buyer='{}' group by (buyer, seller) order by count desc".format(user))
    best_buy_friend = cur.fetchall()
    if len(best_buy_friend) == 0:
        best_buy_friend = [['None'], ['0']]
    cur.execute("select * from trade where seller = '{}'".format(user))
    sell_list = cur.fetchall()
    cur.execute("select count(trade_price), sum(trade_price) from trade where seller = '{}'".format(user))
    sell_amount = cur.fetchall()
    cur.execute("select buyer, count(buyer) from trade where seller='{}' group by (buyer, seller) order by count desc".format(user))
    best_sell_friend = cur.fetchall()
    if len(best_sell_friend) == 0:
        best_sell_friend = [['None'], ['0']]

    return render_template("my_page.html", user_info=user_info[0], next_rating=next_rating, need_money=need_money,
                           buy_list=buy_list, buy_amount=buy_amount, best_buy_friend=best_buy_friend[0],
                           sell_list=sell_list, sell_amount=sell_amount, best_sell_friend=best_sell_friend[0])

@app.route("/fill_balance", methods=['post'])
def to_fill_balance():
    user = request.form["user"]
    balance = request.form["balance"]
    return render_template("fill_page.html", user=user, balance=balance)

@app.route("/fill_balance_confirm", methods=['post'])
def fill_balance():
    user = request.form["user"]
    amount = request.form["amount"]
    balance = request.form["balance"]
    new_balance = int(amount) + int(balance)
    if int(amount) <= 0:
        return render_template("fail.html", user=user, tip='charge amount must be more than 0!')
    cur.execute("update account set balance = {} where id = '{}'".format(new_balance, user))
    cur.execute("select rating from rating_info where condition <= {} order by condition desc".format(new_balance))
    rating = cur.fetchall()
    cur.execute("update account set rating = '{}' where id = '{}'".format(rating[0][0], user))
    connect.commit()
    return render_template("success.html", mode='charge', user=user)

if __name__ == '__main__':
    app.run()