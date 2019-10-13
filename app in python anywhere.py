from flask import Flask, render_template, flash, redirect, url_for, session, request
#from data import Cards #imports function Cards in data.py
from flaskext.mysql import MySQL#pip install flask-mysql
from pymysql.cursors import DictCursor
from wtforms import Form, StringField, TextAreaField, PasswordField, validators, widgets, SelectField, SelectMultipleField
from passlib.hash import sha256_crypt
from functools import wraps #pip install jaraco.itertools
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

# Config mysql
app.config['MYSQL_DATABASE_HOST'] = 'ieatzinc.mysql.pythonanywhere-services.com'
app.config['MYSQL_DATABASE_USER'] = 'ieatzinc'
#login in to mysql with: mysql -u root;, select database myflaskapp, then wtv
app.config['MYSQL_DATABASE_PASSWORD'] = 'sprouts2244'
app.config['MYSQL_DATABASE_DB'] = 'ieatzinc$myflaskapp'
#app.config['MYSQL_DB'] = 'myflaskapp'
#heroku uri postgres://goelzacpynjyrb:a1fa813562ae6
#efb194978a7b3de9e56398f218f086322d7faead5a9b1245024@ec2-54-243-241-62.compute-1.amazonaws.com:5432/darahtdqkrviiv


#initalize MySQL
mysql = MySQL(app, cursorclass=DictCursor)
#Cards = Cards() #makes variable equal to return value of function, before using card database

@app.route('/')
def index():
    return render_template("home.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/cards")
def cards():
    #create cursor, execute, commit, close
    cur = mysql.get_db().cursor()
    result = cur.execute("SELECT * FROM cards")#view cards?
    cards = cur.fetchall()

    if bool(result) == True:
        return render_template('cards.html', cardZ = cards)
    else:
        msg = "No Cards Found"
        return render_template('cards.html', msg = msg)
    cur.close()

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#functions for scraping
#class RestaurantOverallRating is called when the card is viewed, returns the aggregate ratings
class RestaurantOverallRating:
    myRestName = ""
    yelpOverall= 0
    opentableOverall = 0
    googleOverall = 0
    def __init__(self, givenRestName):
        self.myRestName = givenRestName
        #get restaurant chosen from mysql database
        cur = mysql.get_db().cursor()
        cur.execute("SELECT * FROM restaurants WHERE name_location=%s", [givenRestName])
        restaurantInDB = cur.fetchone()
        self.yelpOverall = restaurantInDB['y_rating']
        self.opentableOverall = restaurantInDB['o_rating']
        self.googleOverall = restaurantInDB['g_rating']


        cur.close()

    def updateOverallRatings(self):
        cur = mysql.get_db().cursor()
        cur.execute("SELECT * FROM restaurants WHERE name_location=%s", [self.myRestName])
        restaurantInDB = cur.fetchone()

        cur.close()

        #sets google rating
        if restaurantInDB['g_url'] != "":
            response = requests.get(restaurantInDB['g_url'])
            soup = BeautifulSoup(response.text, 'html.parser')
            ratingObj = soup.find(class_="oqSTJd")#encrypted word for rating
            self.googleOverall = (ratingObj.get_text())
            cur = mysql.get_db().cursor()
            cur.execute("UPDATE restaurants SET g_rating=%s WHERE name_location=%s", [self.googleOverall, self.myRestName])
            mysql.get_db().commit()
            cur.close()
        else:
            cur = mysql.get_db().cursor()
            cur.execute("UPDATE restaurants SET g_rating=0 WHERE name_location=%s", [self.myRestName])
            mysql.get_db().commit()
            cur.close()

        #sets yelp rating
        if restaurantInDB['y_url'] != "":
            response = requests.get(restaurantInDB['y_url'])
            soup = BeautifulSoup(response.text, 'html.parser')
            print(soup)
            self.yelpOverall = soup.find(itemprop="aggregateRating").find_next().get('content')
            cur = mysql.get_db().cursor()
            cur.execute("UPDATE restaurants SET y_rating=%s WHERE name_location=%s", [self.yelpOverall, self.myRestName])
            mysql.get_db().commit()
            cur.close()
        else:
            cur = mysql.get_db().cursor()
            cur.execute("UPDATE restaurants SET y_rating=0 WHERE name_location=%s", [self.myRestName])
            mysql.get_db().commit()
            cur.close()

        #sets open table rating
        if restaurantInDB['o_url'] != "":
            print("~~~~a~~~~~~")
            response = requests.get(restaurantInDB['o_url'])
            print("~~~~b~~~~~~")
            soup = BeautifulSoup(response.text, 'html.parser')
            self.opentableOverall = soup.find(itemprop="ratingValue").get('content')
            cur = mysql.get_db().cursor()
            cur.execute("UPDATE restaurants SET o_rating=%s WHERE name_location=%s", [self.opentableOverall, self.myRestName])
            mysql.get_db().commit()
            cur.close()
        else:
            cur = mysql.get_db().cursor()
            cur.execute("UPDATE restaurants SET o_rating=0 WHERE name_location=%s", [self.myRestName])
            mysql.get_db().commit()
            cur.close()
