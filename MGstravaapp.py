#
# Copyright @ 2019 Michael George All Rights Reserved - MGstravaapp.py
#
# strava API demo program @(python 3.7)
#
# this will run without modification and prompt for the required Strava authentication elements. It will dump all Strava
#  data for the athlete associated with the secrets you enter (ID and SECRET) come from your strava account settings API page.
#    prompt 1 will be: Strava Client ID:  12345
#    prompt 2 will be: Strava Client_Secret: XXXXXXXXXXXXXX  (careful of the spaces at the end. it's a hex string with NO spaces)
#    prompt 3 will ask: do you want to enter an App Code or <enter> to open a browser. Just <enter> to Open the browser
#             then COPY the number from the code=AAAAAAAAAAAA portion of the strava-generated response URL
#    prompt 4 will ask: enter the App Code from the URL: AAAAAAAAAAA (again careful of no spaces!)
#    App should execute and dump the activity for the athlete.
#
# Optionally you can code values in variables immediately after these comments with your secrets
#
#  This source was constructed from various web discussions related to implementing an app based on STRAVA API
#  I use the standard python 'requests' module and the API examples on Strava.com
#  *some lessons learned*
#  **Authentication** is not part of the'strava api' it is a protocol based on oAuth standard and uses a combination of strava user profile
#    identifying code values (CLIENTID and CLIENT_SECRET) and a runtime handshake between strava and a hypothetical 'app server' which generates an (App Code)
#    derived from those two secrets. 
#    Those three values are prerequisite to a Strava API request which returns a runtime validated Access Code which enables every API action request.
#
#    For my testing I used strava docs' proposed localhost proto testing, where one step is to use a a web page and strava returns a fail, but with 
#     the necessary strava App Code in the failed URL of the browser. This utility will auto-generate the URL and open a browser, user must manually
#     import the App Code which is embedded in the failed URL. 
#     A little clumsy but works 100% reliably.
#    See my StravaAPIauthenticator class. Tough to find a full explicit since strava API call is the request to get valid runtime Access Code but the
#    larger authentication scheme is oAuth model using the account secrets, not any Strava coding instruction.
#     
#   In any case, proper authentication produces a runtime-validated ACCESS TOKEN which is mandatory element in any user API requests.
#
#  **REST and python url 'requests' module- first time using these. a couple of interesting behaviors unfamiliar to me 
#  the query args in the requests may be critical for success- for example the API request to get list of activities
#    in my test data (athlete John Doe) there were about 700 activities (bike rides, runs, swims, workouts, etc). The
#    requests have a (web-page) data model of N items per-page (an integer) and Page N request (an integer). by trial-and error I learned
#    if I omit those query items I got zero activities returned. if I put &per-page=800, &page=1, I got nothing
#    so I iteratively grab per-page=199 and iterated until no items were returned. this worked. I didn't find clear
#    documentation of the rules for per-page count. I believe it is an underlying protocol per-request data size limit so be aware of this.
#
#  **regarding Strava API request frequency & limits.
#   Strava imposes a "< 30,000 requests per day,  < 600 requests per 15 minutes" I dealt with this in the core
#     api request method below. if a request is not successful (typically due to violating the limts), sleep(30) and try again. 
#     this seemed highly stable and you can see in the Strava user login SETTINGS | it has API status monitor where the requests 
#     grow to 600..610 and stop, then t each :00 :15 :30 :45 minute threshold the limit resets & events start showing up again on the activity view
#  
#  **Windows standard output  print() limitations for non-ASCII characters. you'll see in my mgtextout() how I dealt with this. 
#     anyhow, trying to print() a string with UTF-8 or other emoji encoding will cause an exception... I didn't fully 
#     deal with it, but I do manage to avoid exceptions and put out the string text with in-line hex-display corresponding to the embedded emoji  
#
#  **I started out trying the stravalib github project. it works but doesn't clarify the authenticator algorithm and the 
#    API requests return custom objects that to me are more complex than the very simple '.json()' dictionary returned directly 
#    from the direct strava api via python 'requests' module. So I abandoned using that python/git strava module. this is my code.
#    For reference, I included a StravaData-stravalibdemoapp.py that demonstrates the entire authenticate and get activity sequence based on that
#    existing git/stravalib project.
#
#    This MGstravaapp.py does full dump of athelete activities including secondary items like laps, segments, splits... 
#
#   mg 2019-11-15 cleaned up to run turnkey unmodified with all test code disabled. comments reviewed.
#                 release as v1.0 in git
#
import requests as r
import time 
import sys
import codecs
from datetime import datetime

#
## M O D I F Y these values to change redirection behavior; enable and define path for a log file
DOREDIRECTION = False
BASEPATH = "y:/"

## M O D I F Y these values to enable the Strava authentication
# the ID & Secret MUST come from your strava online acct API Settings page 
# IF YOU PLUG IN CONSTANTS ID & SECRET, app will ask for the App Code derived from a URL as described above
# IF YOU PLUG IN CONSTANTS ID & SECRET & APP CODE, app will run without any challenges
M1_STRAVA_CLIENT_ID= None #'' #you can code your value here if you want for a local copy
M1_STRAVA_CLIENT_SECRET= None # '' #you can code your value here if you want for a local copy
# the App Code is derived in 2 steps if you don't already have one
#   1) call the URL generator in the api using (CLIENT_ID, CLIENT_SECRET)
#   2) make an http request (in a browser) using the URL generated in step 1. 
#       in absence of a legit oAUTH server, this request fails but STRAVA re-forms the URL to include the required App Code 
M1_APP_CODE = None #'' # you have to get it from Web once, but you can code your value here if you want for a local copy until it expires (24 hrs)

# use simple stdout redirection to create a .CSV file
class MG_OutputRedirect:
    def __init__(self, redirfile, otherflags=0):
        self.stdout = None
        self.makestdoutredirect(redirfile)

    def makestdoutredirect(self,basetag,resetredirection=False ):
            if  resetredirection:  #just reset any existing redirect
                if self.stdout:
                    sys.stdout = self.stdout
                    self.stdout = None
                return 

            # change BASEPATH if you want output to different location 
            fname = BASEPATH+"%s-%d-%s.csv"%(basetag,logtyperadioval,(datetime.now()).strftime("%Y-%m-%d-%H-%M-%S"))  #,self.gettimedaystr())
            try:
                #print("starting redir")
                if self.stdout != sys.stdout:
                    if self.stdout:
                        self.stdout.close()
                self.stdout = sys.stdout
                print("opening %s"% fname)
                sys.stdout = open(fname, 'w')
                return fname
            except:
                #print("ending redir")
                if sys.stdout:
                    self.stdout = None
                print("MGU-stdout redirect failed: ", fname)
                return None
                


