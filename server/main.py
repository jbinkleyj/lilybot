"""
This is ardyh
Tornado Websockts server used the pass for lilybots.

Wil Black, wilblack21@gmail.com 
Oct. 26, 2013



## Messages

- message
    -- name
    -- from
    -- message
    -- command
    -- channel
    -- ardyh_timestamp - May not be present


"""
import sys, json, ast
import time 
import collections
import datetime
from datetime import datetime as dt
 
import redis

import tornado.httpserver
import tornado.ioloop
import tornado.web
import tornado.websocket
import tornado.template

from backends.apigee import ApiGeeClient

# Settings
VERBOSE = True
PORT = 9093
LOG_DTFORMAT = "%Y-%m-%d %H:%M:%S"
IP = "173.255.213.55"
ARDYH_MONITOR = 'monitor.solalla.ardyh'


listeners = []

def get_bot_listener(bot_name):
    return next( (bot for bot in listeners if bot['bot_name'] == bot_name), [] )


class ArdyhWebRequestHandler(tornado.web.RequestHandler):

    def set_allow_origin(self, request):
        origin_domain = self.request.headers.get("Origin", None)        
        if origin_domain:
            self.set_header("Access-Control-Allow-Origin", origin_domain)


class MainHandler(ArdyhWebRequestHandler):

    # def set_default_headers(self):
    #     self.set_header("Access-Control-Allow-Origin", "http://ardyh.solalla.com")
    #     self.set_header("Access-Control-Allow-Origin", "http://ctenophore.solalla.com")

    def get(self, action=None):
        """
        Displays the webpage.
        """
        self.set_allow_origin(self.request)

        if action == "bots-list":
            # out = [ {'bot_name':l['bot_name'], 'subscriptions':l['subscriptions']} for l in listeners]
            temp = []
            for l in listeners:
                row = {
                    'bot_name': l['bot_name'],
                    'bot_roles': l['bot_roles'],
                    'mac': l.get('mac', ''),
                    'local_ip': l.get('local_ip', ''),
                    'subscriptions': l.get('subscriptions', ''),
                    'sensors': l.get('sensors', []),
                }
                temp.append(row)

            out = json.dumps(temp)
            self.write(out)
        else:
            loader = tornado.template.Loader(".")
            self.write(loader.load("templates/index.html").generate())


class TwineHandler(ArdyhWebRequestHandler):

    def get(self, action):
        print "Got message ", action
        self.set_allow_origin(self.request)

        for bot in listeners:
            if action == "bottom":
                message = json.dumps({
                    'command': 'allOff',
                    'kwargs': {}
                })
            else:
                if action == "top":
                    color = "#FF00FF"
                elif action == "back":
                    color = "#0000FF"
                elif action == "front":
                    color = "#00FFFF"
                elif action == "left":
                    color = "#00FF00"
                elif action == "right":
                    color = "#FF0000"
                elif action == "shake":
                    color = "#FFFFFF"
                message = json.dumps({
                    'command': 'fillRGB',
                    'kwargs': {'color': color}
                })
            bot['socket'].write_message(message)
        self.write("Received action %s" % (action))

class MagicMushroomHandler(ArdyhWebRequestHandler):
    """
    Simple WEB API to change the state of the magic mushroom

    /magic-mushroom/COMMAND/?kwargs

    COMAANDS:
    - off
    - color-cap : clor is parameter, did not add the hash sign to the hex color

    Example Usage
    /magic-mushroom/color-cap/?color=FF00FF

    """
    # def set_default_headers(self):
    #     self.set_header("Access-Control-Allow-Origin", "http://ardyh.solalla.com")
    #     self.set_header("Access-Control-Allow-Origin", "http://ctenophore.solalla.com")

    def get(self, action):
        self.set_allow_origin(self.request)


        action = action.strip("/")
        print "Got message ", action
        params = {}
        pieces = self.request.query.split("&")
        for piece in pieces:
            key, val = piece.split('=')
            params.update({key: val})

        kwargs = {}

        for bot in listeners:
            if bot['socket']:
                if action == "off":
                    command = "allOff"
                    kwargs = {}

                elif action == "color-cap":
                    kwargs = {'color': '#'+params['color']}
                    command = "color_cap"

                elif action == 'set-state':
                    command = 'set_state'
                    kwargs = {'state': '#' + params['state']}

                message = json.dumps({
                    'command': command,
                    'kwargs': kwargs
                })
                try:
                    print "sending ", message
                    print "to bot", bot['bot_name']
                    bot['socket'].write_message(message)
                except AttributeError:
                    print "WTF bot %s is no good" % (bot['bot_name'])

        self.write("Received action %s with kwargs %s" % (action, kwargs))