#class RestaurantReviews: called when restaurant is added(w/ urls)
class RestaurantReviews:
    myRestName = ""
    y_url = ''
    o_url = ''
    # constructor stores all reviews onto mysql databases
    def __init__(self, givenRestName):
        self.myRestName = givenRestName
        #get restaurant chosen from mysql database
        cur = mysql.get_db().cursor()
        cur.execute("SELECT * FROM restaurants WHERE name_location=%s", [givenRestName])
        restaurantInDB = cur.fetchone()
        cur.close()
        self.y_url = restaurantInDB['y_url']
        self.o_url = restaurantInDB['o_url']

    def storeAllReviews(self):
        #use soup to fetch then commit each review
        #repeat for yelp and open table, if url != ''

        if self.y_url != "":
            print("adding yelps")
            num = 0
            sNum = 20
            while sNum==20 and num<=380:#all pages w/ 20 reviews
                sNum = 0
                response = requests.get(self.y_url + '?start=%s&sort_by=date_desc' % num)
                soup = BeautifulSoup(response.text, 'html.parser')
                reviewList = soup.findAll(itemprop="author")
                for review in reviewList:
                    num = 1+num
                    sNum = 1+sNum
                    yelp_rating = review.find_next_sibling().find_next().get('content')#rating
                    yelp_date = review.find_next_sibling().find_next_sibling().get('content')#date
                    yelp_author = review.get('content') #author

                    cur = mysql.get_db().cursor()
                    cur.execute('INSERT INTO yelp_reviews(restaurant, date, rating, author) VALUES(%s, %s, %s, %s)', (self.myRestName, yelp_date, yelp_rating, yelp_author))
                    mysql.get_db().commit()
                    cur.close()
                print("\n %s" % num)

            print("FINISHED yelps")

        #store all open table reviews
        if self.o_url != "":
            print("adding opentables")
            num = 0
            sNum = 40
            while sNum==40 and num<=400:
                sNum = 0
                response = requests.get(self.o_url + '?page=%s' % (1+ num/40))#each page has 40 reviews, num/40 gives page number based on reviews counted
                soup = BeautifulSoup(response.text, 'html.parser')
                reviewList = soup.findAll(class_="oc-reviews-47b8de40")
                for review in reviewList:
                    num = 1+num
                    sNum = 1+sNum
                    opentable_date = review.find_parent().find_parent().find_parent().find_next_sibling().find_next_sibling().find_next_sibling().get('content')#date
                    if opentable_date == None:
                        opentable_date = review.find_parent().find_parent().find_parent().find_next_sibling().find_next_sibling().find_next_sibling().find_next_sibling().find_next_sibling().get('content')#date when restaurant replies
                    opentable_rating = review.find_next().get('content')#rating
                    opentable_author = review.find_previous().find_parent().find_parent().find_parent().find_previous().find_previous().find_previous().find_previous().find_previous().get_text()#author


                    cur = mysql.get_db().cursor()
                    cur.execute('INSERT INTO opentable_reviews(restaurant, date, rating, author) VALUES(%s, %s, %s, %s)', (self.myRestName, opentable_date, opentable_rating, opentable_author))
                    mysql.get_db().commit()
                    cur.close()

            print("FINISHED opentables")

    def updateAllReviews(self):
        self.deleteAllReviews()
        cur = mysql.get_db().cursor()
        cur.execute("UPDATE restaurants SET last_updated = CURRENT_TIMESTAMP WHERE name_location = %s", [self.myRestName])
        mysql.get_db().commit()
        cur.close()
        self.storeAllReviews()

    def deleteAllReviews(self):
        #test by storing all reviews, then manually delete newest ones in mysql
        cur = mysql.get_db().cursor()
        cur.execute("DELETE FROM yelp_reviews WHERE restaurant = %s", [self.myRestName])
        cur.execute("DELETE FROM opentable_reviews WHERE restaurant = %s", [self.myRestName])
        mysql.get_db().commit()
        cur.close()

    #getters of the reviews
    def getYelp(self):
        cur = mysql.get_db().cursor()
        cur.execute("SELECT * FROM yelp_reviews WHERE restaurant = %s" % self.myRestName)
        reviewList = cur.fetchall()
        cur.close()
        return reviewList

    def getOpentable(self):
        cur = mysql.get_db().cursor()
        cur.execute("SELECT * FROM opentable_reviews WHERE restaurant = %s" % self.myRestName)
        reviewList = cur.fetchall()
        cur.close()
        return reviewList
        #then -->return in render template, for x in reviewList:  x['date'],etc