defaultcodes = {'1':(M1_STRAVA_CLIENT_ID,M1_STRAVA_CLIENT_SECRET,M1_APP_CODE), '2':('','','')}
# *** some notes about Strava API authentication. it is based on OAUTH ietf rfc for web transaction authetication****
# the strava api is based multiple security values which are derived to succeed with API web data request (the runtime Access Code)
# 1) Application ClientID is static in strava user's API settings page (i.e. login to your online acct and read this number)
# 2) Application ClientSecret from strava user's API settings page (i.e. login to your online acct and read this number)
# 3) an intermediate App Code value is required; it is Strava-generated by this authentication sequence with 24hr life. 
#      A legit implementation would handshake with oAuth app server to deliver the App Code to the runtime. In this proto test, 
#      the Localhost model is used as described in strava SDK docs (LOCALHOST 127.0.0.1) This proto method is reliable to manually  
#      establish a valid App Code. See the StravaAPIauthenticator() class below which uses codes (1) and (2) to construct a URL/ http request.
#      The request fails but the web request results in a re-formed URL containing the necessary App Code.
#      The failed page URL looks like this and includes embedded code that user can manually cut/paste into the runtime prompt:
#           http://127.0.0.1:5000/authorization?state=&code=24e1f74f22105a98159688b9816d47b659e4650a&scope=read,activity:read
#     the only use for this 'failed url' is to extract the code=<value> ; in this example value is
#                                                                24e1f74f22105a98159688b9816d47b659e4650a
#     This App Code value is used with valid user client_id and client_secret to derive the Access Code (4) 
# 4)  An Access Code is returned during a runtime strava API call (a method here in StravaAPIauthenticator.saa_validatedstravatoken())
#     Each of the Authetnicator class methods below is a few lines and transparently shows STRAVA API details. The Access Code is
#     mandatory for every API user data request.
# 
#   NOTE that the App Code (#3) can be reused (not required to regenerate it every time) although it does have a shelf life. It can be reused
#     to generate Access Code in repeated program executions (and - the whole Cut/Paste cycle isn't as ugly as it sounds).
#
# this class implements the methods required to establish a valid Access Code during application runtime.
# if App Code is already available, reuse it (it's an optional clientcode arg to instantiate this, it can be hardcoded at top of this file);
# if no App Code, then step3 is required to obtain and App Code from Strava. 
# After the App Code is present, the authentication is completed by a call to Strava API to get a validated Access Code
class StravaAPIauthenticator():
    def __init__(self, clientcode=None):
        self.clientid= defaultcodes['1'][0] #clientid
        self.clientsecret= defaultcodes['1'][1] #clientsecret
        if not clientcode:
            self.clientcode = defaultcodes['1'][2] # clientcode from strava URL
        else:
            self.clientcode = clientcode
        self.accesstoken = None
        if not self.clientcode: #if we got a code in the instantiation, don't go through the secrets sequence
            retstat = self.saa_getsecrets()
            if not self.clientcode:
                print('failed getsecrets')
                return 
        retstat = self.saa_validatedstravatoken(self.clientid,self.clientsecret,self.clientcode)
        if retstat:
            #print('success with token',self.accesstoken)
            return
        print('failed validatetoken')
        return  #we failed

    # there would be a commercial user interface for getting these secrets in a deployed app. not part of this app.
    # this is a very rudimentary sequence to allow a user to enter their CLIENT_ID and CLIENT_SECRET provided via
    # access to their standard strava athlete web account. then it opens the web page where strava posts a URL with 'code'
    def saa_getsecrets(self):
        val1 = input("enter CLIENT_ID from your strava acct or hit <enter key> if you coded a value: ").strip()
        if not val1 =='':
            self.clientid=val1  #this comes from Strava user's standard login 'SETTINGS'|'API' page
        val1 = input("enter CLIENT_SECRET from your strava acct or hit <enter key> if you coded a value: ").strip()
        if not val1 =='':
            self.clientsecret=val1  #this comes from Strava standard login 'SETTOMGS'|'API' page

        requesturl = self.saa_constructrequesturl(self.clientid, self.clientsecret)
        #print("****  current app code-request URL: ***",requesturl)
        #print("The browser will open this page if you simply press <enter> (Recommended)")
        #print("Either enter your App Code or <enter> to popup browser with request URL")
        print("NOTE - You MUST be logged in to athlete's strava web account for the URL request to function")
        print("   After the browser opens (given valid secrets), it should display \"Unable To Connect can’t establish a connection to the server at 127.0.0.1:5000\"")
        print("   In this normal outcome, the resulting URL in the browser has a valid App Code embedded in it at 'code=nnnnnnnnnnnnnnnnnnnnnnnnn'")
        print("   Such a URL looks like this: http://127.0.0.1:5000/authorization?state=&code=24e1f74f22105a98159688b9816d47b659e4650a&scope=read,activity:read")
        print("          in this example your App Code would be 24e1f74f22105a98159688b9816d47b659e4650a  COPY/ PASTE it into the next App Code prompt")
        print("   ** IF your CLIENT ID or CLIENT SECRET are invalid, the browser will display corresponding \"Bad Request\" (clientid or clientsecret) message.")
        inval = input('Press <Enter> to open the browser request page (or you can enter an App Code if you got one earlier):').strip()
        if not inval == '':
            self.clientcode=inval
        else:
            import webbrowser
            webbrowser.open( requesturl, new=2)
            inval = input("Enter the App Code value from browser URL (copy/paste the Code=-->0000000000000<---- value: ").strip()
            if inval == '':
              print('Failed to enter an app code')
              return 
            else:
              self.clientcode = inval
              return 

    # this method returns the validated access token if this instance run the protocol to derive one
    def saa_getaccesstoken(self):
        return self.accesstoken

    # this method constructs/ returns to caller the specific strava URL which will respond by posting a URL (and failed page request) 
    # invoking browser. that strava-posted url contains the App code= xxxxxx  required for the API call to get a valid access token.
    def saa_constructrequesturl(self, clientid, clientsecret):
        # construct the CODE request xxURL query from strava
        self.coderequesturl='https://www.strava.com/oauth/authorize?client_id=%s&response_type=code&redirect_uri=%s&approval_prompt=auto&scope=read,activity:read'%(self.clientid,'http://127.0.0.1:5000/authorization')
        return self.coderequesturl

    # this method executes protocol to return a Strava-validated accesstoken using query url syntax defined in strava api authentication docs 
    # and examples. A successful query includes an athlete's unique static CLIENT_ID and CLIENT_SECRET from user Strava Settings API page,
    # a successful query also includes a current temporary CODE returned from the code request url constructed from the same clientID Strava
    #
    #  
    def saa_validatedstravatoken(self,clientid,clientsecret,clientcode):
        # the specific Strava POST URL query to get a validated accesstoken given an athlete clientid,clientsecret,code
        request_url= "https://www.strava.com/oauth/token?client_id=%s&client_secret=%s&code=%s&grant_type=authorization_code"%(clientid, clientsecret, clientcode)
        resp = r.post(request_url)
        if not resp.ok:
            print("Failed to validate token: ", resp)
            return False
        # make the response into a structure I can decode to extract authenticated, validated token 
        respdata = resp.json()
        self.accesstoken = respdata['access_token']
        return True