class WSHandler(tornado.websocket.WebSocketHandler):
    def __init__(self, uri, protocols):
        super(WSHandler, self).__init__(uri, protocols)

        self.nav = ArdyhNav(self)
        self.portA_fifo = collections.deque(5*[255], 5)
        self.busy = False # Tells the ardyh to stop sending messages to listener, useful while executing a command
        self.operationa_mode = "user_controlled"
        self.api = ApiGeeClient()

    def open(self):
        print 'connection opened...'

        try:
            bot_name = self.request.uri.split("?")[1]
        except:
            bot_name = ""
        print "this is %s" %bot_name

        self.bot_name = bot_name
        old_socket = get_bot_listener(bot_name)
        if old_socket:
            old_socket.update({'socket':self})
        else:
            bot = {
                "socket": self,
                "subscriptions": [],
                "bot_name": bot_name
            }

            listeners.append( bot )


    def on_message(self, envelope):      # receives the data from the webpage and is stored in the variabe message
        """
        Messages should come as a JSON Object string.

        envelope contains meta data plus a message. Once converted to json as data
        the message is available at data['message']

        An initial connection should send a handshake and the handshake should be of the format

        handshake = {
            'bot_name': "",
            'bot_roles': "", # Not currently used. Defines is its a server or a node.
            'mac': "", # The MAC Address of the bot, '-' removed.
            'handshake': [Boolean],
            'subscriptions': [],  # A list of bot_names to listen to
            'sensors': [], # List of attached sensors
            'local_ip': ""
        }

        """
        if VERBOSE: print "recieved message: \n", envelope
        try:
            data = ast.literal_eval(envelope)
        except ValueError, e:
            try:
                data = json.loads(envelope)
            except:
                print sys.exc_info()[0]
                if VERBOSE: print "Message is not JSON"
                return

        if 'heartbeat' in data.keys():
            self.write_message(data)
            return

        if 'handshake' in data.keys():
            print "Updating %s's subscriptions to %s" %(data['bot_name'], data['subscriptions'])
            bot = get_bot_listener(data['bot_name'])
            local_ip = data.get("local_ip", "")
            sensors = data.get("sensors", "")

            bot.update({
                'subscriptions':data['subscriptions'],
                'mac': data.get('mac', ''),
                'local_ip': local_ip,
                'sensors': sensors,
                'bot_roles': data['bot_roles']
            })
            self.broadcast(data['bot_name'], [], data)
            return


        if 'message' in data.keys():
            message = data['message']
            if 'command' in message and message['command'] == 'sensor_values':
                res = self.api.post('sensor_values', data)


        # save message to redis
        now = dt.utcnow()
        ts = time.mktime(now.timetuple()) + now.microsecond * 1e-6
        rstore = data

        self.broadcast(self.bot_name, [], data)

    def on_close(self):
        print 'Lost a %s. connection closed.' % self.bot_name
        bot = next( bot for bot in listeners if bot['bot_name'] == self.bot_name )
        listeners.remove(bot)

        self.log("Connection closed to %s" %(bot['bot_name']))

    def broadcast(self, from_bot_name, channels, message):
        """
        This will broadcast to all subscribers and monitors.

        Inputs
        from - [String] the bot_name the message is coing from or 'ardyh'
        channels - [List] a list of channels to broadcast to, these are 
                   generally bot_names. These channels are in addtion to
                   the bots subscribers.
        message - [Dict] A message dict. A timestamp and the bot_name will be attached. 

        A command message. 
        -- command
        -- kwargs


        """

        bot = get_bot_listener(from_bot_name)
        if not bot:
            self.log("bot %s not found." % from_bot_name)


        out = message

        timestamp = dt.now().strftime(LOG_DTFORMAT)
        out.update({
            'timestamp': timestamp,
            'bot_name': from_bot_name,
            'channels': channels
        })

        
        # Get the subscribing bots and send the message
        print "About to broadcast ", out
        for sub in self.get_subscribers(from_bot_name):
            try:
                print "Broadcasting to %s" %(sub['bot_name'])
                sub['socket'].write_message(out)
            except AttributeError:
                print "No socket found ", sub


    def get_subscribers(self, channel):
        """

        Checks listeners for a bots with channel in their subscription list.
        channel is usually a bot_name.

        Returns:
            If channel is falsy then the all listeners are returned else
            returns a lit of listerns.

        """
        
        if channel:
            return [bot for bot in listeners if channel in bot['subscriptions'] ]
        else:
            return listeners


    def log(self, message, mode=None):
        """
        Sends out a message to 'monitor.solalla.ardyh' from ardyh.

        Inputs
        mode - [String] 'echo' .  if mode is None then turns on the ardyh signature
        message

        """
        print "\nlogging message: \n", message
        if self.busy: return

        # Update with ardyh timestamp.
        now = dt.now().strftime(LOG_DTFORMAT)

        if message.__class__ == {}.__class__:
            if VERBOSE: print "message is a dict"
            message.update({"ardyh_timestamp":"%s" %(now)})
        else:
            if VERBOSE: print "message is a string"
            message = {"message":message, "ardyh_timestamp": "%s" %(now) }

        bot = get_bot_listener(ARDYH_MONITOR)
        
        try:
            print "sending to %s" % (bot['bot_name'])
            bot['socket'].write_message(message)
        except AttributeError:
            print "No socket found ", bot

    def loopCallback(self):
      now = dt.now().strftime(LOG_DTFORMAT)
      message = "[%s]" %(now)
      self.write_message(message)