#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
class GraphForm(Form):
    graph_rest = SelectField('Change Graph To:', choices=[])

#single cards
@app.route("/viewCard/<string:id>/", methods=['GET', 'POST']) #<string:id> is to utlize dynamic value
def viewCard(id):
    #create cursor, execute, commit, close
    cur = mysql.get_db().cursor()
    #get card
    cur.execute("SELECT * FROM cards WHERE id=%s", [id])
    cardToView = cur.fetchone()
    #get restaurants in card
    cur.execute("SELECT restaurant_name FROM card_restaurant WHERE card_id=%s", [id])
    restListOfID = cur.fetchall()
    #create list of restNetReview objects
    restListOnCard = []
    for x in restListOfID:
        #print(x['restaurant_name'])
        restListOnCard.append(RestaurantOverallRating(x['restaurant_name']))

    #graph calulations begin~~~
    graph_date_list =[]
    yelp_rating_list = []
    opentable_rating_list = []
    graph_restaurant = ''
    #set restaurant to graph
    cur.execute("SELECT * FROM card_restaurant WHERE card_id=%s", [id])
    result = cur.fetchone()
    if bool(result) == True:#code only runs if card has one or more restaurants chosen
        graph_restaurant = result['rest_to_graph']
        cur.execute("SELECT * FROM restaurants WHERE name_location=%s", graph_restaurant)
        graph_url = cur.fetchone()
        #variables for yelp and opentable are valid
        isValid_yelp = False
        isValid_opentable = False
        if not graph_url['y_url']=='':
            isValid_yelp = True
        if not graph_url['o_url']=='':
            isValid_opentable = True
        #make sure theres a url for yelp or opentable, if so, run code to calculate graph points
        if isValid_yelp or isValid_opentable:
            #make sure the date for curr and tail are on a valid url
            #set curr and tail dates
            if not isValid_yelp:
                cur.execute("SELECT * FROM opentable_reviews WHERE restaurant=%s ORDER BY date", (graph_restaurant))
            else:
                cur.execute("SELECT * FROM yelp_reviews WHERE restaurant=%s ORDER BY date", (graph_restaurant))
            curr = cur.fetchone()
            curr = str(curr['date']).split('-') #curr[0] is year, [1] is month, i made to int
            curr = [int(float(curr[0])), int(float(curr[1])), int(float(curr[2]))]
            if not isValid_yelp:
                cur.execute("SELECT * FROM opentable_reviews WHERE restaurant=%s ORDER BY date DESC", (graph_restaurant))
            else:
                cur.execute("SELECT * FROM yelp_reviews WHERE restaurant= %s ORDER BY date DESC", (graph_restaurant))
            tail= cur.fetchone()
            tail = str(tail['date']).split('-')
            tail = [int(tail[0]), int(tail[1]), int(tail[2])]
            #gather monthly averages for both sites
            avgRateOT=0
            avgRateY=0
            while True:
                while curr[1] < 13:
                    if isValid_yelp:
                        cur.execute("SELECT * FROM yelp_reviews WHERE restaurant = %s AND YEAR(date)=%s AND MONTH(date)=%s", (graph_restaurant, curr[0], curr[1]))
                        tempList = cur.fetchall()
                        totalRate=0
                        numOfRate=0
                        for g in tempList:
                            totalRate = totalRate + int(g['rating'])
                            numOfRate = numOfRate + 1
                        if not numOfRate == 0:
                            avgRateY = totalRate*1.0/numOfRate
                        yelp_rating_list.append(avgRateY)
                    #repeat for opentable
                    if isValid_opentable:
                        cur.execute("SELECT * FROM opentable_reviews WHERE restaurant = %s AND YEAR(date)=%s AND MONTH(date)=%s", (graph_restaurant, curr[0], curr[1]))
                        tempList = cur.fetchall()
                        totalRate=0
                        numOfRate=0
                        for g in tempList:
                            totalRate = totalRate + int(g['rating'])
                            numOfRate = numOfRate + 1
                        if not numOfRate == 0:
                            avgRateOT = totalRate*1.0/numOfRate
                        opentable_rating_list.append(avgRateOT)




                    graph_date_list.append(str(curr[0]) + "-" + str(curr[1]))
                    if curr[1]==tail[1] and curr[0]==tail[0]:
                        break
                    curr[1] = curr[1] + 1
                if curr[1]==tail[1] and curr[0]==tail[0]:
                    break
                curr[1] = 1
                curr[0] = curr[0]+1
    #end of graph calculations~~~~

    #start selection for choose a new graph
    form = GraphForm(request.form)
    form.graph_rest.choices = [(restaurant['restaurant_name'], restaurant['restaurant_name']) for restaurant in restListOfID]

    if request.method == 'POST' and form.validate():
        graph_restaurant = form.graph_rest.data
        cur.execute("UPDATE card_restaurant SET rest_to_graph =%s WHERE card_id=%s", (graph_restaurant,[id]))
        mysql.get_db().commit()
        return redirect(request.url)




    cur.close()
    return render_template("viewCard.html", cardX = cardToView, restListOnCard=restListOnCard,graph_date_list=graph_date_list, yelp_rating_list=yelp_rating_list,opentable_rating_list=opentable_rating_list, graph_restaurant=str(graph_restaurant+ " Review Trends"), form=form)