# Strava API class construct requests, invoke web transaction, decode responses and display data in .CSV usable lines output
# 
# Class is fully working prototype. all the output converter functions should either be moved into this class, 
#  or they should be replaced with more efficient/ integral python converters
class StravaCSVgenerator:
    def __init__(self, stravaaccesstoken, redirectionfile=None):
        if not stravaaccesstoken:
            return False  #mandatory! 
            #accesstoken = StravaAPIauthenticator()
            #self.stravaapipost() # an already authenticated athlete accesstoken
        self.requestcounterper15min = 0 # we'll track requests per 15 minutes strava limit is 600 & per day limit is 30,000
        self.requestcounterper24hr = 0
        self.base15mins = None # put in a base time
        self.accesstoken = stravaaccesstoken
        self.activity_response = None
        self.activity_ids = []
        self.athlete_response = None
        self.redirectionfile = redirectionfile
        pass

    # make a generic STRAVA web API request for any given STRAVA api function
    # All requests require an **already-authenticated** strava.com access token in this instance
    def stravaapirequest(self, request_url, maxretries=20, retrydelay=30):
        for retrycount in range(maxretries):
            # r.get is in the standard python request library
            #print('url',request_url,'token',self.accesstoken)
            request = r.get(request_url, 
                             headers={'Authorization': 'Bearer %s'%self.accesstoken}) #access token is associated with athelete
            respdata = request.json()
            if request.status_code == 200:
                return True, respdata  # return good response
            else:
                print(request, request_url)
                pass #print('failed',request)
            if True :#self.redirectionfile != None:
                print("API request failed; retrying... #", retrycount)
            time.sleep(retrydelay)
        return False, None #retry count expired without success

    # the STRAVA Get List of Activities request. gets all activities for the authenticated Athlete
    def strava_getactivities(self):        
        page = 1
        while True:   
            # get page of activities from Strava
            stat,respdata = self.stravaapirequest(
                request_url="https://www.strava.com/api/v3/athlete/activities?per_page=199&page="+str(page))
                # "Authorization: Bearer [[access_token['access_token']]]"    
                #request_header={'Authorization': 'Bearer %s'%self.accesstoken },
                #maxretries=10, retrydelay=30 )
            rlen = len(respdata)
            if not rlen:
                break 
            # build a list of activity IDs
            for activityid in respdata:
                self.activity_ids.append(activityid['id'])
            #self.activities_response.append(respdata)
            page += 1
        self.activity_pages = page
        return self.activity_ids
        # r = requests.get(url + '?' + access_token + '&per_page=50' + '&page=' + str(page))

    # the STRAVA Get Activity Detail by ID request for currently authenticated athlete
    def strava_activityrequest(self, activity_n):
        stat,respdata = self.stravaapirequest(
                request_url="https://www.strava.com/api/v3/activities/%d?include_all_efforts="%activity_n)
                # "Authorization: Bearer [[access_token['access_token']]]"    
                #request_header={'Authorization': 'Bearer %s'%self.accesstoken },
                #maxretries=10, retrydelay=30 )
        if stat:
            self.activity_response = respdata
        else:
            self.activity_response= None
        return stat, self.activity_response

    # Strava API Get Athlete info for currently authenticated athlete
    def stravaathleterequest(self):
        stat,respdata = self.stravaapirequest( request_url = "https://www.strava.com/api/v3/athlete")
        #header = {'Authorization': 'Bearer %s'%self.accesstoken }
        #self.athlete_response = r.get(url, headers=header).json()
        #return self.athlete_response
        if stat:
            self.athlete_response = respdata
        else:
            self.athlete_response= None
        return stat, self.aathlete_response

    # STRAVA API Get kudos By-Activity_ID
    def stravakudorequest(self, activity_n):
        '''
        url = "https://www.strava.com/api/v3/activities/%d/kudos"%activity_n
        header = {'Authorization': 'Bearer %s'%self.accesstoken }
        self.activity_kudo_response = r.get(url, headers=header).json()
        '''
        stat,respdata = self.stravaapirequest(
                request_url="https://www.strava.com/api/v3/activities/%d/kudos"%activity_n) 
        if stat:
            self.activity_kudo_response = respdata
            return True, self.activity_kudo_response
        else:
            return False, None

    # STRAVA API Get Comments By-Activity_ID
    def stravacommentrequest(self,activity_n):
        stat,respdata = self.stravaapirequest(
                request_url = "https://www.strava.com/api/v3/activities/%d/comments"%activity_n)
        if stat:
            self.activity_comment_response = respdata
            return True, self.activity_comment_response
        else:
            return False, None

#
# all the output converters for various Strava distance, time, text, GPS, elevation, speed, etc...
#
def mgintout(key,val,idval=0):
    try:
        if val==None:
            return ''
        return '%d'%val
    except:
        return 'mgint fail!  %s:%d'%(key,idval)

