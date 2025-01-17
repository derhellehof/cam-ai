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

# /trainers/c_trainers.py V0.9.14 11.06.2023

import gc
from multiprocessing import Process, Queue
from threading import Thread, Lock
from queue import Queue as threadqueue, Empty
from signal import signal, SIGINT, SIGTERM, SIGHUP
from traceback import format_exc
from logging import getLogger
from time import sleep, time
from setproctitle import setproctitle
from django.utils import timezone
from django.db.utils import DatabaseError, OperationalError
from django.db import connections, connection
from django.db.models import Max
from tools.c_logger import log_ini
from tools.l_tools import QueueUnknownKeyword, ts2mysqltime, djconf
from tf_workers.models import school
from .models import trainer as dbtrainer, trainframe, fit, epoch
if djconf.getconfigbool('local_trainer', True):
  from .train_worker_gpu import train_once_gpu
from .train_worker_remote import train_once_remote

#from threading import enumerate

trainers = {}
short_brake = djconf.getconfigfloat('short_brake', 0.01)

def sigint_handler(signal, frame):
  #print ('TFWorkers: Interrupt is caught')
  pass

#***************************************************************************
#
# trainers server
#
#***************************************************************************

class trainer():
  def __init__(self, idx):
    self.inqueue = Queue()
    self.id = idx
    self.outqueue = Queue()
    self.queueinfobuffers = {}
    self.mylock = Lock()
    self.job_queue_list = []

    #*** Client Var
    self.active_schools = set()
    self.run_out_proc = None

  def in_queue_thread(self):
    try:
      while True:
        received = self.inqueue.get()
        #print('Trainer:', received)
        if (received[0] == 'stop'):
          self.do_run = False
          while not self.inqueue.empty():
            received = self.inqueue.get()
          break
        elif (received[0] == 'getqueueinfo'):
          self.outqueue.put(('getqueueinfo', received[1], self.job_queue_list))
        else:
          raise QueueUnknownKeyword(received[0])
    except:
      self.logger.error(format_exc())
      self.logger.handlers.clear()

  def job_queue_thread(self):
    try:
      while self.do_run:
        schoollines = school.objects.filter(
          active=True,
          tf_worker=self.dbline.id,
        )
        for item in schoollines:
          with self.mylock:
            if item.id not in self.job_queue_list:
              run_condition = False
              if item.extra_runs:
                item.extra_runs -= 1
                item.save(update_fields=["extra_runs"])
                run_condition=trainframe.objects.filter(school=item.id).count()
              else:
                filterdict = {
                  'school' : item.id,
                  'train_status__lt' : 2,}
                if not item.ignore_checked:
                  filterdict['checked'] = True
                undone = trainframe.objects.filter(**filterdict)
                count = undone.count()
                if count:
                  undone.update(train_status=1)
                  alllines = 1
                else:
                  alllines = trainframe.objects.filter(school=item.id).count()
                run_condition = (count >= item.trigger) and alllines
              if run_condition:
                fitstodelete = fit.objects.filter(
                  status='Queuing', 
                  school=item.id)
                for fititem in fitstodelete:
                  epoch.objects.filter(fit=fititem).delete()
                fitstodelete.delete()
                fitstodelete = fit.objects.filter(
                  status='Working', 
                  school=item.id)
                for fititem in fitstodelete:
                  epoch.objects.filter(fit=fititem).delete()
                fitstodelete.delete()
                myfit = fit(made=timezone.now(), 
	                minutes = 0.0, 
	                school = item.id, 
	                epochs = 0, 
	                nr_tr = 0,
	                nr_va = 0,
	                loss = 0.0, 
	                cmetrics = 0.0, 
	                hit100 = 0.0, 
	                val_loss = 0.0, 
	                val_cmetrics = 0.0, 
	                val_hit100 = 0.0, 
	                cputemp = 0.0, 
	                cpufan1 = 0.0, 
	                cpufan2 = 0.0, 
	                gputemp = 0.0, 
	                gpufan = 0.0, 
	                description = '',
                  status = 'Queuing',
                )
                myfit.save()
                self.job_queue_list.append(item.id)
                self.job_queue.put((item, myfit)) 
        sleep(10.0)
    except:
      self.logger.error(format_exc())
      self.logger.handlers.clear()

  def run(self):
    self.do_run = True
    self.run_process = Process(target=self.runner)
    connections.close_all()
    self.run_process.start()

  def runner(self):
    self.dbline = dbtrainer.objects.get(id=self.id)
    Thread(target=self.in_queue_thread, name='Trainer_InQueueThread').start()
    signal(SIGINT, sigint_handler)
    signal(SIGTERM, sigint_handler)
    signal(SIGHUP, sigint_handler)
    self.logname = 'trainer #'+str(self.dbline.id)
    self.logger = getLogger(self.logname)
    log_ini(self.logger, self.logname)
    try:
      setproctitle('CAM-AI-Trainer #'+str(self.dbline.id))
      self.finished = False
      self.job_queue = threadqueue()
      Thread(target=self.job_queue_thread, name='Trainer_JobQueueThread').start()
      while self.do_run:
        while True:
          try:
            self.dbline = dbtrainer.objects.get(id=self.id)
            break
          except OperationalError:
            connection.close()
        timestr = ts2mysqltime(time())
        if((self.dbline.startworking < timestr) 
            and (self.dbline.stopworking > timestr)
            and self.dbline.running):
          try:
            tempread = self.job_queue.get(timeout=1.0)
            myschool = tempread[0]
            myfit = tempread[1]
            if (self.dbline.t_type == 1):
              gpu_process = Process(target = train_once_gpu, args = (myschool, myfit, 
                self.dbline.gpu_nr, self.dbline.gpu_mem_limit, ))
              gpu_process.start()
              gpu_process.join()
              trainresult = (gpu_process.exitcode)
            elif (self.dbline.t_type in {2, 3}):
              trainresult = train_once_remote(
                myschool, 
                myfit, 
                self.dbline.wsserver, 
                self.dbline.wsname, 
                self.dbline.wspass, 
                self.dbline.t_type,
                self.logger,
              ).run()
            if  not trainresult:
              filterdict = {
                'school' : myschool.id,
                'train_status' : 1,
              }
              if not myschool.ignore_checked:
                filterdict['checked'] = True
              while True:
                try:
                  trainframe.objects.filter(**filterdict).update(train_status=2)
                  break
                except OperationalError:
                  connection.close()
            with self.mylock:
              self.job_queue_list.remove(myschool.id)
            gc.collect()
          except Empty:
            pass
        sleep(10.0)
      self.finished = True
    except:
      self.logger.error(format_exc())
      self.logger.handlers.clear()
    #for thread in enumerate(): 
    #  print(thread)
    self.logger.info('Finished Process '+self.logname+'...')
    self.logger.handlers.clear()
  
  def stop(self):
    if self.run_out_proc and self.run_out_proc.is_alive():
      self.outqueue.put(('stop',))
      self.run_out_proc.join()
    self.inqueue.put(('stop',))
    self.run_process.join()

#***************************************************************************
#
# trainers client
#
#***************************************************************************

  def out_reader_proc(self):
    while (received := self.outqueue.get())[0] != 'stop':
      #print('Out:', received)
      if (received[0] == 'getqueueinfo'):
        self.queueinfobuffers[received[1]] = received[2]
      else:
        raise QueueUnknownKeyword(received[0])
    #print('Finished:', received)

  def run_out(self, schoolnr):
    if schoolnr in self.active_schools:
      return('Busy')
    else:
      if not self.active_schools:
        self.run_out_proc = Thread(
          target=self.out_reader_proc, 
          name='RunOutThread'+str(schoolnr), 
          )
        self.run_out_proc.start()
      self.active_schools.add(schoolnr)
      return('OK')

  def stop_out(self, schoolnr):
    self.active_schools.remove(schoolnr)
    if not self.active_schools:
      self.outqueue.put(('stop',))
      self.run_out_proc.join()

  def getqueueinfo(self, schoolnr):
    self.queueinfobuffers[schoolnr] = None
    self.inqueue.put(('getqueueinfo', schoolnr, ))
    while self.queueinfobuffers[schoolnr] is None:
      sleep(short_brake)
    return(self.queueinfobuffers[schoolnr])