graph_me = ''
listOfUsernames = []
def takenUsernames():
    #creates list of usernames
    cur = mysql.connect().cursor()
    cur.execute("SELECT * FROM users")
    data = cur.fetchall()
    cur.close()
    for tName in data:
        #if False == (tName in listOfUsernames): ---realisticly, allowing duplicates is more efficient than searching the list
        listOfUsernames.append(tName['username'])

class RegisterForm(Form):
    name = StringField('Name', [validators.Length(min =1, max=50)])
    username = StringField('Username', [
        validators.Length(min =4, max=25),
        validators.NoneOf(listOfUsernames ,message = 'Username Taken')#unique username checker
    ])
    email = StringField('Email', [validators.Length(min =6, max = 50)])
    password = PasswordField('Password', [
        validators.DataRequired(),
        validators.EqualTo('confirm', message = 'Passwords do not matchh')
    ])
    confirm = PasswordField('Confirm Password')

@app.route('/register', methods=['GET', 'POST'])
def register():
    takenUsernames()
    form = RegisterForm(request.form)
    #print(app.config)
    if request.method == 'POST' and form.validate():#wtforms using
        name = form.name.data
        email = form.email.data
        user = form.username.data
        password = sha256_crypt.encrypt(str(form.password.data))#encrpyt password

        #Create cursor
        cur = mysql.get_db().cursor() #used to execute commands
        # print(cur)

        #execute qurrey
        cur.execute('INSERT INTO users(name, email, username, password) VALUES(%s, %s, %s, %s)', (name, email, user, password))

        #commit to database
        mysql.get_db().commit()

        #close connection
        cur.close()

        flash('You are now registered and can log in.', 'success')
        return redirect(url_for("login"))
        #register user and all that
    return render_template('register.html', form = form)#passing in the 3 lines above form