# return a distance string from a value
# Strava defaults to meters. converter defaults to MILES, use stdunits=False to get metric output
def mgdistanceout(key,val,idval=0,stdunits=True):
    try:
        if val==None:
            return ''
        METERSPERMILE=1609.34
        divisor=1
        if stdunits:
            divisor = METERSPERMILE
        return '%5.2f'%(val/divisor)
    except:
        return 'mgfloatmiles fail! %s:%d'%(key,idval)

# default Strava data is Meters. this converter defaults to FEET, stdunits=False to get metric output
def mgelevationout(key,val,idval=0,stdunits=True):
    try:
        if val==None:
            return ''
        FEETPERMETER = 3.2808399 
        multiplier=1
        if stdunits:
            multipler = FEETPERMETER
        return '%5.2f'%(val*multiplier)
    except:
        return 'mgelevationout fail!  %s:%d'%(key,idval)
    
# return a speed string from value
# default strava data is meters/second.  this decoder default converts that to Miles/Hr, stdunits=False to get metric output
def mgspeedout(key,val,idval=0):
    return mgdistanceout(key,val*3600)

# return minutes value from value
# Strava data defaults to seconds. converter defaults to MINUTES
def mgminsout(key,val,idval=0):
    try:
        if val==None:
            return ''
        return '%5.2f'%(val/60.0)
    except:
        return 'mgfloatmins fail!  %s:%d'%(key,idval)

# return string from float value
def mgfloatout(key,val,idval=0):
    try:
        if val==None:
            return ''
        return '%5.2f'%val
    except:
        return 'mgfloat fail!  %s:%d'%(key,idval)

# return string from list of floats (like GPS data)
def mgfloatlist(key,val,idval=0):
    try:
        if val==None:
            return ''
        mystr = '\"['
        separator=''
        for i in val:
            mystr = mystr+separator+'%5.2f'%i
            separator = ','
        mystr = mystr +  ']\"'
        return mystr
    except:
        return 'mgfloatlist fail!  %s:%d'%(key,idval)

#
def mgtwocommas(key,val,idval=0):
    return ',,'

# attempt to normalize text output on Windows accomodating emoji encoding
def mgtextout(key,val,idval=0):
    if val==None:
        return ''
    # normal windows cmd console, and python runtime console barfed on emojis; I added this test
    # maybe to FIXUPLATER to do for a graphical app output 
    isascii = lambda s: len(s) == len(s.encode())
    try:
        if not isascii(val):
            l1 = len(val)
            l2 = len(val.encode())
            #val = val.encode(val,'utf-8')
            val = val.encode() 
           # https://www.iemoji.com/view/emoji/2728/smileys-people/cold-face
           # in this example, the Cold Face Emoji encoded to this "b'Gorgeous! Wish I had gloves in the morning tho \xf0\x9f\xa5\xb6'"
    except:
        return '<char decode>! %s:%d'%(key,idval)

    try:
        return '%s'%val
    except:
        return 'mgtextout fail!  %s:%d'%(key,idval)

def mgqtextout(key,val,idval=0):
    return '\"'+mgtextout(key,val)+'\"'

# catchall to output OTHER field
def mgotherout(key,val,idval=0):
    if val==None:
        return 'x'
    try:
        return 'other<%s>'%key
    except:
        return 'mgother fail!  %s:%d'%(key,idval)

# convert a boolean to a string for output
def mgboolout(key,val,idval=0):
    try:
        if val==None:
            return ''
        if val:
            return 'True'
        else:
            return 'False'
    except:
        return 'mgbool fail!  %s:%d'%(key,idval)

#kudoitem has same structure as comment athleteitem
#kudo record  {'resource_state': 2, 'firstname': 'Sam', 'lastname': 'T.'}, {'resource_state': 2, 'firstname': 'Randall', 'lastname': 'S.'}]
#commentinfokeys = listofcomments
commentathleteitem = {    #{'resource_state': 2, 'firstname': 'Lucas', 'lastname': 'L.'}}, {'id': 511289549, 'activity_id': 2253349870, 'post_id': None, 'resource_state': 2, 'text': 'Lucas Lux thanks for the push. Missing you JB Sam. Maybe a PG outing in May or June ', 'mentions_metadata': None, 'created_at': '2019-04-20T01:43:22Z', 'athlete': {'resource_state': 2, 'firstname': 'mikey', 'lastname': 'G.'
    'resource_state':mgintout, #: 2, 
    'firstname': mgtextout, #: 'Lucas', 
    'lastname': mgtextout, 
    }
    # {'id': 511289549, 'activity_id': 2253349870, 'post_id': None, 'resource_state': 2, 'text': 'Lucas Lux thanks for the push. Missing you JB Sam. Maybe a PG outing in May or June ', 'mentions_metadata': None, 'created_at': '2019-04-20T01:43:22Z', 'athlete': {'resource_state': 2, 'firstname': 'mikey', 'lastname': 'G.'

def mgathleteout(key,respdata,idval=0):
    mystr = ''
    for j in respdata:
        #for i in commentathleteitem:
        mystr += commentathleteitem[j](j, respdata[j])+','
    return mystr

# define the template for a comment data item
commentitem = [
    ('id',mgintout), # 511130856, 
    ('activity_id',mgintout), #: 2253349870, 
    ('post_id',mgotherout), #: None, 
    ('resource_state', mgintout), #: 2, 
    ('text',mgqtextout), #: 'Been a while. Get out there and earn some Little Star.', 
    ('mentions_metadata',mgotherout), #: None, 
    ('created_at', mgtextout), #: '2019-04-19T18:27:08Z', 
    ('athlete',mgathleteout), #: 
    #{'resource_state': 2, 'firstname': 'Lucas', 'lastname': 'L.'}}, {'id': 511289549, 'activity_id': 2253349870, 'post_id': None, 'resource_state': 2, 'text': 'Lucas Lux thanks for the push. Missing you JB Sam. Maybe a PG outing in May or June ', 'mentions_metadata': None, 'created_at': '2019-04-20T01:43:22Z', 'athlete': {'resource_state': 2, 'firstname': 'mikey', 'lastname': 'G.'
    ]