class ArdyhNav():

    def __init__(self, conn):
        self.conn = conn

    def event(self, event_type):
        if event_type == 'bump':
            self.conn.write_message("d")
            tornado.ioloop.IOLoop.instance().add_timeout(datetime.timedelta(seconds=0.3), self.stop)
            tornado.ioloop.IOLoop.instance().add_timeout(datetime.timedelta(seconds=1.0), self.rotateLeft)
            tornado.ioloop.IOLoop.instance().add_timeout(datetime.timedelta(seconds=1.3), self.stop)
            tornado.ioloop.IOLoop.instance().add_timeout(datetime.timedelta(seconds=1.4), self.tryForward)

    def stop(self):
        self.conn.write_message("b")

    def rotateLeft(self):
        self.conn.write_message("l")

    def rotateRight(self):
        self.conn.write_message("r")

    def tryForward(self):
        if self.conn.portA_fifo[1] >= 50:
            self.conn.write_message("u")
        print "trying to set self.conn.busy %s" %self.conn.busy
        self.conn.busy = False
        



application = tornado.web.Application([
      (r'/ws', WSHandler),
      (r'/', MainHandler),
      (r'/(bots-list)', MainHandler),
      (r'/twine/(.*)', TwineHandler),
      (r'/magic-mushroom/(.*)', MagicMushroomHandler),
      (r"/(.*)", tornado.web.StaticFileHandler, {"path": "./resources"}),
    ])


if __name__ == "__main__":
    r = redis.StrictRedis(host='localhost', port=6379, db=0)

    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(PORT) 
    #application.listen(PORT)
    
    print "Starting server at %s:%s" %(IP, PORT)          #starts the websockets connection
    tornado.ioloop.IOLoop.instance().start()
  