#user login
@app.route('/login', methods=["GET", "POST"])
def login():
    if request.method == 'POST' :
        #get Form fields        not using wtforms for this part
        username = request.form['username']
        password_candidate = request.form['password']

        #create cursor
        cur = mysql.get_db().cursor()

        #get user by Username
        result = cur.execute("SELECT * FROM users WHERE username = %s", [username])#this username is the username made above there

        if bool(result): #if username at all is entered
            #get stored hash (encrpyed pass?)
            #looks at querey in result, fetching first thing, finding first acc of Username
            data = cur.fetchone()
            password = data['password']
            #password = data['password']
            #related to dictcursor

            #compare passwords -----check if this command is old
            if sha256_crypt.verify(password_candidate, password):
                #app.logger.info('PASSWORD MATCHED')
                session['logged_in']=  True
                session['username']= username #from the form Username

                flash('You are now logged in', 'success')
                return redirect(url_for('dashboard'))
            else:
                error = 'Invalid login'
                return render_template('login.html', error=error)
            cur.close()
        else:
            error = 'Username not found....'
            return render_template('login.html', error=error)

    return render_template('login.html')

#check if user logged in(so they cant just edit url)
def is_logged_in(f):#takes in parameter f
    @wraps(f)#pass in f value
    def wrap(*args, **kwargs):#put logic here
        if 'logged_in' in session:
            return f(*args, **kwargs)#return f with the things
        else:
            flash('Unauthorized, Please log in first', 'danger')
            return redirect(url_for('login'))
    return wrap

@app.route('/logout')
@is_logged_in
def logout():
    session.clear()#clears session?
    flash("Logged out", 'success')
    return redirect(url_for('login'))

@app.route('/dashboard')
@is_logged_in
def dashboard():
    #create cursor, execute, commit, close
    cur = mysql.get_db().cursor()
    cardResult = cur.execute("SELECT * FROM cards")
    cards = cur.fetchall()
    restResult = cur.execute("SELECT * FROM restaurants")
    restaurantZ = cur.fetchall()
    if bool(restResult) and bool(cardResult):
        return render_template('dashboard.html', cardZ = cards, restaurantZ = restaurantZ)
    elif bool(restResult):
        msg = "No Cards Found"
        return render_template('dashboard.html', msg = msg, restaurantZ = restaurantZ)
    elif bool(cardResult):
        msg = "No Restaurants Found"
        return render_template('dashboard.html', msg = msg, cardZ = cards)
    else:
        msg = "No Cards or Restaurants Found"
        return render_template('dashboard.html', msg = msg)
    cur.close()

    return render_template('dashboard.html')

class MultiCheckboxField(SelectMultipleField):
    """
    A multiple-select, except displays a list of checkboxes.

    Iterating the field will produce subfields, allowing custom rendering of
    the enclosed checkbox fields.
    """
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()

#add card using wtforms
class CardForm(Form):
    title = StringField('Title', [validators.Length(min =1, max = 100)])
    body = TextAreaField('Body', [validators.Length(min =30)])
    restName = MultiCheckboxField('Restaurants', choices=[])

#add card using wtforms
@app.route('/add_card', methods =['GET', 'POST'])
@is_logged_in
def add_card():
    form = CardForm(request.form)
    #create dynamic list of restaurants to choose from

    cur = mysql.get_db().cursor()
    cur.execute("SELECT name_location FROM restaurants ORDER BY name_location ASC")
    restaurantList = cur.fetchall()

    form.restName.choices = [(restaurant['name_location'], restaurant['name_location']) for restaurant in restaurantList]
    cur.close()



    if request.method == 'POST' and form.validate():
        title = form.title.data
        body = form.body.data
        restName = form.restName.data
        #create cursor, execute, commit, close
        cur = mysql.get_db().cursor()
        cur.execute("INSERT INTO cards(title,body,author) VALUES(%s, %s, %s)", (title,body,session['username']))
        cur.execute("SELECT * FROM cards ORDER BY id DESC LIMIT 1")
        last_card = cur.fetchone()
        for x in restName:
            cur.execute("INSERT INTO card_restaurant(card_id, restaurant_name, rest_to_graph) VALUES (%s, %s, %s)", (last_card['id'], x.split("'")[0], x.split("'")[0]))

        mysql.get_db().commit()
        cur.close()
        #flash message
        flash('Card Created', 'success')
        return redirect(url_for('dashboard'))

    return render_template('add_card.html', form=form)