#convert a comment to CSV output format
def mgcommentout(respdata):
    n = len(respdata)
    mystrs = []
    for j in respdata:
        tmpstr = ''
        for i in commentitem:
            try:
                tmpstr += '\"'+i[1](i[0],j[i[0]])+'\"'+','
            except:
                tmpstr += '<comment text special char>,'
        mystrs.append(tmpstr)
    return mystrs

#convert a kudo item for output
def mgkudoout(respdata):
    mystrs = []
    for kud in respdata:
        tmpstr=mgathleteout('',kud)
        mystrs.append(tmpstr)
    return mystrs
    #return mgathleteout(respdata)

def mgactivityout(key,segrespdata, tagstr='ACTIVITY',idval=0): # segment activity id
    #print('%s: segrespdata.id'%tagstr,segrespdata['id'])
    #print('%s: segrespdata.resourcestate'%tagstr,segrespdata['resource_state'])
    return '' #this is a noop for output

def mgathleteout2(key,respdata,idval=0): #segment athlete 
    mgactivityout(key,respdata,'ATHLETE')
    return '' # this is a noop for output

# template for the segment data; these are keys contained in a Segment list item
segmentkeys = {
    #'id': mgintout, #: 16648497, 
    #'resource_state': mgintout, #: 2, 
    'name': mgqtextout,#: 'Lake Merritt 2-Mile':
    'activity':mgotherout, # dummy data for activity id/resource state
    'athlete': mgotherout, # dummy data for athlete id/resource state
    'activity_type': mgtextout,#: 'Run':
    'distance': mgdistanceout,#: 3222.7,
    'average_grade': mgelevationout,#: 0.0, 
    'maximum_grade': mgelevationout,#: 3.5, 
    'elevation_high': mgelevationout,#: 4.9,
    'elevation_low': mgelevationout,#: 1.1,
    'start_latlng': mgfloatlist,#: [37.81062, -122.261604],
    'end_latlng': mgfloatlist,#: [37.808487, -122.249705], 
    'start_latitude': mgfloatout,#: 37.81062, 
    'start_longitude': mgfloatout,#: -122.261604,
    'end_latitude': mgfloatout,#: 37.808487,
    'end_longitude': mgfloatout,#: -122.249705,
    'climb_category': mgintout,#: 0, 
    'city': mgtextout,#: 'Oakland':
    'state': mgtextout,#: 'California',
    'country': mgtextout,#: 'United States',
    'private': mgboolout,#False, 
    'hazardous': mgboolout,#: False, 
    'starred': mgboolout,#: False #}
    }

# algorithmically decode and generate rows for a SEGMENT entry
def mgsegmentout(key,segdb,idval=0, gethdrrow=False):
    # the csv headings for the LAPs records
    if gethdrrow:
        retstr = ''
        for i in segmentkeys:
            retstr += i+','
        return retstr
    # the csv data row for a lap 

    mystr = ''
    separatorstr = ','
    for i in segmentkeys:
        if i not in segdb.keys():
            argval = None
        else:
            argval = segdb[i]
        mystr = mystr+ segmentkeys[i](i,argval) + separatorstr
        separatorstr = ','
    return mystr

# template for the SEGMENTEFFORT data items
segmenteffortkeys = {
    'id': mgintout,# 67439351742, 
    'resource_state': mgintout,#: 2,
    'name': mgqtextout, #: 'Lake Merritt 2-Mile':	
    'activity': mgactivityout, #: { 'id': 2696839465,  ‘resource_state': 1}, 
    'athlete': mgathleteout2, # { 'id': 5292665,  'resource_state': 1}, 
    'elapsed_time': mgminsout, #: 1321, 
    'moving_time': mgminsout, #: 1321, 
    'start_date': mgtextout, #: '2019-09-10T15:11:08Z': 
    'start_date_local': mgtextout, #: '2019-09-10T08:11:08Z':
    'distance': mgdistanceout, #: 3214.2,  
    'start_index': mgintout, #: 50, 
    'end_index': mgintout, #: 235, 
    'average_cadence': mgfloatout, #: 80.6, 
    'average_heartrate': mgfloatout, #: 128.4, 
    'max_heartrate': mgfloatout, #: 154.0, 
    'segment': mgsegmentout, #: {
    'kom_rank':mgotherout,#: None, 
    'pr_rank':mgotherout,#: None, 
    'achievements':mgotherout,#: [], 
    'hidden':mgboolout #: False},
    }

# algorithmically decode and generate rows for a list of SegmentEfforts (segmenteffort is wrapper of Segment)
def mgsegmenteffortsout(key,segmentsdb,activityid=0, gethdrrow=False):
    # the csv headings for the SegmentEfforts records
    if gethdrrow:
        retstr = ''
        for istr in segmenteffortkeys:
            if istr == 'segment':
                for s1 in segmentkeys:
                    retstr += s1+','
            retstr += istr+','
        return [retstr]
    # the csv data row for a lap 

    segstrs = []
    retstr = '\"Segment_effort: %d segments\"'%len(segmentsdb)
    #print(retstr)
    for segs in segmentsdb:
        #for i in segmentsdb:
            segeffstr = '%d,Segment,'%activityid  #+ (','*69) # add the commas to offset to align with segment header
            #separatorstr = ','
            #print(i['name'], i['elapsed_time'])
            #for j in segmenteffortkeys:
            for i in segmenteffortkeys:
                if not i in segs.keys():
                    segretstr = '\"<nodata: %s>\"'%i
                else:
                    segretstr = segmenteffortkeys[i](i,segs[i])
                #print(j[0],retstr)
                segeffstr =segeffstr+ segretstr + ','
                #separatorstr = ','
            segstrs.append(segeffstr)
    #for sstr in segstrs:
    #    print(sstr)
    return segstrs

