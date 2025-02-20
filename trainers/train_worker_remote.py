# Copyright (C) 2022 Ludger Hellerhoff, ludger@cam-ai.de
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 3
# of the License, or (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  
# See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.

import json
import requests
from time import sleep, time
from multitimer import MultiTimer
from traceback import format_exc
from django.utils import timezone
from tools.l_tools import djconf, seq_to_int
from .models import trainframe

class train_once_remote():

  def __init__(self, myschool, myfit, wsserver, wsname, wspass, t_type, logger):
    self.myschool = myschool
    self.myfit = myfit
    self.t_type = t_type
    self.logger = logger
    self.wsurl = wsserver+'ws/remotetrainer/'
    self.wsname = wsname
    self.wspass = wspass
    self.ws_ts = None

  def send_ping(self):
    while True:
      try:
        self.ws.send('Ping', opcode=1)
        self.ws_ts = time()
        break
      except BrokenPipeError:
        self.logger.warning('Socket error while pinging prediction server')
        sleep(djconf.getconfigfloat('medium_brake', 0.1))

  def run(self):
    try:
      self.logger.info('****************************************************');
      self.logger.info('*** Working on School #'
        +str(self.myschool.id)+', '+self.myschool.name+'...');
      self.logger.info('****************************************************');
      from websocket import WebSocket #, enableTrace
      #enableTrace(True)
      self.ws = WebSocket()
      self.ws.connect(self.wsurl)
      outdict = {
        'code' : 'auth',
        'name' : self.wsname,
        'pass' : self.wspass,
      }
      while True:
        try:
          self.ws.send(json.dumps(outdict), opcode=1) #1 = Text
          break
        except BrokenPipeError:
          self.logger.warning('Socket error while pushing initialization data '
            + 'to training server')
          sleep(djconf.getconfigfloat('medium_brake', 0.1))


      outdict = {
        'code' : 'namecheck',
        'school' : self.myschool.e_school,
      } 
      self.ws.send(json.dumps(outdict), opcode=1) #1 = Text
      remotesearch = json.loads(self.ws.recv())
      self.ws_ts = time()
      pingproc = MultiTimer(interval=2, 
        function=self.send_ping, 
        runonstart=False)
      pingproc.start()
      remoteset = set()
      remotedict = {}
      for item in remotesearch:
        remotedict[item[0]] = item[1]
        remoteset.add(item[0])
      filterdict = {'school' : self.myschool.id, }
      if not self.myschool.ignore_checked:
        filterdict['checked'] = True
      localsearch = trainframe.objects.filter(**filterdict)
      localset = set()
      localdict = {}
      for item in localsearch:
        localdict[item.name] = [item.c0, item.c1, item.c2, item.c3, item.c4, 
          item.c5, item.c6, item.c7, item.c8, item.c9, ]
        localdict[item.name] += [seq_to_int(localdict[item.name])]
        localdict[item.name] += [item.code]
        localset.add(item.name)
      pingproc.stop()
      count = len(remoteset & localset)
      for item in (remoteset & localset):
        if remotedict[item] != localdict[item][10]:
          outdict = {
            'code' : 'delete',
            'name' : item,
          }
          self.ws.send(json.dumps(outdict), opcode=1) #1 = Text
          self.logger.info('(' + str(count) + ') Changed, deleting: ' + item)
          remoteset.remove(item)
        count -= 1  
      count = len(remoteset - localset)
      for item in (remoteset - localset):
        self.logger.info('(' + str(count) + ') Deleting: ' + item)
        outdict = {
          'code' : 'delete',
          'name' : item,
        }
        self.ws.send(json.dumps(outdict), opcode=1) #1 = Text
        i = 0
        while i < 20:
          try:
            self.ws.recv()
            break
          except TimeoutError:
            i += 1
        count -= 1  
      count = len(localset - remoteset)
      for item in (localset - remoteset):
        self.logger.info('(' + str(count) + ') Sending: ' + item)
        outdict = {
          'code' : 'send',
          'name' : item,
          'tags' : localdict[item][:10],
          'framecode' : localdict[item][11],
        }
        self.ws.send(json.dumps(outdict), opcode=1) #1 = Text
        filepath = self.myschool.dir + 'frames/' + item
        with open(filepath, "rb") as f:
          self.ws.send_binary(f.read())
        self.ws.recv()
        count -= 1  
      if self.t_type == 2:
        outdict = {
          'code' : 'checkfitdone',
          'mode' : 'init',
          'school' : self.myschool.e_school,
        }
        self.ws.send(json.dumps(outdict), opcode=1) #1 = Text
        model_type = json.loads(self.ws.recv())
      outdict = {
        'code' : 'trainnow',
      } 
      self.ws.send(json.dumps(outdict), opcode=1) #1 = Text
      self.logger.info('Sent trigger for train_now... ')
      if self.t_type == 2:
        outdict = {
          'code' : 'checkfitdone',
          'mode' : 'sync',
          'school' : self.myschool.e_school,
        }
        self.ws.send(json.dumps(outdict), opcode=1) #1 = Text
        dlurl = json.loads(self.ws.recv())
        self.logger.info('DL Url: ' + dlurl)
        outdict = {
          'code' : 'checkfitdone',
          'mode' : 'check',
          'school' : self.myschool.e_school,
        }
        while True:
          self.ws.send(json.dumps(outdict), opcode=1) #1 = Text
          result = json.loads(self.ws.recv())
          if result:
            break
          else:
            sleep(10.0)
        r = requests.get(dlurl, allow_redirects=True)
        dlfile = djconf.getconfig('schools_dir', 'data/schools/')
        dlfile += 'model' + str(self.myschool.id) + '/model/' + model_type + '.h5'
        self.logger.info('DL Model: ' + dlfile)
        open(dlfile, 'wb').write(r.content)
        self.myschool.lastmodelfile = timezone.now()
        self.myschool.save(update_fields=["lastmodelfile"])
        self.logger.info('Done...')
      self.ws.close()
      
    except:
      self.logger.error(format_exc())
      self.logger.handlers.clear()
    return(0)