#edit Card
@app.route('/edit_card/<string:id>', methods =['GET', 'POST'])
@is_logged_in
def edit_card(id):

    cur = mysql.get_db().cursor()
    cur.execute("SELECT * FROM cards WHERE id = %s", [id])#get card by id
    cardEdit = cur.fetchone()#get specific card

    #check if valid author to edit
    page_username = cardEdit['author']
    if page_username != session['username']:
        flash("You can't edit other user's cards!", 'danger')
        return redirect(url_for('dashboard'))


    form = CardForm(request.form)#get Form FORMAT

    #create choices
    cur.execute("SELECT name_location FROM restaurants ORDER BY name_location ASC")
    restaurantList = cur.fetchall()
    #find choices from last time
    cur.execute("SELECT * FROM card_restaurant WHERE card_id=%s", [id])
    oldRestListRaw = cur.fetchall()
    oldRestList = []
    for z in oldRestListRaw:
        oldRestList.append(z['restaurant_name'])
    #populate card form fields from last submission
    form.title.data = cardEdit['title']
    form.body.data = cardEdit['body']
    form.restName.choices = [(restaurant['name_location'], restaurant['name_location']) for restaurant in restaurantList]
    form.restName.data = oldRestList

    cur.close()
    if request.method == 'POST':
        #these 3 lines get the data in the input boxes currently
        form.title.data = request.form['title']
        form.body.data = request.form['body']
        form.restName.data = request.form.getlist('restName')
        #confirms input data is valid
        if form.validate():
            #create cursor, execute, commit, close
            #update title/body
            cur = mysql.get_db().cursor()
            cur.execute("UPDATE cards SET title= %s, body=%s, update_date= SYSDATE() WHERE id = %s", ([form.title.data,form.body.data,id]))

            #reset restaurant/card correlations
            cur.execute("DELETE FROM card_restaurant WHERE card_id = %s", [id])
            for x in form.restName.data:
                cur.execute("INSERT INTO card_restaurant(card_id, restaurant_name, rest_to_graph) VALUES (%s, %s, %s)",
                ([id], x.split("''"), x.split("''")))
            #close cursor
            mysql.get_db().commit()
            cur.close()
            #flash message
            flash('Card updated', 'success')
            return redirect(url_for('dashboard'))
    return render_template('edit_card.html', form=form)

listOfRestNames = []#prevents duplicate restaurant entries, similar to preventing duplicate users
def takenRestNames():
    #listOfRestNames = []
    cur = mysql.connect().cursor()
    cur.execute("SELECT * FROM restaurants")
    data = cur.fetchall()
    cur.close()
    for x in data:
        listOfRestNames.append(x['name_location'])


#add card using wtforms
class RestaurantForm(Form):
    title = StringField('Restaurant Name and location', [validators.NoneOf(listOfRestNames, message = 'Restaurant identifier is already taken'), validators.Length(min =1, max = 100)])
    yelp_url = StringField('Yelp URL', [
        validators.Optional(),
        validators.URL(message='Invalid url, leave blank if none exists.')] )
    open_table_url = StringField('Open Table URL', [
        validators.Optional(),
        validators.URL(message='Invalid url, leave blank if none exists.')] )
    google_url = StringField('Google URL', [
        validators.Optional(),
        validators.URL(message='Invalid url, leave blank if none exists.')] )