# template for the SPLIT data inputs
Splitinfokey = {   # both _metric and _standard {'distance', #: 1000.3, 'elapsed_time', #: 1164, 'elevation_difference', #: 4.8, 'moving_time', #: 803, 'split', #: 2, 'average_speed', #: 1.25, 'pace_zone', #: 0}, {'distance', #: 998.4, 'elapsed_time', #: 1168, 'elevation_difference', #: 0.1, 'moving_time', #: 837, 'split', #: 3, 'average_speed', #: 1.19, 'pace_zone', #: 0}, {'distance', #: 1001.3, 'elapsed_time', #: 1662, 'elevation_difference', #: -14.0, 'moving_time', #: 861, 'split', #: 4, 'average_speed', #: 1.16, 'pace_zone', #: 0}, {'distance', #: 329.9, 'elapsed_time', #: 414, 'elevation_difference', #: 0.3, 'moving_time', #: 278, 'split', #: 5, 'average_speed', #: 1.19, 'pace_zone', #: 0}], 
    'distance':mgdistanceout, #: 1002.6, 
    'elapsed_time':mgminsout, #: 1036, 
    'elevation_difference':mgelevationout, #: 1.3, 
    'moving_time':mgintout, #: 794, 
    'split':mgintout, #: 1, 
    'average_speed': mgspeedout, #: 1.26,
    'average_heartrate': mgfloatout, # 162.4,
    'pace_zone': mgintout # #: 0},
    # {'distance', #: 1000.3, 'elapsed_time', #: 1164, 'elevation_difference', #: 4.8, 'moving_time', #: 803, 'split', #: 2, 'average_speed', #: 1.25, 'pace_zone', #: 0}, {'distance', #: 998.4, 'elapsed_time', #: 1168, 'elevation_difference', #: 0.1, 'moving_time', #: 837, 'split', #: 3, 'average_speed', #: 1.19, 'pace_zone', #: 0}, {'distance', #: 1001.3, 'elapsed_time', #: 1662, 'elevation_difference', #: -14.0, 'moving_time', #: 861, 'split', #: 4, 'average_speed', #: 1.16, 'pace_zone', #: 0}, {'distance', #: 329.9, 'elapsed_time', #: 414, 'elevation_difference', #: 0.3, 'moving_time', #: 278, 'split', #: 5, 'average_speed', #: 1.19, 'pace_zone', #: 0}], 
    }

# template for the LAP data inputs
Lapinfokey = {
    #'laps': [
    'id': mgintout, #8887730826, 
    'resource_state': mgintout, #: 2, 
    'name': mgtextout, #'Lap 1', 
    'activity': mgotherout, # {'id': 2711323876, 'resource_state': 1}, 
    'athlete': mgotherout, # {'id': 5292665, 'resource_state': 1}, 
    'elapsed_time': mgintout, # 555, 
    'moving_time': mgintout, #541, 
    'start_date': mgtextout, #'2019-09-15T14:18:02Z', 
    'start_date_local': mgtextout, #'2019-09-15T07:18:02Z', 
    'distance': mgdistanceout, # 1609.34, 
    'start_index': mgintout, # 0, 
    'end_index': mgintout, # 82, 
    'total_elevation_gain': mgelevationout, # 12.0, 
    'average_speed': mgspeedout, # 2.97, 
    'max_speed': mgspeedout, #: 4.3,
    'average_cadence': mgfloatout, # 84.2, 
    'average_heartrate': mgfloatout, # 151.7,
    'max_heartrate': mgfloatout, # 185.0, 
    'lap_index': mgintout, # 1, 
    'split': mgintout, #1, 
    'pace_zone': mgintout, # 2
    } 

# algorithmically decode and generate rows for a list of SPLITS
def  mgsplitsout(key,splitsdb,activ_id=0, gethdrrow=False):
    # the csv headings for the LAPs records
    if gethdrrow:
        retstr = ''
        for i in Splitinfokey:
            retstr += i+','
        return [retstr]
    # the csv data row for a lap 
    splitstrs = []
    for eachsplit in splitsdb:
        mystr = ''
        separatorstr = ','
        for i in Splitinfokey:
            if i not in eachsplit.keys():
                argval = None
            else:
                argval = eachsplit[i]
            mystr = mystr+ Splitinfokey[i](i,argval) + separatorstr
            separatorstr = ','
        splitstrs.append('%d,%s,%s'%(activ_id,key,mystr))
    return splitstrs
    #return retstr, hdrstr, segstrs 

# algorithmically decode and generate rows for a list of LAPS
def  mglapsout(key,lapsdb,activ_id=0, gethdrrow=False):
    # the csv headings for the LAPs records
    if gethdrrow:
        retstr = ''
        for i in Lapinfokey:
            retstr += i+','
        return [retstr]
    # the csv data row for a lap 
    lapstrs = []
    for eachlap in lapsdb:
        mystr = ''
        separatorstr = ','
        for i in Lapinfokey:
            if i not in eachlap.keys():
                argval = None
            else:
                argval = eachlap[i]
            mystr = mystr+ Lapinfokey[i](i,argval) + separatorstr
            separatorstr = ','
        lapstrs.append('%d,%s,%s'%(activ_id,key,mystr))
    return lapstrs

# convert a summary line of laps data
def  mglenout(key,lapsdb,activ_id=0):
    try:
        retstr = '"%s: %d items"'%(key,len(lapsdb))
    except:
        retstr = "%s/lenerr"%key
    return retstr

# template of top level ACTIVITY data item
ActivityInfoKeys = [('resource_state', mgintout), #:3
    ('athlete', mgotherout), # athleteinfo #{'id': 23235001, 'resource_state': 1}
    ('name', mgqtextout), #: 'Holes 8-18 and home ', 
    ('distance', mgdistanceout), # 4332.5
    ('moving_time', mgminsout), #: 3573,
    ('elapsed_time', mgminsout), #: 5444, 
    ('total_elevation_gain', mgelevationout), #: 40.7, 
    ('type', mgtextout), #: 'Walk',
    ('id', mgintout), #: 2452708685, 
    ('external_id', mgtextout), #: 'C6364FE6-2D5C-44DC-8D8A-6D9B87B8C15F', 
    ('upload_id', mgintout), #: 2606342610, 
    ('start_date', mgtextout), #: '2019-06-15T16:11:52Z', 
    ('start_date_local', mgtextout), #: '2019-06-15T09:11:52Z', 
    ('timezone', mgtextout), #: '(GMT-08:00) America/Los_Angeles', 
    ('utc_offset', mgfloatout), #: -25200.0, 
    ('start_latlng', mgfloatlist), #: [36.56, -121.94], 
    ('end_latlng', mgfloatlist), #: [36.57, -121.95], 
    ('location_city', mgtextout), #: None, 
    ('location_state', mgtextout), #: None,
    ('location_country', mgtextout), #: None,
    ('start_latitude', mgfloatout), #: 36.56, 
    ('start_longitude', mgfloatout), #: -121.94,
    ('achievement_count', mgintout), #: 0, 
    ('kudos_count', mgintout), #: 5,
    ('comment_count', mgintout), #: 2,
    ('athlete_count', mgintout), #: 1,
    ('photo_count', mgintout), #: 0, 
    ('map', mgotherout), #: mapinfokeys 
    ('photos', mgotherout), #: photokey and array of photourls
    ('device_name', mgtextout), #: 'Strava iPhone App', 
    ('embed_token', mgtextout), #: 'f434587211db7ce56563dfa44177984c2606816e', 
    ('available_zones', mgotherout), #: []
    ('trainer', mgboolout), #: False,
    ('commute', mgboolout), #: False,
    ('manual', mgboolout), #: False,
    ('private', mgboolout), #: False, 
    ('visibility', mgtextout), #: 'everyone',
    ('flagged', mgintout), #: False, 
    ('gear_id', mgintout), #: None,
    ('from_accepted_tag', mgintout), #: False,
    ('upload_id_str', mgtextout), #:'2606342610',
    ('average_speed', mgspeedout), #: 1.213,
    ('max_speed', mgspeedout), #: 2.0, 
    ('average_cadence',mgfloatout), #: 67.8	 
    ('average_temp',mgfloatout), #: 18.0	 
    ('average_watts',mgintout), #: 151.2	 
    ('weighted_average_watts',mgintout),#: 176	 
    ('kilojoules', mgfloatout), #: 2676.9	 
    ('device_watts',mgboolout), #: True
    ('has_heartrate', mgboolout), #: False,
    ('average_heartrate',mgfloatout), #: 163.9
    ('max_heartrate',mgfloatout), # 187.0
    ('heartrate_opt_out', mgboolout), #: False,
    ('display_hide_heartrate_option', mgboolout), #: False,
    ('max_watts',mgintout), #: 678
    ('elev_high', mgelevationout), #: 33.3, 
    ('elev_low', mgelevationout), #: 6.1, 
    ('pr_count', mgintout), #: 0,
    ('total_photo_count', mgintout), #: 5, 
    ('has_kudoed', mgboolout), #: False,
    ('suffer_score', mgfloatout), #: 98.0
    ('description', mgqtextout), #: None,
    ('calories', mgfloatout), #: 0.0,
    ('perceived_exertion', mgintout), #: None,
    ('prefer_perceived_exertion', mgintout), #: None,
    ('segment_efforts', mglenout ), #: [],
    ('splits_metric', mglenout ), #:
    ('splits_standard', mglenout ), # 
    ('laps', mglenout ), #: )
    ]

# template for activity items that are compound LAPS SEGMENT_EFFORTS SPLITS_METRIC SPLITS_STANDARD. 
# each has an associated processing function to convert data 
ActivityCompoundFuncs = {
    #'StravaActivity':StravaActivityOut,
    'laps':mglapsout,
    'segment_efforts':mgsegmenteffortsout,
    'splits_metric':mgsplitsout,
    'splits_standard':mgsplitsout
    }

# template for a MAP data item
Mapinfokeys = [
    'id', #: 'a2452708685', 
    'polyline', #: 
    #'o_d~EnjggVAQ@_@HGY]e@{@IKEAECWk@IUa@m@i@SIGEAEBAGQKGMQu@OqA?c@Fq@@{@EOOYCOLi@\\o@b@kAx@wBTc@`@m@HWp@kAZ]NGBERe@@WJ[`@e@NUv@y@Hy@LUZw@JADFJEJDLGJBFHFAl@i@zA_Af@_@d@Sl@OAEDM?OAGWWm@]s@WiBeAYMOOOICCAOUUOHCFIVGJMB[Ac@HM?Yb@?PE^CFQDADKt@@LGTP\\NN@HALGVOPGJEZC^KPE@Gf@?TBl@R|@LL@HWj@SVKVORQf@e@~@_@j@_@bACDMKWb@NJMPG\\MZaAzBSx@MPQj@Ud@AY_@u@G_@}A|@m@XSDk@ZkB`@CTBTC`@D\\FRCFOAK@K`@BC?GOQYIi@BKBY@c@Ci@W_A@a@CIDBKEEOCAFIHELE@G^w@x@E`@EBOVDVEb@CHONWFANKZy@jBSXk@d@GJCRYPGJBLD@LSGPIHJHGR@FAFORQb@AHB^AFHJNb@VVb@t@BNA`@V\\`@\\TZj@hBPnACJH\\^VRTD?HILA@L@OE@ENFRFFDAAFBBZTJ@PHDENHfAz@PT`@VBDALBBBLITFEH[BFVJ`@T@D?F@FAFOTkAn@MD[@YH?F@GEGG?KFc@h@EVUv@EV?NCXMr@_@`AShAMZIn@Kb@C`@K\\Al@@ZDPARED?FD\\BDD?KJK?GBIVIHGNHJ?GBDD\\JL\\TARPD',
    'resource_state', #: 3, 
    'summary_polyline', #: 
    #'o_d~EnjggVAQ@_@HGY]e@{@IKEAECWk@IUa@m@i@SIGEAEBAGQKGMQu@OqA?c@Fq@@{@EOOYCOLi@\\o@b@kAx@wBTc@`@m@HWp@kAZ]NGBERe@@WJ[`@e@NUv@y@Hy@LUZw@JADFJEJDLGJBFHFAl@i@zA_Af@_@d@Sl@OAEDM?OAGWWm@]s@WiBeAYMOOOICCAOUUOHCFIVGJMB[Ac@HM?Yb@?PE^CFQDADKt@@LGTP\\NN@HALGVOPGJEZC^KPE@Gf@?TBl@R|@LL@HWj@SVKVORQf@e@~@_@j@_@bACDMKWb@NJMPG\\MZaAzBSx@MPQj@Ud@AY_@u@G_@}A|@m@XSDk@ZkB`@CTBTC`@D\\FRCFOAK@K`@BC?GOQYIi@BKBY@c@Ci@W_A@a@CIDBKEEOCAFIHELE@G^w@x@E`@EBOVDVEb@CHONWFANKZy@jBSXk@d@GJCRYPGJBLD@LSGPIHJHGR@FAFORQb@AHB^AFHJNb@VVb@t@BNA`@V\\`@\\TZj@hBPnACJH\\^VRTD?HILA@L@OE@ENFRFFDAAFBBZTJ@PHDENHfAz@PT`@VBDALBBBLITFEH[BFVJ`@T@D?F@FAFOTkAn@MD[@YH?F@GEGG?KFc@h@EVUv@EV?NCXMr@_@`AShAMZIn@Kb@C`@K\\Al@@ZDPARED?FD\\BDD?KJK?GBIVIHGNHJ?GBDD\\JL\\TARPD'}, 
    ]