#add restaurant using wtforms
@app.route('/add_restaurant', methods =['GET','POST'])
@is_logged_in
def add_restaurant():
    takenRestNames()
    form = RestaurantForm(request.form)
    if request.method == 'POST' and form.validate():
        title = form.title.data
        title = title.replace("\'", "")
        yelp_url = form.yelp_url.data
        open_table_url = form.open_table_url.data
        open_table_url = open_table_url.split("?")[0]
        if open_table_url != '':
            open_table_url = "http://oauth" + open_table_url.split('https://www')[1]

        google_url = form.google_url.data
        #create cursor, execute, commit, close
        cur = mysql.get_db().cursor()
        cur.execute("INSERT INTO restaurants(name_location,y_url,o_url,g_url, author) VALUES(%s, %s, %s, %s, %s)", (title,yelp_url.split("?")[0], open_table_url,google_url, session['username']))#default add current time, in edit_restaurant, update time
        mysql.get_db().commit()
        print("~~~~~~~~~~~~~~~~~~~~~~~~~")
        #commit the restaurant urls, then upload ratings
        newRest = RestaurantOverallRating(title)
        newRest.updateOverallRatings()
        cur.execute("UPDATE restaurants SET y_rating=%s, g_rating=%s, o_rating=%s WHERE name_location=%s", (newRest.yelpOverall, newRest.googleOverall, newRest.opentableOverall, title))
        mysql.get_db().commit()
        cur.close()

        #testing yelp review add to db
        RestaurantReviews(title).updateAllReviews()
        RestaurantOverallRating(title).updateOverallRatings()

        #flash message
        flash('Restaurant Added', 'success')
        return redirect(url_for('dashboard'))

    return render_template('add_restaurant.html', form=form)


#delete card
@app.route('/delete_card/<string:id>', methods = ['POST'])
@is_logged_in
def delete_card(id):
    cur = mysql.get_db().cursor()
    #delete from card_restaurant related entries, then delete the card itself
    cur.execute("DELETE FROM card_restaurant WHERE card_id = %s", [id])
    cur.execute("DELETE FROM cards WHERE id = %s", [id])
    mysql.get_db().commit()
    cur.close()
    #flash message
    flash('Card Deleted', 'success')
    return redirect(url_for('dashboard'))

#delete restaurant
@app.route('/delete_restaurant/<string:restName>', methods = ['POST'])
@is_logged_in
def delete_restaurant(restName):
    cur = mysql.get_db().cursor()
    #delete anything dependent on the restaurant
    RestaurantReviews(restName).deleteAllReviews()
    cur.execute("DELETE FROM card_restaurant WHERE restaurant_name = %s", [restName])
    cur.execute("DELETE FROM restaurants WHERE name_location = %s", [restName])
    mysql.get_db().commit()
    cur.close()
    #flash message
    flash('Restaurant Deleted', 'success')
    for x in listOfRestNames:
        if x == restName:
            listOfRestNames.remove(restName)
    return redirect(url_for('dashboard'))

@app.route('/update_restaurant/<string:restName>', methods = ['POST'])
@is_logged_in
def update_restaurant(restName):
    #begin the updating and yelp is slow lol
    RestaurantReviews(restName).updateAllReviews()
    #flash message
    flash('Restaurant Graph Data Updated', 'success')
    return redirect(url_for('dashboard'))

@app.route('/update_restaurant_overall/<string:restName>', methods = ['POST'])
@is_logged_in
def update_restaurant_overall(restName):
    RestaurantOverallRating(restName).updateOverallRatings()
    #flash message
    flash('Restaurant Aggregate Ratings Updated', 'success')
    return redirect(url_for('dashboard'))

@app.route('/update_restaurant_overall_all/', methods = ['POST'])
@is_logged_in
def update_restaurant_overall_all():
    cur = mysql.get_db().cursor()
    cur.execute("SELECT * FROM restaurants")
    allRestaurant_db = cur.fetchall()
    for x in allRestaurant_db:
        RestaurantOverallRating(x['name_location']).updateOverallRatings()
    #flash message
    flash('All Aggregate Ratings Updated', 'success')
    return redirect(url_for('dashboard'))



app.secret_key= 'secret123'
if __name__ == '__main__':
    app.secret_key= 'secret123'
    app.run()