# template (placeholder!) for PHOTO data item
Photoinfokeys = [
    'primary', # None
    'count', # 0}, 
    ]

# template (placeholder!) for PHOTO 2nd part data item
Photokey = [
    'id', #: None, 
    'unique_id', #: '10163026-9F0D-4C73-A9F7-E1739500FC88', 
    'urls', #: photourlkeys
    ]

# template for PHOTO URL data item
Photourlkeys = [ 
    #{'600': 'https://dgtzuqphqg23d.cloudfront.net/lD8aK9JJw5oZqW_xW92ROOHSvtws6vu1M5lh2Tb8AcE-576x768.jpg', '100': 'https://dgtzuqphqg23d.cloudfront.net/lD8aK9JJw5oZqW_xW92ROOHSvtws6vu1M5lh2Tb8AcE-96x128.jpg'},
    'source', #: 1},
    'use_primary_photo', #: True, 
    'count', #: 5},
    ]

# algorithmically decode and generate row for all primary items included in single activity entry. 
def StravaActivityOut(key, resp, acti_id=0, gethdrrow=False, ):
    if gethdrrow:
        hdrstr = '0,0-Activity:header,' 
        # if hdr flag is True, just build the Activity header row for csv
        # hdrstr = 'activity_id, rec type:InfoHdr,'
        for i in ActivityInfoKeys:
            hdrstr = hdrstr + i[0] + ','
        return hdrstr
    #
    mystr = '%d,Activity,'%(acti_id)
    for i in ActivityInfoKeys:
        # decode each item in Activity info in csv format, construct an item data row
        if i[0] not in resp.keys():
            mystr += "<nodata>,"  #%i[0]
            continue
        retstr = i[1](i[0],resp[i[0]], acti_id)            
        mystr +=  retstr+','
    return mystr
  

#a main function entry point for simply testing the class and functions here
if __name__ == '__main__':
    #
    #create an instance of the StravaAPIauthenticator(access code). 
    auth = StravaAPIauthenticator() 
    # authenticator instance will return a runtime validated Access Token from Strava
    mytoken = auth.saa_getaccesstoken()
    if not mytoken:
        print('authenticator Access Token sequence failed')
        exit()

    # flag to enable redirection of print() to a .csv file
    # turn this off False if you just want to test with std output
    doredirection = DOREDIRECTION

    # redirect output into a CSV file if this flag is true. 
    if doredirection : # doredirection:
        redirector = MG_OutputRedirect('stravadata.csv')
    countrequests = 0
    newcountactivities = 0

    # output the banner with column titles
    hdrrow = StravaActivityOut('Activity',None, None, gethdrrow=True )
    print(hdrrow)
    for i in ['laps','segment_efforts','splits_metric','splits_standard']:
            segstrs=ActivityCompoundFuncs[i](i, None, None, gethdrrow=True)
            print("0,0-%s:header,"%i,segstrs[0])

    # instantiate the API engine. 
    stravaapi = StravaCSVgenerator(mytoken)

    # get a list of the athlete activities IDs
    my_activities = stravaapi.strava_getactivities()
    if not len(my_activities):
        redirector = MG_OutputRedirect('',False)
        print('GetActivities failed')
        exit(1)

    # iterate through the list of Activities. reqeust detail inside the loop
    for activity_n in  my_activities:
        # activity request to get each athlete activity item detail by event Id
        # respdata_activity holds the json structure response from the API request
        stat, respdata_activity = stravaapi.strava_activityrequest(activity_n) # 
        if not stat:
            redirector = MG_OutputRedirect('',False)
            print('GetActivities failed')
            exit()
        countrequests += 1
        # decode the activity response data to get top level Activity info
        activityrow = StravaActivityOut('Activity', respdata_activity, activity_n ) # 
        print(activityrow)

        # decode the activity response data secondary details if present for an activity; Laps, Segments, splits_metric, splits_standard
        # TBD add photos, maps, ...
        for i in ['laps','segment_efforts','splits_metric','splits_standard']:
            if i in respdata_activity.keys():
                segstrs=ActivityCompoundFuncs[i](i, respdata_activity[i],activity_n, False)
                for sstr in segstrs:
                    print('%s'%sstr)        

        # get the kudos for activity by id 
        if respdata_activity['kudos_count'] > 0:
            # make the api request for kudos
            stat,respdata = stravaapi.stravakudorequest( activity_n)  # !
            #url = "https://www.strava.com/api/v3/activities/%d/kudos"%activity_n.id # "Authorization: Bearer [[access_token['access_token']]]"    
            if not stat:
                redirector = MG_OutputRedirect('',False)
                print('GetKudos failed')
                exit()
            countrequests += 1
            mystrs = mgkudoout(respdata)
            for kud in mystrs:
                print('%d,kudo,'%activity_n , kud)

        #  activities/comments
        # activities/{id}/kudos?page=&per_page=" "Authoriz
        if respdata_activity['comment_count'] > 0:
            # web api request to get comments by activity Id
            stat, respdata = stravaapi.stravacommentrequest(activity_n )
            if not stat:
                redirector = MG_OutputRedirect('',False)
                print('Get Comments failed')
                exit()
            countrequests += 1
            # output a list of comments
            mystrs = mgcommentout(respdata) #print('comment data --->',respdata)
            for comm in mystrs:
                try:
                    print('%d,comment,'%activity_n ,comm)
                except:
                    print('%d,<special chars comment>'%activity_n )

        newcountactivities = countrequests
        # if your activity list is huge, these 2 lines can be used as a limit for partial list of activities
        ## if newcountactivities > 10:
        ##   break
    #reset redirector
    if doredirection:
        redirector.makestdoutredirect('',True)
